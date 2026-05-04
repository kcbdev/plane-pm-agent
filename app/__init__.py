"""
plane-pm-agent - FastMCP server wrapping Plane API with high-level PM tools.
"""

import os
import httpx
from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Config from env
# ---------------------------------------------------------------------------
PLANE_BASE_URL = os.getenv("PLANE_BASE_URL", "https://plane.kcb.ma")
PLANE_API_KEY = os.getenv("PLANE_PAT", "plane_api_ac571e3e4b80488fac8d6d45d679da75")
PLANE_WORKSPACE = os.getenv("PLANE_WORKSPACE_SLUG", "kcbdev")
PLANE_PROJECT_ID = os.getenv("PLANE_PROJECT_ID", "3b5bd197-028c-4884-a304-011f088694e2")

API_BASE = f"{PLANE_BASE_URL}/api/v1"
HEADERS = {
    "x-api-key": PLANE_API_KEY,
    "Content-Type": "application/json",
}

mcp = FastMCP("plane-pm-agent")

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _make_client() -> httpx.Client:
    return httpx.Client(base_url=API_BASE, headers=HEADERS, timeout=30)


def api_get(path: str, params: dict = None) -> dict | list:
    try:
        with _make_client() as client:
            r = client.get(path, params=params)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        raise Exception(f"Plane API error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        raise Exception(f"Request failed: {str(e)}")


def api_post(path: str, data: dict) -> dict:
    try:
        with _make_client() as client:
            r = client.post(path, json=data)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        raise Exception(f"Plane API error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        raise Exception(f"Request failed: {str(e)}")


def api_patch(path: str, data: dict) -> dict:
    try:
        with _make_client() as client:
            r = client.patch(path, json=data)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        raise Exception(f"Plane API error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        raise Exception(f"Request failed: {str(e)}")


def api_delete(path: str) -> None:
    try:
        with _make_client() as client:
            r = client.delete(path)
            r.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise Exception(f"Plane API error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        raise Exception(f"Request failed: {str(e)}")


def _workspace_path(workspace_slug: str | None, project_id: str | None = None) -> str:
    """Build base path for workspace/project endpoints."""
    ws = workspace_slug or PLANE_WORKSPACE
    if project_id:
        return f"workspaces/{ws}/projects/{project_id}"
    return f"workspaces/{ws}/projects"


def _fetch_all_work_items(project_id: str, per_page: int = 50) -> list[dict]:
    """Paginate through all work items, returning a flat list."""
    all_items = []
    cursor = None
    while True:
        params = {"per_page": per_page}
        if cursor:
            params["cursor"] = cursor
        data = api_get(f"workspaces/{PLANE_WORKSPACE}/projects/{project_id}/work-items/", params)
        if isinstance(data, dict):
            items = data.get("results", data.get("items", []))
        elif isinstance(data, list):
            items = data
        else:
            items = []
        all_items.extend(items)
        if isinstance(data, dict):
            next_cursor = data.get("next_cursor") or data.get("next")
            if not next_cursor:
                break
            cursor = next_cursor
        else:
            break
    return all_items


def _fetch_states(project_id: str) -> dict[str, dict]:
    """Fetch all states and return a mapping of state_id -> state object."""
    try:
        data = api_get(f"workspaces/{PLANE_WORKSPACE}/projects/{project_id}/states/")
        if isinstance(data, list):
            states = data
        elif isinstance(data, dict):
            states = data.get("results", data.get("states", []))
        else:
            states = []
        return {s["id"]: s for s in states}
    except Exception:
        return {}


def _fetch_members(project_id: str) -> dict[str, dict]:
    """Fetch all members and return a mapping of member_id -> member info."""
    try:
        data = api_get(f"workspaces/{PLANE_WORKSPACE}/projects/{project_id}/members/")
        if isinstance(data, list):
            members = data
        elif isinstance(data, dict):
            members = data.get("results", data.get("members", []))
        else:
            members = []
        result = {}
        for m in members:
            mid = m.get("member_id", m.get("id"))
            result[mid] = m
        return result
    except Exception:
        return {}


def _state_group(work_item: dict) -> str:
    """Extract state group from a work item."""
    state = work_item.get("state")
    if isinstance(state, dict):
        return state.get("group", "unknown")
    return "unknown"


def _assignees_list(work_item: dict) -> list[str]:
    """Extract assignees list from a work item."""
    assignees = work_item.get("assignees", [])
    if not isinstance(assignees, list):
        return []
    return [a.get("id", a) if isinstance(a, dict) else str(a) for a in assignees]


def _priority_display(priority: str | None) -> str:
    """Map priority code to display string."""
    mapping = {
        "urgent": "Urgent",
        "high": "High",
        "medium": "Medium",
        "low": "Low",
        "none": "No Priority",
    }
    return mapping.get(priority, "No Priority")


# ---------------------------------------------------------------------------
# Basic Plane Operations
# ---------------------------------------------------------------------------

@mcp.tool()
def pm_list_projects(workspace_slug: str | None = None) -> dict:
    """
    List all projects in a workspace.

    Args:
        workspace_slug: Workspace identifier (defaults to configured workspace)

    Returns:
        List of projects with their IDs and names
    """
    path = f"workspaces/{workspace_slug or PLANE_WORKSPACE}/projects/"
    return api_get(path)


@mcp.tool()
def pm_list_work_items(
    project_id: str | None = None,
    cursor: str | None = None,
    per_page: int = 50,
) -> dict:
    """
    List work items in a project with pagination.

    Args:
        project_id: Project UUID (defaults to configured project)
        cursor: Pagination cursor for next page
        per_page: Items per page (default 50, max 100)

    Returns:
        Paginated work items response
    """
    pid = project_id or PLANE_PROJECT_ID
    params = {"per_page": min(per_page, 100)}
    if cursor:
        params["cursor"] = cursor
    return api_get(f"workspaces/{PLANE_WORKSPACE}/projects/{pid}/work-items/", params)


@mcp.tool()
def pm_create_work_item(
    project_id: str | None = None,
    name: str = "",
    description: str | None = None,
    priority: str | None = None,
    assignees: list[str] | None = None,
    labels: list[str] | None = None,
    state: str | None = None,
    type_id: str | None = None,
    start_date: str | None = None,
    target_date: str | None = None,
) -> dict:
    """
    Create a new work item in a project.

    Args:
        project_id: Project UUID (defaults to configured project)
        name: Work item title (required)
        description: Work item description
        priority: Priority level (urgent/high/medium/low/none)
        assignees: List of assignee user UUIDs
        labels: List of label IDs
        state: State UUID to set on creation
        type_id: Work item type UUID
        start_date: Start date (ISO format YYYY-MM-DD)
        target_date: Target date (ISO format YYYY-MM-DD)

    Returns:
        Created work item object
    """
    pid = project_id or PLANE_PROJECT_ID
    data = {"name": name}
    if description is not None:
        data["description_html"] = description
    if priority is not None:
        data["priority"] = priority
    if assignees is not None:
        data["assignees"] = assignees
    if labels is not None:
        data["labels"] = labels
    if state is not None:
        data["state_id"] = state
    if type_id is not None:
        data["type_id"] = type_id
    if start_date is not None:
        data["start_date"] = start_date
    if target_date is not None:
        data["target_date"] = target_date
    return api_post(f"workspaces/{PLANE_WORKSPACE}/projects/{pid}/work-items/", data)


@mcp.tool()
def pm_update_work_item(
    project_id: str | None = None,
    work_item_id: str = "",
    name: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    state: str | None = None,
    assignees: list[str] | None = None,
    labels: list[str] | None = None,
) -> dict:
    """
    Update an existing work item.

    Args:
        project_id: Project UUID (defaults to configured project)
        work_item_id: Work item UUID to update
        name: New title
        description: New description
        priority: New priority level (urgent/high/medium/low/none)
        state: New state UUID
        assignees: New list of assignee user UUIDs (replaces existing)
        labels: New list of label IDs (replaces existing)

    Returns:
        Updated work item object
    """
    pid = project_id or PLANE_PROJECT_ID
    data = {}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description_html"] = description
    if priority is not None:
        data["priority"] = priority
    if state is not None:
        data["state_id"] = state
    if assignees is not None:
        data["assignees"] = assignees
    if labels is not None:
        data["labels"] = labels
    if not data:
        raise Exception("No update fields provided")
    return api_patch(f"workspaces/{PLANE_WORKSPACE}/projects/{pid}/work-items/{work_item_id}/", data)


@mcp.tool()
def pm_delete_work_item(
    project_id: str | None = None,
    work_item_id: str = "",
) -> str:
    """
    Delete a work item.

    Args:
        project_id: Project UUID (defaults to configured project)
        work_item_id: Work item UUID to delete

    Returns:
        Confirmation message
    """
    pid = project_id or PLANE_PROJECT_ID
    api_delete(f"workspaces/{PLANE_WORKSPACE}/projects/{pid}/work-items/{work_item_id}/")
    return f"Work item {work_item_id} deleted successfully"


@mcp.tool()
def pm_get_project_members(project_id: str | None = None) -> dict:
    """
    List all members of a project.

    Args:
        project_id: Project UUID (defaults to configured project)

    Returns:
        List of project members with their IDs, names, and emails
    """
    pid = project_id or PLANE_PROJECT_ID
    return api_get(f"workspaces/{PLANE_WORKSPACE}/projects/{pid}/members/")


# ---------------------------------------------------------------------------
# High-Level PM Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def pm_standup_report(project_id: str | None = None) -> str:
    """
    Generate a structured standup report for the project.

    Groups work items by assignee and state:
    - In Progress: items in 'started' state group
    - Todo: items in 'unstarted' or 'backlog' state group
    - Done: items in 'completed' state group

    Args:
        project_id: Project UUID (defaults to configured project)

    Returns:
        Markdown-formatted standup report
    """
    pid = project_id or PLANE_PROJECT_ID

    # Fetch states for group mapping
    states = _fetch_states(pid)
    # Fetch all work items
    all_items = _fetch_all_work_items(pid)
    # Fetch members for display names
    members = _fetch_members(pid)

    # Group items by assignee and state group
    by_assignee: dict[str, dict[str, list[dict]]] = {}

    # Also collect done items by assignee for "recently completed" section
    done_by_assignee: dict[str, list[dict]] = {}

    for item in all_items:
        group = _state_group(item)
        assignees = _assignees_list(item)

        if not assignees:
            # Unassigned items go to "unassigned" bucket
            unassigned_key = "unassigned"
            if unassigned_key not in by_assignee:
                by_assignee[unassigned_key] = {"started": [], "unstarted": [], "backlog": [], "completed": []}
            if group == "completed":
                by_assignee[unassigned_key]["completed"].append(item)
                done_by_assignee.setdefault(unassigned_key, []).append(item)
            elif group == "started":
                by_assignee[unassigned_key]["started"].append(item)
            elif group in ("unstarted", "backlog"):
                by_assignee[unassigned_key]["unstarted"].append(item)
        else:
            for assignee_id in assignees:
                if assignee_id not in by_assignee:
                    by_assignee[assignee_id] = {"started": [], "unstarted": [], "backlog": [], "completed": []}
                if group == "completed":
                    by_assignee[assignee_id]["completed"].append(item)
                    done_by_assignee.setdefault(assignee_id, []).append(item)
                elif group == "started":
                    by_assignee[assignee_id]["started"].append(item)
                elif group in ("unstarted", "backlog"):
                    by_assignee[assignee_id]["unstarted"].append(item)

    # Build markdown report
    lines = ["# Daily Standup Report\n"]

    if not by_assignee:
        lines.append("_No work items found in this project._")
        return "\n".join(lines)

    for assignee_id, groups in by_assignee.items():
        # Get display name
        member_info = members.get(assignee_id, {})
        if isinstance(member_info, dict):
            member = member_info.get("member", member_info)
            display_name = member.get("display_name", member.get("name", assignee_id))
        else:
            display_name = str(assignee_id)

        lines.append(f"## {display_name}\n")

        # In Progress
        started = groups.get("started", [])
        if started:
            lines.append("**In Progress:**")
            for item in started:
                priority = _priority_display(item.get("priority"))
                state_name = item.get("state", {}).get("name", "") if isinstance(item.get("state"), dict) else ""
                name = item.get("name", "Untitled")
                lines.append(f"- [{priority}] {name} ({state_name})")
            lines.append("")

        # Todo
        unstarted = groups.get("unstarted", []) + groups.get("backlog", [])
        if unstarted:
            lines.append("**Todo:**")
            for item in unstarted:
                priority = _priority_display(item.get("priority"))
                state_name = item.get("state", {}).get("name", "") if isinstance(item.get("state"), dict) else ""
                name = item.get("name", "Untitled")
                lines.append(f"- [{priority}] {name} ({state_name})")
            lines.append("")

        # Done (recently completed)
        done = done_by_assignee.get(assignee_id, [])
        if done:
            lines.append("**Done:**")
            for item in done:
                name = item.get("name", "Untitled")
                state_name = item.get("state", {}).get("name", "") if isinstance(item.get("state"), dict) else ""
                lines.append(f"- {name} ({state_name})")
            lines.append("")

    return "\n".join(lines)


@mcp.tool()
def pm_sprint_status(project_id: str | None = None) -> dict:
    """
    Show sprint health metrics for the project.

    Returns:
        Dictionary with:
        - total_items: total count of work items
        - by_state: list of {name, count} per state
        - unassigned_count: items without assignees
        - completion_rate_pct: percentage of items in completed state
    """
    pid = project_id or PLANE_PROJECT_ID

    all_items = _fetch_all_work_items(pid)
    states = _fetch_states(pid)

    total = len(all_items)
    state_counts: dict[str, int] = {}
    completed_count = 0
    unassigned_count = 0

    for item in all_items:
        state = item.get("state", {})
        state_name = "Unknown"
        if isinstance(state, dict):
            state_name = state.get("name", "Unknown")
            group = state.get("group", "")
            if group == "completed":
                completed_count += 1
        else:
            # Try by state_id
            state_id = item.get("state_id")
            if state_id and state_id in states:
                s = states[state_id]
                state_name = s.get("name", "Unknown")
                if s.get("group") == "completed":
                    completed_count += 1

        state_counts[state_name] = state_counts.get(state_name, 0) + 1

        assignees = _assignees_list(item)
        if not assignees:
            unassigned_count += 1

    completion_rate = round((completed_count / total * 100), 1) if total > 0 else 0.0

    by_state = [{"name": name, "count": count} for name, count in state_counts.items()]

    return {
        "total_items": total,
        "by_state": by_state,
        "unassigned_count": unassigned_count,
        "completion_rate_pct": completion_rate,
    }


@mcp.tool()
def pm_priority_matrix(project_id: str | None = None) -> str:
    """
    Show all work items in a priority x status matrix table.

    Rows: priority levels (Urgent, High, Medium, Low, None)
    Columns: state groups (Backlog, Todo, In Progress, Done, Cancelled)

    Args:
        project_id: Project UUID (defaults to configured project)

    Returns:
        Markdown-formatted matrix table
    """
    pid = project_id or PLANE_PROJECT_ID

    all_items = _fetch_all_work_items(pid)

    # Build matrix: priority -> state_group -> count
    priorities = ["urgent", "high", "medium", "low", "none"]
    state_groups = ["backlog", "unstarted", "started", "completed", "cancelled"]

    matrix: dict[str, dict[str, list[dict]]] = {p: {g: [] for g in state_groups} for p in priorities}

    for item in all_items:
        priority = item.get("priority", "none")
        if priority not in priorities:
            priority = "none"
        group = _state_group(item)
        if group not in state_groups:
            group = "backlog"
        matrix[priority][group].append(item)

    # Build markdown table
    lines = ["# Priority Matrix\n"]
    lines.append("| Priority | Backlog | Todo | In Progress | Done | Cancelled |")
    lines.append("|---|---|---|---|---|---|")

    priority_labels = {
        "urgent": "Urgent",
        "high": "High",
        "medium": "Medium",
        "low": "Low",
        "none": "No Priority",
    }

    for priority in priorities:
        row = [priority_labels[priority]]
        for group in state_groups:
            items = matrix[priority][group]
            count = len(items)
            if count > 0:
                # List item names
                names = ", ".join(i.get("name", "Untitled")[:30] for i in items[:3])
                if count > 3:
                    row.append(f"{count} ({names}...)")
                else:
                    row.append(f"{count} ({names})")
            else:
                row.append("-")
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    total_items = len(all_items)
    lines.append(f"_Total: {total_items} work items_")

    return "\n".join(lines)


@mcp.tool()
def pm_blocker_report(project_id: str | None = None) -> list[dict]:
    """
    Find work items that need attention (potential blockers).

    Items are considered blockers if they are:
    - Unassigned (no assignees)
    - Have no state set

    Args:
        project_id: Project UUID (defaults to configured project)

    Returns:
        List of blocker work items with reason
    """
    pid = project_id or PLANE_PROJECT_ID

    all_items = _fetch_all_work_items(pid)
    blockers = []

    for item in all_items:
        assignees = _assignees_list(item)
        state = item.get("state")
        state_id = item.get("state_id")
        has_state = state is not None or state_id is not None

        reasons = []
        if not assignees:
            reasons.append("unassigned")
        if not has_state:
            reasons.append("no_state")

        if reasons:
            blockers.append({
                "id": item.get("id"),
                "name": item.get("name", "Untitled"),
                "priority": item.get("priority", "none"),
                "reasons": reasons,
                "state": state.get("name") if isinstance(state, dict) else None,
            })

    return blockers


@mcp.tool()
def pm_bulk_create(
    project_id: str | None = None,
    items: list[dict] | None = None,
) -> list[dict]:
    """
    Bulk create multiple work items.

    Args:
        project_id: Project UUID (defaults to configured project)
        items: List of item dictionaries. Each dict supports:
            - name (required): item title
            - description: item description
            - priority: urgent/high/medium/low/none
            - assignees: list of user UUIDs
            - labels: list of label IDs
            - state: state UUID
            - start_date: ISO date string
            - target_date: ISO date string

    Returns:
        List of created work items
    """
    if not items:
        return []

    pid = project_id or PLANE_PROJECT_ID
    created = []

    for item_data in items:
        name = item_data.get("name")
        if not name:
            continue

        payload = {"name": name}
        for field in ("description", "priority", "assignees", "labels", "state", "start_date", "target_date"):
            if field in item_data and item_data[field] is not None:
                if field == "state":
                    payload["state_id"] = item_data[field]
                else:
                    payload[field] = item_data[field]

        try:
            result = api_post(f"workspaces/{PLANE_WORKSPACE}/projects/{pid}/work-items/", payload)
            created.append(result)
        except Exception as e:
            # On error, add a placeholder with error info
            created.append({
                "error": str(e),
                "name": name,
            })

    return created


@mcp.tool()
def pm_unassigned_items(project_id: str | None = None) -> list[dict]:
    """
    List all work items with no assignees.

    Args:
        project_id: Project UUID (defaults to configured project)

    Returns:
        List of unassigned work items
    """
    pid = project_id or PLANE_PROJECT_ID

    all_items = _fetch_all_work_items(pid)
    unassigned = []

    for item in all_items:
        assignees = _assignees_list(item)
        if not assignees:
            unassigned.append({
                "id": item.get("id"),
                "name": item.get("name", "Untitled"),
                "priority": item.get("priority", "none"),
                "state": item.get("state", {}).get("name") if isinstance(item.get("state"), dict) else None,
            })

    return unassigned


@mcp.tool()
def pm_get_work_item(
    project_id: str | None = None,
    work_item_id: str = "",
) -> dict:
    """
    Get a single work item by ID.

    Args:
        project_id: Project UUID (defaults to configured project)
        work_item_id: Work item UUID

    Returns:
        Full work item object
    """
    pid = project_id or PLANE_PROJECT_ID
    return api_get(f"workspaces/{PLANE_WORKSPACE}/projects/{pid}/work-items/{work_item_id}/")


@mcp.tool()
def pm_mark_complete(
    project_id: str | None = None,
    work_item_id: str = "",
) -> dict:
    """
    Mark a work item as complete by setting its state to the completed state.

    Args:
        project_id: Project UUID (defaults to configured project)
        work_item_id: Work item UUID

    Returns:
        Updated work item
    """
    pid = project_id or PLANE_PROJECT_ID

    # Fetch states to find the completed state
    states = _fetch_states(pid)
    completed_state_id = None
    for state_id, state in states.items():
        if state.get("group") == "completed":
            completed_state_id = state_id
            break

    if not completed_state_id:
        raise Exception("Could not find a completed state in this project")

    return api_patch(
        f"workspaces/{PLANE_WORKSPACE}/projects/{pid}/work-items/{work_item_id}/",
        {"state_id": completed_state_id},
    )


if __name__ == "__main__":
    mcp.run()