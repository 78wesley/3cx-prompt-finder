import os
import shutil
from typing import Dict, List, Optional
import orjson
import api
import argparse
from dotenv import load_dotenv

load_dotenv()


def load_json_file(path: str) -> Optional[dict]:
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return orjson.loads(f.read())


def gather_prompt_usages(
    prompt_filenames: set,
    receptionists: dict,
    queues: dict,
    groups: dict,
    music_on_hold_settings: dict,
    conference_settings: dict,
    call_parking_settings: dict,
) -> Dict[str, List[str]]:
    """Return a mapping filename -> list of human-readable usage descriptions."""
    usages: Dict[str, List[str]] = {fn: [] for fn in prompt_filenames}

    # Helpers to add usage
    def add(fn: str, text: str) -> None:
        if fn in usages:
            usages[fn].append(text)

    # Receptionists
    for item in (receptionists or {}).get("value", []):
        filename = item.get("PromptFilename")
        if filename and filename in prompt_filenames:
            add(filename, f"Receptionist: {item.get('Number')} {item.get('Name')}")

        for forward in item.get("Forwards", []):
            custom_data = forward.get("CustomData")
            if custom_data and custom_data in prompt_filenames:
                add(custom_data, f"Receptionist (forward key): {item.get('Number')} {item.get('Name')}")

    # Queues: direct file fields and route prompts
    queue_file_keys = ["IntroFile", "OnHoldFile", "GreetingFile"]
    route_keys = ["OutOfOfficeRoute", "BreakRoute", "HolidaysRoute"]

    for item in (queues or {}).get("value", []):
        for key in queue_file_keys:
            value = item.get(key)
            if value and value in prompt_filenames:
                add(value, f"Queue {key}: {item.get('Number')} {item.get('Name')}")

        for rkey in route_keys:
            route = item.get(rkey, {}) or {}
            prompt = route.get("Prompt")
            if prompt and prompt in prompt_filenames:
                add(prompt, f"Queue route {rkey}: {item.get('Number')} {item.get('Name')}")

    # Groups routes
    group_route_keys = ["OfficeRoute", "OutOfOfficeRoute", "BreakRoute", "HolidaysRoute"]
    for item in (groups or {}).get("value", []):
        for rkey in group_route_keys:
            route = item.get(rkey, {}) or {}
            prompt = route.get("Prompt")
            if prompt and prompt in prompt_filenames:
                add(prompt, f"Group route {rkey}: {item.get('Number')} {item.get('Name')}")

    # Music on hold settings (look for keys starting with MusicOnHold)
    for key, value in (music_on_hold_settings or {}).items():
        if value and value in prompt_filenames:
            add(value, f"MusicOnHold setting ({key})")

    # Conference settings
    conf_moh = (conference_settings or {}).get("MusicOnHold")
    if conf_moh and conf_moh in prompt_filenames:
        add(conf_moh, "Conference: MusicOnHold")

    # Call parking
    cps_moh = (call_parking_settings or {}).get("MusicOnHold")
    if cps_moh and cps_moh in prompt_filenames:
        add(cps_moh, "CallParking: MusicOnHold")

    # Remove filenames with no usages
    usages = {k: v for k, v in usages.items() if v}
    return usages


def print_report(usages: Dict[str, List[str]]) -> None:
    if not usages:
        print("No prompt files in use were found.")
        return

    print("Detailed list of used prompt filenames:")
    for filename in sorted(usages.keys()):
        print(f"\n{filename}:")
        for entry in usages[filename]:
            print(f"  - {entry}")

    print("\nUsed prompt filenames:")
    for filename in sorted(usages.keys()):
        print(f" - {filename}")


def print_call_flow_apps(client: api.APIClient) -> None:
    call_flow_apps = client.call_flow_apps() or {"value": []}
    print("\nCall Flow Apps Files:")
    for item in call_flow_apps.get("value", []):
        if not item.get("Files") == []:
            print(f"{item.get('Number')} {item.get('Name')}:")
            for file in item.get("Files", []):
                print(f"  - File: {file}")

    call_flow_apps = client.call_flow_apps() or {"value": []}


def report_from_output(output_dir: str = "output") -> None:
    # load files from output/ (if present)
    def ld(fname: str):
        return load_json_file(os.path.join(output_dir, fname)) or {}

    prompts = ld("custom_prompts.json") or {"value": []}
    receptionists = ld("receptionists.json") or {"value": []}
    queues = ld("queues.json") or {"value": []}
    groups = ld("groups.json") or {"value": []}
    playlists = ld("playlists.json") or {"value": []}
    music_on_hold_settings = ld("music_on_hold_settings.json") or {}
    conference_settings = ld("conference_settings.json") or {}
    call_parking_settings = ld("call_parking_settings.json") or {}

    prompt_filenames = {p.get("DisplayName") for p in prompts.get("value", []) if p.get("DisplayName")}
    usages = gather_prompt_usages(
        prompt_filenames,
        receptionists,
        queues,
        groups,
        music_on_hold_settings,
        conference_settings,
        call_parking_settings,
    )

    print_report(usages)


def report_from_api(client: api.APIClient) -> None:
    prompts = client.custom_prompts() or {"value": []}
    receptionists = client.receptionists() or {"value": []}
    queues = client.queues() or {"value": []}
    groups = client.groups() or {"value": []}
    playlists = client.playlists() or {"value": []}
    conference_settings = client.conference_settings() or {}
    music_on_hold_settings = client.music_on_hold_settings() or {}
    call_parking_settings = client.call_parking_settings() or {}
    call_flow_apps = client.call_flow_apps() or {"value": []}

    os.makedirs("output", exist_ok=True)
    with open("output/custom_prompts.json", "wb") as f:
        f.write(orjson.dumps(prompts, option=orjson.OPT_INDENT_2))
    with open("output/playlists.json", "wb") as f:
        f.write(orjson.dumps(playlists, option=orjson.OPT_INDENT_2))
    with open("output/receptionists.json", "wb") as f:
        f.write(orjson.dumps(receptionists, option=orjson.OPT_INDENT_2))
    with open("output/queues.json", "wb") as f:
        f.write(orjson.dumps(queues, option=orjson.OPT_INDENT_2))
    with open("output/groups.json", "wb") as f:
        f.write(orjson.dumps(groups, option=orjson.OPT_INDENT_2))
    with open("output/conference_settings.json", "wb") as f:
        f.write(orjson.dumps(conference_settings, option=orjson.OPT_INDENT_2))
    with open("output/music_on_hold_settings.json", "wb") as f:
        f.write(orjson.dumps(music_on_hold_settings, option=orjson.OPT_INDENT_2))
    with open("output/call_parking_settings.json", "wb") as f:
        f.write(orjson.dumps(call_parking_settings, option=orjson.OPT_INDENT_2))
    with open("output/call_flow_apps.json", "wb") as f:
        f.write(orjson.dumps(call_flow_apps, option=orjson.OPT_INDENT_2))

    prompt_filenames = {p.get("DisplayName") for p in prompts.get("value", []) if p.get("DisplayName")}

    usages = gather_prompt_usages(
        prompt_filenames,
        receptionists,
        queues,
        groups,
        music_on_hold_settings,
        conference_settings,
        call_parking_settings,
    )

    print_report(usages)
    print_call_flow_apps(client)


def main():
    output_dir = "output"
    if os.path.isdir(output_dir) and os.path.exists(os.path.join(output_dir, "custom_prompts.json")):
        report_from_output(output_dir)
        return

    fqdn = os.environ.get("FQDN")
    token = os.environ.get("BEARER_TOKEN")
    if not token:
        token = ""

    client = api.APIClient(token=token, fqdn=fqdn)
    report_from_api(client)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="3CX Prompt Usage Reporter")
    parser.add_argument("--clear", action="store_true", help="Clear the output directory before running")
    args = parser.parse_args()

    if args.clear:
        if os.path.isdir("output"):
            shutil.rmtree("output")

    main()
