"""The spans of launch and resume (harness/otel.py, 05/F32): with HARNESS_OTEL_ENDPOINT set they reach that OTLP/HTTP
endpoint, a collector this test runs on 127.0.0.1; without it nothing is exported and OpenTelemetry is not imported."""

from __future__ import annotations

import http.server
import os
import subprocess
import sys
import threading

import pytest
from harness import otel
from opentelemetry import trace
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

PROXIES = ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY")


@pytest.fixture()
def collector(monkeypatch):
    """A local OTLP/HTTP collector: the paths of the requests it received, and their bodies."""
    for var in PROXIES:  # the collector is local; a sandbox's proxy would never reach it
        monkeypatch.delenv(var, raising=False)
    received: list[str] = []
    bodies: list[bytes] = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            bodies.append(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
            received.append(self.path)
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/v1/traces", received, bodies
    server.shutdown()


def test_a_span_of_launch_reaches_the_endpoint_when_it_ends(collector, monkeypatch):
    endpoint, received, bodies = collector
    monkeypatch.setenv("HARNESS_OTEL_ENDPOINT", endpoint)
    with otel.span("invoke_agent", agent_name="reader", run_id="r1", stage="read", model="sonnet"):
        assert received == []  # sent when the span ends, not before
    assert received == ["/v1/traces"]
    (resource,) = ExportTraceServiceRequest.FromString(bodies[0]).resource_spans
    (sent,) = (s for scope in resource.scope_spans for s in scope.spans)
    assert {a.key: a.value.string_value for a in resource.resource.attributes}["service.name"] == "harness"
    assert sent.name == "invoke_agent reader" and {a.key: a.value.string_value for a in sent.attributes} == {
        "gen_ai.operation.name": "invoke_agent",
        "gen_ai.agent.name": "reader",
        "gen_ai.provider.name": "anthropic",
        "gen_ai.request.model": "sonnet",
        "harness.run_id": "r1",
        "harness.stage": "read",
    }
    with pytest.raises(KeyError), otel.span("invoke_agent", agent_name="judge", run_id="r1", stage="judge"):
        raise KeyError("a launch that fails inside its span")  # the error goes on; the span is sent all the same
    assert received == ["/v1/traces", "/v1/traces"]
    assert type(trace.get_tracer_provider()).__name__ == "ProxyTracerProvider"  # the global provider is left as it is


UNSET = (
    "import sys\nfrom harness import otel\n"
    "with otel.span('invoke_agent', agent_name='reader', run_id='r1', stage='read'):\n    pass\n"
    "print(sorted(m for m in sys.modules if m.startswith('opentelemetry')))"
)


def test_without_the_endpoint_nothing_is_exported_or_imported():
    env = {k: v for k, v in os.environ.items() if k != "HARNESS_OTEL_ENDPOINT"}
    for unset in (env, {**env, "HARNESS_OTEL_ENDPOINT": ""}):  # missing, or set to nothing
        done = subprocess.run([sys.executable, "-c", UNSET], capture_output=True, text=True, check=True, env=unset)
        assert done.stdout.strip() == "[]"
