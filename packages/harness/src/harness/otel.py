"""OpenTelemetry spans for harness actions. Attribute names follow the OTel GenAI agent-span conventions
(gen_ai.operation.name, gen_ai.agent.name, gen_ai.provider.name, gen_ai.request.model); harness.* are ours.
Claude Code does not pass its OTEL_* variables to subprocesses, so the exporter endpoint comes from HARNESS_OTEL_ENDPOINT:
the full OTLP/HTTP traces URL (`http://localhost:4318/v1/traces`). Without it nothing is exported or imported."""

from __future__ import annotations

import contextlib
import functools
import os
from collections.abc import Iterator


@functools.cache
def _tracer(endpoint: str):
    """A tracer whose every span goes to `endpoint` when it ends (an OTLP/HTTP exporter behind a simple span processor:
    a harness command ends right after its span, before a batch would be sent). The provider is the harness's own;
    the process's global provider is left as it is."""
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": "harness"}))
    provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    return provider.get_tracer("harness")


@contextlib.contextmanager
def span(operation: str, *, agent_name: str, run_id: str, stage: str, model: str | None = None) -> Iterator[None]:
    endpoint = os.environ.get("HARNESS_OTEL_ENDPOINT")
    if not endpoint:
        yield
        return
    with _tracer(endpoint).start_as_current_span(f"{operation} {agent_name}") as s:
        s.set_attribute("gen_ai.operation.name", operation)
        s.set_attribute("gen_ai.agent.name", agent_name)
        s.set_attribute("gen_ai.provider.name", "anthropic")
        if model:
            s.set_attribute("gen_ai.request.model", model)
        s.set_attribute("harness.run_id", run_id)
        s.set_attribute("harness.stage", stage)
        yield
