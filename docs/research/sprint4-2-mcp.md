# Sprint 4.2 — Hermes MCP Integration Layer

Optional MCP server: `src/sportoto/mcp_server.py`

Exposed tools only:

```text
sportoto_run
sportoto_inspect
```

Not exposed:

```text
set_probability
override_risk
force_banko
modify_decision
modify_filter
```

## Hermes configuration

`pyproject.toml` has the optional dependency group:

```bash
uv sync --extra hermes-mcp
```

Example `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  sportoto:
    command: "uv"
    args: ["--directory", "/root/sportoto", "run", "--extra", "hermes-mcp", "python", "-m", "sportoto.mcp_server"]
    timeout: 180
    connect_timeout: 30
```

Restart Hermes after adding the server. Native MCP registers the tools with the `mcp_sportoto_*` prefix.

## Operations

`sportoto_run` executes the complete domain workflow and returns `WorkflowResult`. `sportoto_inspect` reads an existing journal projection and never reruns or mutates the workflow.

The domain interface does not expose policy overrides.
