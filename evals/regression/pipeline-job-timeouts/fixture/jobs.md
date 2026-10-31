# Jobs that run the regression suite, one job's command per line
timeout -k 10 90m uv run harness eval --suite regression
timeout 80m uv run harness eval --suite regression --threshold 1.0
timeout 5000 uv run harness eval --suite regression
timeout 1.5h uv run harness eval --suite regression
timeout 1.2h uv run harness eval --suite regression
timeout 40m uv run harness eval --suite regression --case s-pair
timeout --preserve-status 30m uv run harness eval --case s-pair --suite regression
timeout 2m uv run harness eval --suite regression --baseline
timeout 1m uv run harness eval --suite regression --no-sessions --threshold 1.0
timeout -s KILL 50m uv run harness eval --suite regression
timeout 60 uv run harness eval --suite regression --case code-a
uv run harness eval --suite regression
timeout 0.06d uv run harness eval --suite regression
timeout --kill-after=10s 84m uv run harness eval --suite regression
timeout 0 uv run harness eval --suite regression
