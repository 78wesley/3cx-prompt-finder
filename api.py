import orjson
import httpx
from typing import Optional


class APIClient:
    """Small wrapper around httpx for the 3CX XAPI used by the project.

    Notes:
    - `token` should be a JWT/Bearer token.
    - `fqdn` should be the hostname (without scheme) or full host:port; scheme is added.
    """

    def __init__(self, token: str, fqdn: str):
        self.token = token
        if token.startswith("Bearer "):
            self.token = token[len("Bearer ") :]
        # Use correct standard header names and values
        headers = {"Accept": "application/json", "Authorization": f"Bearer {self.token}"}
        self.client = httpx.Client(headers=headers, timeout=30.0)
        self.fqdn = f"https://{fqdn}"
        if self.fqdn.endswith("/"):
            self.fqdn = self.fqdn[:-1]

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        response = self.client.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def custom_prompts(self) -> Optional[dict]:
        params = {"$select": "DisplayName"}
        response = self.request("GET", f"{self.fqdn}/xapi/v1/CustomPrompts", params=params)
        return orjson.loads(response.content)

    def playlists(self) -> Optional[dict]:
        params = {"$select": "Name,Files"}
        response = self.request("GET", f"{self.fqdn}/xapi/v1/Playlists", params=params)
        return orjson.loads(response.content)

    def receptionists(self) -> Optional[dict]:
        params = {"$select": "Name,Number,PromptFilename", "$expand": "Forwards($select=Input,CustomData)"}
        response = self.request("GET", f"{self.fqdn}/xapi/v1/Receptionists", params=params)
        return orjson.loads(response.content)

    def queues(self) -> Optional[dict]:
        params = {
            "$select": "Name,Number,IntroFile,OnHoldFile,GreetingFile,HolidaysRoute/Prompt,OutOfOfficeRoute/Prompt,BreakRoute/Prompt",
        }
        response = self.request("GET", f"{self.fqdn}/xapi/v1/Queues", params=params)
        return orjson.loads(response.content)

    def groups(self) -> Optional[dict]:
        params = {"$select": "Name,Number,OfficeRoute/Prompt,OutOfOfficeRoute/Prompt,BreakRoute/Prompt,HolidaysRoute/Prompt", "$filter": "not startsWith(Name, '___FAVORITES___')"}
        response = self.request("GET", f"{self.fqdn}/xapi/v1/Groups", params=params)
        return orjson.loads(response.content)

    def conference_settings(self) -> Optional[dict]:
        params = {"$select": "Extension,MusicOnHold"}
        response = self.request("GET", f"{self.fqdn}/xapi/v1/ConferenceSettings", params=params)
        return orjson.loads(response.content)

    def emergency_notifications_settings(self) -> Optional[dict]:
        params = {"$select": "EmergencyPlayPrompt"}
        response = self.request("GET", f"{self.fqdn}/xapi/v1/EmergencyNotificationsSettings", params=params)
        return orjson.loads(response.content)

    def call_parking_settings(self) -> Optional[dict]:
        params = {"$select": "MusicOnHold"}
        response = self.request("GET", f"{self.fqdn}/xapi/v1/CallParkingSettings", params=params)
        return orjson.loads(response.content)

    def call_flow_apps(self) -> Optional[dict]:
        params = {"$select": "Id,Name,Number"}
        response = self.request("GET", f"{self.fqdn}/xapi/v1/CallFlowApps", params=params)

        content = orjson.loads(response.content)

        # For each call flow app, fetch the files via the GetFiles action
        for item in content.get("value", []):
            item_id = item.get("Id")
            if item_id is None:
                item["Files"] = []
                continue
            files_response = self.request("GET", f"{self.fqdn}/xapi/v1/CallFlowApps({item_id})/Pbx.GetFiles()")
            files_content = orjson.loads(files_response.content)
            item["Files"] = files_content.get("value", [])

        return content

    def music_on_hold_settings(self) -> Optional[dict]:
        params = {"$select": ",".join([f"MusicOnHold{i}" for i in range(10)])}
        response = self.request("GET", f"{self.fqdn}/xapi/v1/MusicOnHoldSettings", params=params)
        return orjson.loads(response.content)
