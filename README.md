# MCP Tick API Server Setup

This is an MCP-compatible server that connects Claude Desktop to the [Tick time tracking API](https://github.com/tick/tick-api).

## Features
- Get time entries by project and date range
- Create, update, and delete time entries
- List all projects with budget and hours tracking
- Get project tasks and task management
- Time summary reports by day/week/month
- Client management and overview
- Team member activity tracking
- Comprehensive error handling and validation
- Full pagination support for large datasets
- Async HTTP requests for better performance

## Requirements
- Python 3.9+
- Tick API token and subdomain
- Claude Desktop

## Setup Instructions

### 1. Clone/Create Project Directory
```bash
mkdir tick-mcp-server
cd tick-mcp-server
```

### 2. Create Virtual Environment (Recommended)
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Get Your Tick API Credentials
1. Log into your Tick account
2. Go to Settings → API
3. Generate an API token
4. Note your subdomain (the part before `.tickspot.com` in your URL)

### 5. Configure Environment Variables

#### Option A: Export in terminal
```bash
export TICK_API_TOKEN="your-actual-token-here"
export TICK_SUBDOMAIN="your-subdomain"
```

#### Option B: Create a `.env` file (optional)
```bash
# .env
TICK_API_TOKEN=your-actual-token-here
TICK_SUBDOMAIN=your-subdomain
```

### 6. Test the Server
```bash
python3 main.py
```

### 7. Configure Claude Desktop

#### Find your Claude Desktop config file location:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

#### Update the config file:
Replace `/path/to/your/project/main.py` with the actual full path to your main.py file.

### 8. Restart Claude Desktop
Close and reopen Claude Desktop to load the new MCP server.

## Available Tools

Once connected, Claude will have access to these comprehensive tools:

### Time Entry Management
1. **`get_time_entries`** - Get time entries with optional filters
   - project: Project name (optional, partial match)
   - start_date: Start date in YYYY-MM-DD format (optional)
   - end_date: End date in YYYY-MM-DD format (optional)

2. **`create_time_entry`** - Create a new time entry
   - project: Project name (partial match)
   - task: Task name (partial match)
   - hours: Number of hours (decimal allowed)
   - date: Date in YYYY-MM-DD format
   - notes: Optional notes

3. **`update_time_entry`** - Update an existing time entry
   - entry_id: ID of the time entry
   - hours: New hours (optional)
   - notes: New notes (optional)

4. **`delete_time_entry`** - Delete a time entry
   - entry_id: ID of the time entry to delete

### Project & Task Management
5. **`list_projects`** - Get all projects with budget tracking and client info

6. **`get_project_tasks`** - Get all tasks for a specific project
   - project: Project name (partial match)

### Reporting & Analytics
7. **`get_time_summary_by_period`** - Get time tracking summary for periods
   - period: "day", "week", or "month"
   - start_date: Optional start date (defaults to current period)

8. **`list_clients`** - Get all clients with their project information

9. **`get_team_overview`** - Get team member activity and recent work summary

## Usage Examples

After setup, you can ask Claude:

### Time Tracking
- "Show me all time entries for this week"
- "Create a 2.5 hour entry for the Marketing project, Development task, for today"
- "Get time entries for Project ABC from 2024-01-01 to 2024-01-31"
- "Update time entry 12345 to 3 hours with notes 'Fixed login bug'"
- "Delete time entry 12345"

### Project Management  
- "Show me all my Tick projects with their budgets"
- "What tasks are available for the Website project?"
- "List all clients and their project counts"

### Reporting & Analytics
- "Give me a time summary for this month"
- "Show team activity for the last week"
- "What's the total hours logged across all projects this week?"
- "Which projects have the most hours logged?"

### Team Management
- "Show me team overview with recent activity"
- "Who has been most active in time tracking this week?"

## Troubleshooting

### Common Issues:

1. **"Environment variables not found"**
   - Make sure TICK_API_TOKEN and TICK_SUBDOMAIN are set
   - Check spelling and format

2. **"Project not found"**
   - Use `list_projects` first to see available projects
   - Project name matching is case-insensitive and partial

3. **"Authentication failed"**
   - Verify your API token is correct
   - Check your subdomain matches your Tick URL

4. **Claude doesn't see the tools**
   - Ensure the path in claude_desktop_config.json is correct
   - Restart Claude Desktop after config changes
   - Check that Python can run the script without errors

### Testing Connection:
```bash
# Test if your credentials work
python3 -c "
import os
import requests
token = os.environ['TICK_API_TOKEN']
subdomain = os.environ['TICK_SUBDOMAIN']
resp = requests.get(f'https://{subdomain}.tickspot.com/api/v2/projects.json', 
                   headers={'Authorization': f'Token token={token}'})
print(f'Status: {resp.status_code}')
print(f'Projects found: {len(resp.json()) if resp.status_code == 200 else \"Error\"}')"
```

## Security Notes
- Keep your API token secure and never commit it to version control
- Consider using environment variables or a secure secrets manager
- The token has access to all your Tick data, so treat it like a password

## API Rate Limits
Tick API has rate limits. The server includes appropriate headers and error handling, but be mindful of making too many rapid requests.