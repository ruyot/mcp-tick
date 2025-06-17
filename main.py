import os
import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP

# Configuration
TICK_API_TOKEN = os.environ.get("TICK_API_TOKEN")
TICK_SUBDOMAIN = os.environ.get("TICK_SUBDOMAIN")

if not TICK_API_TOKEN or not TICK_SUBDOMAIN:
    raise ValueError("TICK_API_TOKEN and TICK_SUBDOMAIN environment variables are required")

BASE_URL = f"https://{TICK_SUBDOMAIN}.tickspot.com/api/v2"

# Initialize MCP server
mcp = FastMCP("Tick Time Tracker")

class TickAPI:
    def __init__(self):
        self.headers = {
            "Authorization": f"Token token={TICK_API_TOKEN}",
            "User-Agent": "MCP-Tick-Client (claude@anthropic.com)",
            "Content-Type": "application/json"
        }
    
    async def make_request(self, url: str, method: str = "GET", data: Dict = None, params: Dict = None) -> Dict[str, Any]:
        """Make async HTTP request to Tick API"""
        async with aiohttp.ClientSession() as session:
            kwargs = {"headers": self.headers}
            if data:
                kwargs["json"] = data
            if params:
                kwargs["params"] = params
                
            async with session.request(method, url, **kwargs) as response:
                if response.status == 304:
                    return {"not_modified": True}
                response.raise_for_status()
                return await response.json()
    
    async def get_projects(self, page: int = 1) -> List[Dict[str, Any]]:
        """Get projects with pagination"""
        url = f"{BASE_URL}/projects.json"
        params = {"page": page} if page > 1 else None
        return await self.make_request(url, params=params)
    
    async def get_all_projects(self) -> List[Dict[str, Any]]:
        """Get all projects across all pages"""
        all_projects = []
        page = 1
        while True:
            projects = await self.get_projects(page)
            if not projects:
                break
            all_projects.extend(projects)
            page += 1
        return all_projects
    
    async def find_project_id(self, project_name: str) -> Optional[int]:
        """Find project ID by name (case insensitive partial match)"""
        projects = await self.get_all_projects()
        for project in projects:
            if project_name.lower() in project["name"].lower():
                return project["id"]
        return None
    
    async def get_time_entries(self, project_id: int = None, start_date: str = None, end_date: str = None, page: int = 1) -> List[Dict[str, Any]]:
        """Get time entries with optional filters"""
        if project_id:
            url = f"{BASE_URL}/projects/{project_id}/time_entries.json"
        else:
            url = f"{BASE_URL}/time_entries.json"
        
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if page > 1:
            params["page"] = page
            
        return await self.make_request(url, params=params)
    
    async def get_all_time_entries(self, project_id: int = None, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """Get all time entries across pages"""
        all_entries = []
        page = 1
        while True:
            entries = await self.get_time_entries(project_id, start_date, end_date, page)
            if not entries:
                break
            all_entries.extend(entries)
            page += 1
        return all_entries
    
    async def create_time_entry(self, project_id: int, task_id: int, hours: float, date: str, notes: str = "") -> Dict[str, Any]:
        """Create a new time entry"""
        url = f"{BASE_URL}/projects/{project_id}/time_entries.json"
        data = {
            "task_id": task_id,
            "hours": hours,
            "date": date,
            "notes": notes
        }
        return await self.make_request(url, "POST", data)
    
    async def update_time_entry(self, entry_id: int, hours: float = None, notes: str = None) -> Dict[str, Any]:
        """Update an existing time entry"""
        url = f"{BASE_URL}/time_entries/{entry_id}.json"
        data = {}
        if hours is not None:
            data["hours"] = hours
        if notes is not None:
            data["notes"] = notes
        return await self.make_request(url, "PUT", data)
    
    async def delete_time_entry(self, entry_id: int) -> Dict[str, Any]:
        """Delete a time entry"""
        url = f"{BASE_URL}/time_entries/{entry_id}.json"
        return await self.make_request(url, "DELETE")
    
    async def get_tasks(self, project_id: int) -> List[Dict[str, Any]]:
        """Get tasks for a project"""
        url = f"{BASE_URL}/projects/{project_id}/tasks.json"
        return await self.make_request(url)
    
    async def get_clients(self) -> List[Dict[str, Any]]:
        """Get all clients"""
        url = f"{BASE_URL}/clients.json"
        return await self.make_request(url)
    
    async def get_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        url = f"{BASE_URL}/users.json"
        return await self.make_request(url)

# Initialize API client
tick_api = TickAPI()

@mcp.tool()
async def get_time_entries(
    project: str = None,
    start_date: str = None,
    end_date: str = None
) -> Dict[str, Any]:
    """
    Get time entries with optional filters.
    
    Args:
        project: Project name (optional, partial match, case insensitive)
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
    
    Returns:
        Dictionary containing time entries and summary information
    """
    try:
        # Validate dates if provided
        if start_date:
            datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}
    
    try:
        project_id = None
        if project:
            project_id = await tick_api.find_project_id(project)
            if not project_id:
                projects = await tick_api.get_all_projects()
                available_projects = [p["name"] for p in projects]
                return {
                    "error": f"Project '{project}' not found",
                    "available_projects": available_projects
                }
        
        # Get time entries
        entries = await tick_api.get_all_time_entries(project_id, start_date, end_date)
        
        # Calculate summary
        total_hours = sum(entry.get("hours", 0) for entry in entries)
        total_entries = len(entries)
        
        # Group by user
        user_hours = {}
        for entry in entries:
            user_name = entry.get("user", {}).get("first_name", "Unknown")
            user_hours[user_name] = user_hours.get(user_name, 0) + entry.get("hours", 0)
        
        return {
            "project": project or "All projects",
            "project_id": project_id,
            "date_range": f"{start_date or 'beginning'} to {end_date or 'now'}",
            "total_entries": total_entries,
            "total_hours": total_hours,
            "hours_by_user": user_hours,
            "entries": entries
        }
        
    except Exception as e:
        return {"error": f"Failed to fetch time entries: {str(e)}"}

@mcp.tool()
async def create_time_entry(
    project: str,
    task: str,
    hours: float,
    date: str,
    notes: str = ""
) -> Dict[str, Any]:
    """
    Create a new time entry.
    
    Args:
        project: Project name (partial match, case insensitive)
        task: Task name (partial match, case insensitive)
        hours: Number of hours (can be decimal, e.g., 2.5)
        date: Date in YYYY-MM-DD format
        notes: Optional notes for the time entry
    
    Returns:
        Dictionary containing the created time entry or error message
    """
    try:
        # Validate date format
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}
    
    try:
        # Find project
        project_id = await tick_api.find_project_id(project)
        if not project_id:
            return {"error": f"Project '{project}' not found"}
        
        # Get tasks for project
        tasks = await tick_api.get_tasks(project_id)
        task_id = None
        for t in tasks:
            if task.lower() in t["name"].lower():
                task_id = t["id"]
                break
        
        if not task_id:
            available_tasks = [t["name"] for t in tasks]
            return {
                "error": f"Task '{task}' not found in project '{project}'",
                "available_tasks": available_tasks
            }
        
        # Create time entry
        result = await tick_api.create_time_entry(project_id, task_id, hours, date, notes)
        
        return {
            "success": True,
            "message": f"Created {hours} hour entry for {project} - {task}",
            "entry": result
        }
        
    except Exception as e:
        return {"error": f"Failed to create time entry: {str(e)}"}

@mcp.tool()
async def update_time_entry(
    entry_id: int,
    hours: float = None,
    notes: str = None
) -> Dict[str, Any]:
    """
    Update an existing time entry.
    
    Args:
        entry_id: ID of the time entry to update
        hours: New number of hours (optional)
        notes: New notes (optional)
    
    Returns:
        Dictionary containing the updated time entry or error message
    """
    try:
        if hours is None and notes is None:
            return {"error": "Must provide either hours or notes to update"}
        
        result = await tick_api.update_time_entry(entry_id, hours, notes)
        
        return {
            "success": True,
            "message": f"Updated time entry {entry_id}",
            "entry": result
        }
        
    except Exception as e:
        return {"error": f"Failed to update time entry: {str(e)}"}

@mcp.tool()
async def delete_time_entry(entry_id: int) -> Dict[str, Any]:
    """
    Delete a time entry.
    
    Args:
        entry_id: ID of the time entry to delete
    
    Returns:
        Dictionary containing success message or error
    """
    try:
        await tick_api.delete_time_entry(entry_id)
        
        return {
            "success": True,
            "message": f"Deleted time entry {entry_id}"
        }
        
    except Exception as e:
        return {"error": f"Failed to delete time entry: {str(e)}"}

@mcp.tool()
async def list_projects() -> Dict[str, Any]:
    """
    Get all available projects from Tick.
    
    Returns:
        Dictionary containing list of projects with their details
    """
    try:
        projects = await tick_api.get_all_projects()
        
        # Calculate totals
        total_budget = sum(p.get("budget", 0) for p in projects)
        total_hours = sum(p.get("hours", 0) for p in projects)
        
        return {
            "total_projects": len(projects),
            "total_budget": total_budget,
            "total_hours_logged": total_hours,
            "projects": [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "client": p.get("client", {}).get("name", "No client"),
                    "budget": p.get("budget", 0),
                    "hours_used": p.get("hours", 0),
                    "budget_remaining": p.get("budget", 0) - p.get("hours", 0),
                    "is_closed": p.get("closed", False),
                    "owner": p.get("owner", {}).get("first_name", "Unknown")
                }
                for p in projects
            ]
        }
    except Exception as e:
        return {"error": f"Failed to fetch projects: {str(e)}"}

@mcp.tool()
async def get_project_tasks(project: str) -> Dict[str, Any]:
    """
    Get all tasks for a specific project.
    
    Args:
        project: Project name (partial match, case insensitive)
    
    Returns:
        Dictionary containing project tasks
    """
    try:
        project_id = await tick_api.find_project_id(project)
        if not project_id:
            return {"error": f"Project '{project}' not found"}
        
        tasks = await tick_api.get_tasks(project_id)
        
        return {
            "project": project,
            "project_id": project_id,
            "total_tasks": len(tasks),
            "tasks": [
                {
                    "id": t["id"],
                    "name": t["name"],
                    "budget": t.get("budget", 0),
                    "hours_used": t.get("sum_hours", 0),
                    "is_closed": t.get("closed", False)
                }
                for t in tasks
            ]
        }
        
    except Exception as e:
        return {"error": f"Failed to fetch project tasks: {str(e)}"}

@mcp.tool()
async def get_time_summary_by_period(
    period: str = "week",
    start_date: str = None
) -> Dict[str, Any]:
    """
    Get time tracking summary for a specific period.
    
    Args:
        period: Period type - "week", "month", or "day" (default: week)
        start_date: Start date in YYYY-MM-DD format (optional, defaults to current period)
    
    Returns:
        Dictionary containing time summary for the period
    """
    try:
        today = datetime.now()
        
        if period == "day":
            if start_date:
                target_date = datetime.strptime(start_date, "%Y-%m-%d")
            else:
                target_date = today
            start = end = target_date.strftime("%Y-%m-%d")
            
        elif period == "week":
            if start_date:
                target_date = datetime.strptime(start_date, "%Y-%m-%d")
            else:
                target_date = today
            # Get start of week (Monday)
            start_of_week = target_date - timedelta(days=target_date.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            start = start_of_week.strftime("%Y-%m-%d")
            end = end_of_week.strftime("%Y-%m-%d")
            
        elif period == "month":
            if start_date:
                target_date = datetime.strptime(start_date, "%Y-%m-%d")
            else:
                target_date = today
            start = target_date.replace(day=1).strftime("%Y-%m-%d")
            # Get last day of month
            if target_date.month == 12:
                next_month = target_date.replace(year=target_date.year + 1, month=1, day=1)
            else:
                next_month = target_date.replace(month=target_date.month + 1, day=1)
            end = (next_month - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            return {"error": "Period must be 'day', 'week', or 'month'"}
        
        # Get time entries for period
        entries = await tick_api.get_all_time_entries(start_date=start, end_date=end)
        
        # Analyze data
        total_hours = sum(entry.get("hours", 0) for entry in entries)
        
        # Group by project
        project_hours = {}
        for entry in entries:
            project_name = entry.get("project", {}).get("name", "Unknown")
            project_hours[project_name] = project_hours.get(project_name, 0) + entry.get("hours", 0)
        
        # Group by date
        daily_hours = {}
        for entry in entries:
            entry_date = entry.get("date", "Unknown")
            daily_hours[entry_date] = daily_hours.get(entry_date, 0) + entry.get("hours", 0)
        
        return {
            "period": period,
            "date_range": f"{start} to {end}",
            "total_hours": total_hours,
            "total_entries": len(entries),
            "average_hours_per_day": total_hours / max(1, len(daily_hours)),
            "hours_by_project": dict(sorted(project_hours.items(), key=lambda x: x[1], reverse=True)),
            "hours_by_date": daily_hours
        }
        
    except Exception as e:
        return {"error": f"Failed to get time summary: {str(e)}"}

@mcp.tool()
async def list_clients() -> Dict[str, Any]:
    """
    Get all clients with their project information.
    
    Returns:
        Dictionary containing list of clients and their details
    """
    try:
        clients = await tick_api.get_clients()
        projects = await tick_api.get_all_projects()
        
        # Group projects by client
        client_projects = {}
        for project in projects:
            client_id = project.get("client", {}).get("id")
            if client_id:
                if client_id not in client_projects:
                    client_projects[client_id] = []
                client_projects[client_id].append(project)
        
        enriched_clients = []
        for client in clients:
            client_id = client["id"]
            client_project_list = client_projects.get(client_id, [])
            total_budget = sum(p.get("budget", 0) for p in client_project_list)
            total_hours = sum(p.get("hours", 0) for p in client_project_list)
            
            enriched_clients.append({
                "id": client_id,
                "name": client["name"],
                "project_count": len(client_project_list),
                "total_budget": total_budget,
                "total_hours_logged": total_hours,
                "projects": [p["name"] for p in client_project_list]
            })
        
        return {
            "total_clients": len(clients),
            "clients": enriched_clients
        }
        
    except Exception as e:
        return {"error": f"Failed to fetch clients: {str(e)}"}

@mcp.tool()
async def get_team_overview() -> Dict[str, Any]:
    """
    Get an overview of team members and their recent activity.
    
    Returns:
        Dictionary containing team member information and recent activity
    """
    try:
        users = await tick_api.get_users()
        
        # Get recent time entries (last 7 days)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        recent_entries = await tick_api.get_all_time_entries(start_date=start_date, end_date=end_date)
        
        # Calculate user activity
        user_activity = {}
        for entry in recent_entries:
            user_id = entry.get("user", {}).get("id")
            if user_id:
                if user_id not in user_activity:
                    user_activity[user_id] = {"hours": 0, "entries": 0}
                user_activity[user_id]["hours"] += entry.get("hours", 0)
                user_activity[user_id]["entries"] += 1
        
        # Enrich user data
        enriched_users = []
        for user in users:
            user_id = user["id"]
            activity = user_activity.get(user_id, {"hours": 0, "entries": 0})
            
            enriched_users.append({
                "id": user_id,
                "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                "email": user.get("email", ""),
                "recent_hours_7_days": activity["hours"],
                "recent_entries_7_days": activity["entries"],
                "timezone": user.get("timezone", ""),
                "is_active": activity["hours"] > 0
            })
        
        total_recent_hours = sum(activity["hours"] for activity in user_activity.values())
        active_users = len([u for u in enriched_users if u["is_active"]])
        
        return {
            "total_users": len(users),
            "active_users_last_7_days": active_users,
            "total_hours_last_7_days": total_recent_hours,
            "average_hours_per_active_user": total_recent_hours / max(1, active_users),
            "users": enriched_users
        }
        
    except Exception as e:
        return {"error": f"Failed to fetch team overview: {str(e)}"}

# Add helper functions for Google Sheets integration
@mcp.tool()
async def get_time_entries_for_sheets(
    project: str = None,
    start_date: str = None,
    end_date: str = None,
    format_for_sheets: bool = True
) -> Dict[str, Any]:
    """
    Get time entries formatted specifically for Google Sheets import.
    Returns data in a format that can be easily written to sheets.
    
    Args:
        project: Project name (optional, partial match, case insensitive)
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        format_for_sheets: Whether to format data for sheets (default: True)
    
    Returns:
        Dictionary containing formatted data for sheets import
    """
    try:
        # Get time entries using existing function
        result = await get_time_entries(project, start_date, end_date)
        
        if "error" in result:
            return result
        
        if not format_for_sheets:
            return result
        
        # Format for sheets - create 2D array structure
        headers = ["Date", "Project", "Task", "User", "Hours", "Notes", "Client"]
        rows = [headers]
        
        for entry in result.get("entries", []):
            row = [
                entry.get("date", ""),
                entry.get("project", {}).get("name", ""),
                entry.get("task", {}).get("name", ""),
                f"{entry.get('user', {}).get('first_name', '')} {entry.get('user', {}).get('last_name', '')}".strip(),
                entry.get("hours", 0),
                entry.get("notes", ""),
                entry.get("project", {}).get("client", {}).get("name", "")
            ]
            rows.append(row)
        
        return {
            "success": True,
            "sheet_data": rows,
            "total_rows": len(rows),
            "headers": headers,
            "summary": {
                "total_entries": result.get("total_entries", 0),
                "total_hours": result.get("total_hours", 0),
                "date_range": result.get("date_range", ""),
                "project": result.get("project", "")
            }
        }
        
    except Exception as e:
        return {"error": f"Failed to format time entries for sheets: {str(e)}"}

if __name__ == "__main__":
    mcp.run()