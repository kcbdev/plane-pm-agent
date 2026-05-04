# plane-pm-agent

**High-level project management tools for [Plane](https://plane.so) — powered by FastMCP.**

Exposes 14 intelligent PM tools on top of the Plane API. Use natural language to query sprints, generate standup reports, manage backlogs, and automate bulk operations — from any AI coding assistant or MCP-compatible tool.

---

## What it does

Instead of calling the raw Plane API, you get curated, human-readable outputs:

| Tool | Output |
|---|---|
| `pm_standup_report` | Markdown standup grouped by team member + state |
| `pm_sprint_status` | Sprint health: completion rate, state breakdown, unassigned count |
| `pm_priority_matrix` | Priority × status matrix in Markdown table |
| `pm_blocker_report` | Items that are unassigned or have no state |
| `pm_list_projects` | All projects in a workspace |
| `pm_list_work_items` | Paginated work items with cursor support |
| `pm_create_work_item` | Create with full field support |
| `pm_update_work_item` | Update any field |
| `pm_delete_work_item` | Delete by ID |
| `pm_get_work_item` | Full work item details |
| `pm_get_project_members` | Team members with roles |
| `pm_bulk_create` | Batch-create items in one call |
| `pm_unassigned_items` | All items with no assignee |
| `pm_mark_complete` | Move item to the first completed state |

See [SPEC.md](SPEC.md) for the full tool reference.

---

## Quick Start

### Prerequisites

- Python 3.12+
- A running [Plane](https://plane.so) instance (cloud or self-hosted)
- A Plane Personal Access Token (PAT) with read/write access

### 1. Get a Plane PAT

1. Open your Plane instance → **Settings** → **Tokens**
2. Create a new token with the permissions you need
3. Copy the token — you'll use it as `PLANE_PAT`

### 2. Deploy

#### Option A — Docker (recommended for most users)

```bash
# Save as docker-compose.yml in a new directory
curl -fsSL https://raw.githubusercontent.com/kcbdev/plane-pm-agent/main/docker-compose.yml
```

Create a `.env` file:

```env
PLANE_BASE_URL=https://plane.your-instance.com
PLANE_PAT=your_plane_pat_here
PLANE_WORKSPACE_SLUG=your_workspace_slug
PLANE_PROJECT_ID=your_project_uuid
PM_AGENT_API_KEY=change_me_generate_with_python
```

Generate a secure API key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Start:

```bash
docker-compose up -d
```

The server runs on `http://localhost:8212`. The MCP endpoint is at `http://localhost:8212/mcp`.

#### Option B — pip (for local development)

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in your .env values
python -m app
```

#### Option C — Coolify

Deploy to your Coolify instance using the GitHub repository `https://github.com/kcbdev/plane-pm-agent`. Set the environment variables listed in the [Configuration](#configuration) section directly in the Coolify UI.

### 3. Connect an MCP client

Any tool that speaks the [Model Context Protocol](https://modelcontextprotocol.io) can connect. Configure your client with:

- **URL:** `http://localhost:8212/mcp` (or your deployed URL)
- **Auth header:** `X-API-Key: your-pm-agent-api-key`

See the [MCP Clients](#mcp-clients) section below for platform-specific examples.

---

## Configuration

### Environment variables

All configuration is via environment variables.

| Variable | Required | Description |
|---|---|---|
| `PLANE_BASE_URL` | Yes | Base URL of your Plane instance (no trailing slash) |
| `PLANE_PAT` | Yes | Plane Personal Access Token |
| `PLANE_WORKSPACE_SLUG` | Yes | Workspace identifier — find it in the workspace URL |
| `PLANE_PROJECT_ID` | Yes | Default project UUID for tools that need one |
| `PM_AGENT_API_KEY` | **Yes** | API key for MCP client authentication |

**Security:** If `PM_AGENT_API_KEY` is not set, the server rejects *all* requests to prevent accidental open access. Always set it.

#### Optional security tuning

| Variable | Default | Description |
|---|---|---|
| `PM_AGENT_AUTH_ENABLED` | `true` | Set to `false` to disable API key auth (not recommended for public deployments) |
| `PM_AGENT_RATE_LIMIT` | `60/minute` | Rate limit per client IP. Format: `count/period` where period is `s`, `m`, or `h` |
| `PM_AGENT_HSTS_MAX_AGE` | `31536000` | HSTS max-age in seconds. Set `0` to disable HSTS |

---

## MCP Clients

The server implements the **SSE transport** of the [Model Context Protocol](https://modelcontextprotocol.io). Any MCP-compatible client works.

Your client needs two things:
1. **URL:** `http://your-host:8212/mcp`
2. **Header:** `X-API-Key: your-pm-agent-api-key` (or `Authorization: Bearer your-pm-agent-api-key`)

Below are setup examples for common clients. If your client supports a `headers` field, use that. If it supports an `env` block with custom headers, that also works.

### Generic MCP client config

```json
{
  "mcpServers": {
    "plane-pm": {
      "url": "https://your-host/mcp",
      "headers": {
        "X-API-Key": "your-pm-agent-api-key"
      }
    }
  }
}
```

### Claude Desktop

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "plane-pm": {
      "url": "https://your-host/mcp",
      "headers": {
        "X-API-Key": "your-pm-agent-api-key"
      }
    }
  }
}
```

### Zed

Add to `~/.config/zed/settings.json`:

```json
{
  "context_servers": {
    "plane-pm": {
      "enabled": true,
      "remote": true,
      "settings": {
        "url": "https://your-host/mcp",
        "headers": {
          "X-API-Key": "your-pm-agent-api-key"
        }
      }
    }
  }
}
```

### Cursor

Add to Cursor settings → `mcpServers`:

```json
{
  "mcpServers": {
    "plane-pm": {
      "url": "https://your-host/mcp",
      "headers": {
        "X-API-Key": "your-pm-agent-api-key"
      }
    }
  }
}
```

### Cline / Roo Code / other MCP CLIs

These tools typically accept the same `url` + `headers` config. Refer to your tool's MCP server documentation.

> **Note:** Not all MCP clients support custom headers. If yours doesn't, you may need to use an HTTP proxy (e.g., a Cloudflare Worker or nginx reverse proxy) to inject the `X-API-Key` header on your behalf.

---

## API Reference

### Endpoints

| Path | Method | Description |
|---|---|---|
| `/mcp` | GET/POST | Primary MCP SSE endpoint |
| `/sse` | GET | Server-Sent Events fallback |
| `/sse/0.1` | GET | SSE v0.1 |
| `/` | GET | Health check (no auth required) |

### Authentication

All MCP endpoints require a valid `X-API-Key` header (or `Authorization: Bearer`).

```
X-API-Key: your-pm-agent-api-key
```

Unauthorized requests receive `401` with a JSON-RPC error body.

### Rate limiting

Sliding-window rate limiting (default **60 requests/minute per IP**). Rate-limited requests receive `429` with:

```
Retry-After: <seconds>
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: <seconds>
```

### Security headers

Every response includes:

- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; ...`
- `Cache-Control: no-store, no-cache, ...`

---

## For Developers

### Project structure

```
plane-pm-agent/
├── app/
│   ├── __init__.py    # FastMCP server definition + all 14 tools
│   └── __main__.py    # Uvicorn entry point + middleware
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── SPEC.md            # Full tool specifications
├── README.md
├── LICENSE
└── CONTRIBUTING.md
```

### Architecture

- **`app/__init__.py`** — FastMCP instance (`mcp = FastMCP("plane-pm-agent")`) + all tool definitions. All HTTP calls go through `api_get`, `api_post`, `api_patch`, `api_delete` helpers.
- **`app/__main__.py`** — Uvicorn entry point. Applies three middleware layers: auth → rate limiting → security headers. No business logic here.
- **`app.py` (pre-package layout)** — Legacy single-file layout, kept in git history.

### Running locally

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and edit env
cp .env.example .env

# Start the server
python -m app
```

### Adding a new tool

1. Add a function in `app/__init__.py` decorated with `@mcp.tool()`.
2. Document the arguments and return shape in `SPEC.md`.
3. Use the existing API helpers (`api_get`, `api_post`, `api_patch`, `api_delete`) — never raw `httpx` calls.
4. Run locally to test: `python -m app` then send an MCP request.

**Example:**

```python
@mcp.tool()
def pm_my_new_tool(project_id: str | None = None, status: str | None = None) -> list[dict]:
    """
    Describe what this tool does.

    Args:
        project_id: Project UUID (defaults to PLANE_PROJECT_ID).
        status: Filter by status string.

    Returns:
        List of matching work items.
    """
    pid = project_id or PLANE_PROJECT_ID
    params = {"status": status} if status else {}
    return api_get(f"workspaces/{PLANE_WORKSPACE}/projects/{pid}/work-items/", params)
```

### Running tests

```bash
pip install pytest httpx
pytest -v
```

### Code quality

```bash
pip install ruff
ruff check .
```

---

## Deployment

### Docker

```bash
docker run -d \
  --name plane-pm-agent \
  -p 8212:8212 \
  -e PLANE_BASE_URL=https://plane.your-instance.com \
  -e PLANE_PAT=your_plane_pat \
  -e PLANE_WORKSPACE_SLUG=your_workspace \
  -e PLANE_PROJECT_ID=your_project_uuid \
  -e PM_AGENT_API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))") \
  ghcr.io/kcbdev/plane-pm-agent
```

### Coolify

1. Create a new application in Coolify, connect your GitHub repo.
2. Set build pack to **Dockerfile**.
3. Add environment variables:
   - `PLANE_BASE_URL`, `PLANE_PAT`, `PLANE_WORKSPACE_SLUG`, `PLANE_PROJECT_ID`
   - `PM_AGENT_API_KEY` (generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`)

The exposed port is **8212**. Configure your domain in Coolify to point to that port. No health check path is needed — health check is disabled because the MCP server has no `GET /` handler.

---

## Security

The server applies three layers of hardening:

1. **API key auth** — `X-API-Key` or `Authorization: Bearer` required on all MCP endpoints. No key = no access.
2. **Rate limiting** — 60 req/min per IP, sliding window. Protects against abuse.
3. **Security headers** — HSTS, CSP, X-Frame-Options, no-sniff, cache control on every response.

If you expose this server publicly, always set a strong `PM_AGENT_API_KEY`. The server will refuse to start without one.

---

## Known Limitations

- **Plane self-hosted < v1.3.0:** Some Plane API endpoints (`/advanced-search/`, `/features/`) used by other Plane MCP tools may 404. This server only uses stable, documented endpoints.
- **Description field:** Sent as `description_html` — Plane expects HTML-formatted descriptions.
- **Assignee format:** Plane API returns nested member objects but accepts flat user UUIDs on creation. This server normalizes both formats transparently.
- **MCP clients without header support:** If your client doesn't let you pass custom HTTP headers, you'll need a reverse proxy to inject the `X-API-Key` header.

---

## License

MIT — see [LICENSE](LICENSE).