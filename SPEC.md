# plane-pm-agent Specification

## Overview

`plane-pm-agent` is a FastMCP server that wraps the [Plane](https://plane.so) API with high-level project management tools suitable for AI coding assistants (Qwen Code, Zed, Claude Desktop, etc.).

## Architecture

- **Runtime**: Python 3.12 + [FastMCP](https://github.com/jlowin/fastmcp)
- **HTTP server**: Uvicorn (ASGI)
- **Entry point**: `python -m app` (requires the `app/` package)
- **Transport**: SSE (Server-Sent Events) — compatible with MCP clients over HTTP

## MCP Endpoint

- `GET /mcp` — SSE transport, primary endpoint for MCP clients
- `GET /sse` — SSE fallback
- `GET /sse/0.1` — SSE v0.1

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `PLANE_BASE_URL` | Yes | Base URL of your Plane instance (no trailing slash) |
| `PLANE_PAT` | Yes | Personal Access Token from Plane Settings → Tokens |
| `PLANE_WORKSPACE_SLUG` | Yes | Workspace slug (the part after `/` in the workspace URL) |
| `PLANE_PROJECT_ID` | Yes | Default project UUID (used when `project_id` is not passed) |

## API Conventions

- All API calls go through helper functions: `api_get`, `api_post`, `api_patch`, `api_delete`
- Base URL: `{PLANE_BASE_URL}/api/v1`
- Auth header: `x-api-key: {PLANE_PAT}`
- Errors raise `Exception` with a descriptive message

## Tools

All tools are prefixed with `pm_` to avoid collisions with the base `plane-mcp-server`.

### pm_list_projects

List all projects in a workspace.

**Arguments:**
- `workspace_slug: str | None` — defaults to `PLANE_WORKSPACE_SLUG`

**Returns:** Raw Plane API response (list of project objects).

---

### pm_list_work_items

Paginated work item listing.

**Arguments:**
- `project_id: str | None` — defaults to `PLANE_PROJECT_ID`
- `cursor: str | None` — pagination cursor
- `per_page: int` — default 50, max 100

**Returns:** `{ "results": [...], "next_cursor": "..." }`

---

### pm_create_work_item

Create a work item with full field support.

**Arguments:**
- `project_id: str | None`
- `name: str` — required
- `description: str | None`
- `priority: str | None` — `urgent` | `high` | `medium` | `low` | `none`
- `assignees: list[str] | None` — list of user UUIDs
- `labels: list[str] | None` — list of label IDs
- `state: str | None` — state UUID
- `type_id: str | None` — work item type UUID
- `start_date: str | None` — ISO format `YYYY-MM-DD`
- `target_date: str | None` — ISO format `YYYY-MM-DD`

**Returns:** Created work item object.

---

### pm_update_work_item

Update any mutable field on an existing work item.

**Arguments:**
- `project_id: str | None`
- `work_item_id: str` — required
- `name: str | None`
- `description: str | None`
- `priority: str | None`
- `state: str | None` — state UUID
- `assignees: list[str] | None`
- `labels: list[str] | None`

**Returns:** Updated work item object.

**Raises:** `Exception` if no update fields provided.

---

### pm_delete_work_item

**Arguments:**
- `project_id: str | None`
- `work_item_id: str`

**Returns:** Confirmation string.

---

### pm_get_work_item

**Arguments:**
- `project_id: str | None`
- `work_item_id: str`

**Returns:** Full work item object.

---

### pm_get_project_members

**Arguments:**
- `project_id: str | None`

**Returns:** Raw Plane API members response.

---

### pm_standup_report

Generates a markdown standup report grouped by assignee.

**Logic:**
- Fetches all work items (paginated)
- Fetches all states and members
- Groups by assignee (or "unassigned" bucket)
- Groups items by state group: `started` → In Progress, `unstarted`/`backlog` → Todo, `completed` → Done

**Output format:**
```markdown
# Daily Standup Report

## John Doe

**In Progress:**
- [High] Implement login flow (In Review)

**Todo:**
- [Medium] Fix navigation bug (Todo)

**Done:**
- Setup CI pipeline (Done)
```

---

### pm_sprint_status

Returns sprint health metrics as a structured dict.

**Returns:**
```python
{
    "total_items": 42,
    "by_state": [{"name": "In Progress", "count": 5}, ...],
    "unassigned_count": 3,
    "completion_rate_pct": 38.1,
}
```

---

### pm_priority_matrix

Returns a markdown priority × status matrix table.

**Output:**
```markdown
| Priority | Backlog | Todo | In Progress | Done | Cancelled |
|---|---|---|---|---|---|
| Urgent | - | 2 (...) | 1 (...) | - | - |
| High | 3 (...) | - | - | 1 (...) | - |
...
```

---

### pm_blocker_report

Returns items that are unassigned or have no state set — potential blockers.

**Returns:** `list[{"id", "name", "priority", "reasons": [...], "state"}]`

---

### pm_bulk_create

Batch-create multiple work items in a single call.

**Arguments:**
- `project_id: str | None`
- `items: list[dict]` — each dict supports: `name`, `description`, `priority`, `assignees`, `labels`, `state`, `start_date`, `target_date`

**Returns:** List of created work items (or `{"error": ..., "name": ...}` on failure).

---

### pm_unassigned_items

**Arguments:**
- `project_id: str | None`

**Returns:** `list[{"id", "name", "priority", "state"}]` for items with no assignees.

---

### pm_mark_complete

Sets the work item's state to the first state with `group == "completed"`.

**Arguments:**
- `project_id: str | None`
- `work_item_id: str`

**Returns:** Updated work item.

**Raises:** `Exception` if no completed state found in project.

---

## Deployment (Coolify)

Build pack: `Dockerfile`
Port: `8212`
Health check: disabled (SSE-only, no `/` response)

Traefik labels (set in Coolify FQDN config):
```
traefik.http.routers.plane-pm.rule=Host(`plane-pm.your-domain.com`) && PathPrefix(`/`)
traefik.http.services.plane-pm.loadbalancer.server.port=8212
```

## Known Limitations

- Plane self-hosted v1.3.0 is missing `/advanced-search/` and `/features/` endpoints used by some `plane-mcp-server` tools.
- The `description` field is sent as `description_html` — Plane expects HTML.
- Assignee format: Plane API accepts user UUIDs directly on creation but returns nested objects; the agent normalizes both formats.