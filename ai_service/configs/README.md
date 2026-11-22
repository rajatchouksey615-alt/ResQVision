# AI Service Configuration

Runtime configuration comes from environment variables; keep thresholds, source identifiers, model paths, and machine-specific values out of version control. The service requires an explicit confidence threshold, model name/version, source UUID, backend origin, model path, and SQLite outbox path. There are no calibrated defaults. See [AI Service configuration](../README.md#configuration).

Do not store machine credentials in this directory. Production machine authentication is an injected adapter and remains disabled until approved. The test-only adapter requires an explicit test mode and a token supplied by the test environment.
