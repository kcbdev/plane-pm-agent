# plane-pm-agent Specification

## 1. Project Overview

**Project Name:** plane-pm-agent
**Type:** FastMCP (Model Context Protocol) Server
**Core Functionality:** A high-level project management agent that wraps the Plane API with PM-specific tools for sprint management, standups, priority tracking, and bulk operations.
**Target Users:** Development teams using Plane self-hosted for project management.

---

## 2. Technology Stack

- **Runtime:** Python 3.12
- **Framework:** FastMCP
- **HTTP Client:** httpx
- **API:** Plane REST API v1 (self-hosted v1.3.0)
- **Deployment:** Docker container on Coolify

---

## 3. API Configuration

### Base Configuration
- **Base URL:** `https://plane.kcb.ma/api/v1`
- **Workspace Slug:** `kcbdev`
- **Project ID:** `3b5bd197-028c-4884-a304-011f088694e2`
- **Authentication:** `x-api-key` header

### Authentication Headers
```python
HEADERS = {
    "x-api-key": "plane_api_ac571e3e4b80488fac8d6d45d679da75",
    "Content-Type": "application/json",
}
```

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `PLANE_PAT` | `plane_api_ac571e3e4b80488fac8d6d45d679da75` | Plane API key |
| `PLANE_WORKSPACE_SLUG` | `kcbdev` | Workspace identifier |
| `PLANE_PROJECT_ID` | `3b5bd197-028c-4884-a304-011f088694e2` | Default project |
| `PLANE_BASE_URL` | `https://plane.kcb.ma` | Plane instance URL |

---

## 4. API Endpoints

All endpoints are relative to `/api/v1/workspaces/{workspace_slug}/projects/{project_id}/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/projects/` | List all projects in workspace |
| GET | `/{project_id}/members/` | List project members |
| GET | `/{project_id}/states/` | List all states with groups |
| GET | `/{project_id}/work-items/` | List work items (paginated) |
| POST | `/{project_id}/work-items/` | Create work item |
| GET | `/{project_id}/work-items/{work_item_id}/` | Get single work item |
| PATCH | `/{project_id}/work-items/{work_item_id}/` | Update work item |
| DELETE | `/{project_id}/work-items/{work_item_id}/` | Delete work item |

---

## 5. Tool Specification

### 5.1 Basic Plane Operations (Passthrough)

#### `pm_list_projects`
- **Input:** `workspace_slug` (optional, defaults to configured)
- **Output:** List of projects in workspace
- **Endpoint:** `GET /workspaces/{slug}/projects/`

#### `pm_list_work_items`
- **Input:** `project_id`, `cursor`, `per_page` (default 50)
- **Output:** Paginated work items list
- **Endpoint:** `GET /workspaces/{slug}/projects/{project_id}/work-items/`

#### `pm_create_work_item`
- **Input:** `project_id`, `name`, `description`, `priority`, `assignees`, `labels`, `state`, `type_id`, `start_date`, `target_date`
- **Output:** Created work item
- **Endpoint:** `POST /workspaces/{slug}/projects/{project_id}/work-items/`

#### `pm_update_work_item`
- **Input:** `project_id`, `work_item_id`, `name`, `description`, `priority`, `state`, `assignees`, `labels`
- **Output:** Updated work item
- **Endpoint:** `PATCH /workspaces/{slug}/projects/{project_id}/work-items/{work_item_id}/`

#### `pm_delete_work_item`
- **Input:** `project_id`, `work_item_id`
- **Output:** Confirmation message
- **Endpoint:** `DELETE /workspaces/{slug}/projects/{project_id}/work-items/{work_item_id}/`

#### `pm_get_project_members`
- **Input:** `project_id`
- **Output:** List of team members with IDs and names
- **Endpoint:** `GET /workspaces/{slug}/projects/{project_id}/members/`

### 5.2 High-Level PM Tools

#### `pm_standup_report`
- **Input:** `project_id`
- **Process:**
  1. Fetch all states to get state_id → state_group mapping
  2. Fetch all work items (paginate if needed)
  3. Group by assignee
  4. Categorize by state_group: started (In Progress), unstarted (Todo), completed (Done)
- **Output:** Markdown-formatted standup report
- **Sections:**
  - "In Progress" - items with state_group = started
  - "Todo" - items with state_group = unstarted
  - "Done" - items with state_group = completed

#### `pm_sprint_status`
- **Input:** `project_id`
- **Process:**
  1. Fetch all states
  2. Fetch all work items
  3. Count items by state
  4. Calculate completion percentage
  5. Identify unassigned items
- **Output:** Dict with keys:
  - `total_items`: Total count
  - `by_state`: List of {name, count}
  - `unassigned_count`: Items without assignees
  - `completion_rate_pct`: Percentage in completed state

#### `pm_priority_matrix`
- **Input:** `project_id`
- **Process:**
  1. Fetch states
  2. Fetch all work items
  3. Group by priority (urgent/high/medium/low/none) and state_group
- **Output:** Markdown table with priority as rows, state_group as columns

#### `pm_blocker_report`
- **Input:** `project_id`
- **Process:** Filter work items that are unassigned OR have no state
- **Output:** List of items needing attention

#### `pm_bulk_create`
- **Input:** `project_id`, `items` (list of dicts)
- **Process:** Create each item sequentially
- **Output:** List of created work items

#### `pm_unassigned_items`
- **Input:** `project_id`
- **Process:** Filter work items where assignees list is empty
- **Output:** List of unassigned items

---

## 6. Data Models

### Work Item Fields
```python
{
    "id": str,              # UUID
    "name": str,            # Title
    "description": str,     # HTML/markdown description
    "state": {              # Embedded state object
        "id": str,
        "name": str,
        "group": str        # backlog|unstarted|started|completed|cancelled
    },
    "state_id": str,        # Direct state ID reference
    "priority": str,         # urgent|high|medium|low|none
    "assignees": [str],     # List of user UUID strings
    "labels": [str],        # List of label IDs
    "start_date": str,      # ISO date
    "target_date": str,     # ISO date
}
```

### State Object
```python
{
    "id": str,
    "name": str,
    "group": str,  # backlog|unstarted|started|completed|cancelled
    "color": str,
    "sequence": int,
}
```

### Member Object
```python
{
    "id": str,
    "member": {
        "id": str,
        "display_name": str,
        "email": str,
        "avatar": str,
    }
}
```

---

## 7. Error Handling

### HTTP Error Handling
- Catch `httpx.HTTPStatusError` for 4xx/5xx responses
- Return user-friendly error message with status code

### General Error Handling
- Catch generic `Exception` for network/timeouts
- Return descriptive error message

### Error Response Format
```python
{
    "error": "Human readable message",
    "status_code": int,  # if applicable
}
```

---

## 8. Deployment

### Dockerfile
- Base: `python:3.12-slim`
- Port: `8212`
- Command: `uvicorn app:mcp --host 0.0.0.0 --port 8212`

### docker-compose
- Image tag pattern: `${APP_RELEASE:-v1.0.0}`
- Environment variables from env
- Network: `plane-pm-net`
- Restart: always

---

## 9. State Group Reference

| Group | Meaning | Standup Category |
|-------|---------|------------------|
| `backlog` | In backlog | Todo |
| `unstarted` | Ready to work | Todo |
| `started` | In progress | In Progress |
| `completed` | Done | Done |
| `cancelled` | Cancelled | (excluded) |

---

## 10. Priority Reference

| Priority | Display |
|----------|---------|
| `urgent` | Urgent |
| `high` | High |
| `medium` | Medium |
| `low` | Low |
| `none` | No Priority |