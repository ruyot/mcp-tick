import os
import requests
from fastmcp import Server, call, Capability

TICK_API_TOKEN = os.environ["TICK_API_TOKEN"]
TICK_SUBDOMAIN = os.environ["TICK_SUBDOMAIN"]

BASE_URL = f"https://{TICK_SUBDOMAIN}.tickspot.com/api/v2"

server = Server()

@server.capability("tick.getTimeEntries")
class GetTimeEntries(Capability):
    async def call(self, project: str, start_date: str, end_date: str):
        headers = {
            "Authorization": f"Token token={TICK_API_TOKEN}",
            "User-Agent": "MCP-Tick-Client"
        }

        # Get list of projects to find the project ID
        proj_resp = requests.get(f"{BASE_URL}/projects.json", headers=headers)
        proj_resp.raise_for_status()
        projects = proj_resp.json()
        project_id = next(
            (p["id"] for p in projects if project.lower() in p["name"].lower()), None
        )

        if not project_id:
            return {"error": f"Project '{project}' not found."}

        # Get time entries
        time_url = f"{BASE_URL}/projects/{project_id}/time_entries.json?start_date={start_date}&end_date={end_date}"
        time_resp = requests.get(time_url, headers=headers)
        time_resp.raise_for_status()

        return {
            "entries": time_resp.json()
        }

server.run()
