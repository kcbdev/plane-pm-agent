# plane-pm-agent

**High-level project management tools for [Plane](https://plane.so) powered by FastMCP.**

Exposes 14 MCP tools — standup reports, sprint health, priority matrices, bulk operations — on top of the Plane API. Deploy once, use from any MCP client (Qwen Code, Zed, Cursor, Claude Desktop…).

## Tools

| Tool | Description |
|---|---|
| `pm_list_projects` | List all projects in a workspace |
| `pm_list_work_items` | Paginated work item listing |
| `pm_create_work_item` | Create a work item with full field support |
| `pm_update_work_item` | Update any field on an existing work item |
| `pm_delete_work_item` | Delete a work item |
| `pm_get_work_item` | Fetch a single work item |
| `pm_get_project_members` | List project members |
| `pm_standup_report` | Markdown standup grouped by assignee and state |
| `pm_sprint_status` | Sprint health: completion rate, state breakdown, unassigned count |
| `pm_priority_matrix` | Priority × status matrix table in Markdown |
| `pm_blocker_report` | Items that are unassigned or have no state |
| `pm_bulk_create` | Batch-create multiple work items in one call |
| `pm_unassigned_items` | All unassigned work items |
| `pm_mark_complete` | Set a work item's state to the first completed state |

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/kcbdev/plane-pm-agent.git
cd plane-pm-agent
cp .env.example .env
# Edit .env with your Plane instance details
```

### 2. Run locally

```bash
pip install -r requirements.txt
python -m app
```

The server starts on `http://localhost:8212`. The MCP endpoint is available at:

- `http://localhost:8212/mcp` — SSE-based MCP (most clients)
- `http://localhost:8212/sse` — Server-Sent Events
- `http://localhost:8212/sse/0.1` — SSE v0.1

### 3. Docker

```bash
docker run -d \
  --name plane-pm-agent \
  -p 8212:8212 \
  -e PLANE_BASE_URL=https://plane.your-instance.com \
  -e PLANE_PAT=your_personal_access_token \
  -e PLANE_WORKSPACE_SLUG=your_workspace \
  -e PLANE_PROJECT_ID=your_project_uuid \
  ghcr.io/kcbdev/plane-pm-agent
```

Or with `docker-compose`:

```bash
cp .env.example .env
# Fill in your values, then:
docker-compose up -d
```

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `PLANE_BASE_URL` | Yes | `https://plane.kcb.ma` | Your Plane instance base URL |
| `PLANE_PAT` | Yes | — | Personal Access Token from Plane |
| `PLANE_WORKSPACE_SLUG` | Yes | `kcbdev` | Workspace identifier (slug) |
| `PLANE_PROJECT_ID` | No | env default | Default project for tools that need one |

### Getting a Personal Access Token

1. Go to your Plane instance → Settings → Tokens
2. Create a new token with read/write access
3. Copy the token to `PLANE_PAT`

## MCP Clients

### Qwen Code

Add to your `settings.json`:

```json
{
  "mcpServers": {
    "plane-pm": {
      "url": "https://plane-pm.kcb.ma/mcp",
      "enabled": true
    }
  }
}
```

### Zed

Add to `~/.config/zed/settings.json`:

```json
{
  "mcp": {
    "servers": {
      "plane-pm": {
        "url": "https://plane-pm.kcb.ma/mcp"
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
      "url": "https://plane-pm.kcb.ma/mcp"
    }
  }
}
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run in development (with auto-reload)
python -m app

# Run tests
pytest

# Lint
ruff check .
```

## Project Structure

```
plane-pm-agent/
├── app/
│   ├── __init__.py    # FastMCP server + all tools
│   └── __main__.py    # uvicorn entry point
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── SPEC.md            # Full tool specifications
├── README.md
├── LICENSE
└── CONTRIBUTING.md
```

## License

MIT — see [LICENSE](LICENSE).