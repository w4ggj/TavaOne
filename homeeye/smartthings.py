"""
SmartThings Integration for HomeEye
Handles voice commands to control smart home devices via SmartThings API.
Author: Built for W4GGJ / Joe
"""

import urllib.request
import urllib.error
import json
import re

# ── Device map ────────────────────────────────────────────────────────────────
DEVICES = {
    # Lights - Indoor
    "living room light":   "ad212345-6112-4f99-941f-c16c4d8e70e5",
    "living room":         "ad212345-6112-4f99-941f-c16c4d8e70e5",
    "hall lights":         "665c2fe0-7ba5-4bf0-afa8-1b39a1c8eb0d",
    "hall light":          "665c2fe0-7ba5-4bf0-afa8-1b39a1c8eb0d",
    "office light":        "1aed10d7-f41c-46a4-a2c2-4010f193f712",
    "office":              "1aed10d7-f41c-46a4-a2c2-4010f193f712",
    "kinkade":             "b8555dd9-7f4d-4f9b-983c-55c3f227c513",
    "kinkade 1":           "b8555dd9-7f4d-4f9b-983c-55c3f227c513",
    "kinkade 2":           "d831a1fa-acbb-40c3-a71a-621a00f19a49",
    "kinkade light":       "49b1106f-fd21-4add-8e79-d9277dde9d0f",
    "smart light 1":       "560745f4-5d30-4f94-96e5-e43af3582bb3",
    "smart light 2":       "b4c09514-f82a-4930-b299-178a77f8e153",
    "smart light 3":       "d2527491-ea77-4ea4-acfd-d72491df166c",
    "smart light 4":       "19c6faba-cdef-4f9b-acf5-b7cf807f0836",
    "tree lights":         "044148fa-6c7c-4b17-8eee-206d71a9f6f5",
    "tree light":          "044148fa-6c7c-4b17-8eee-206d71a9f6f5",
    "on air":              "229ec1af-4566-4d8b-a4bf-23bd4679c7a4",
    "on air light":        "229ec1af-4566-4d8b-a4bf-23bd4679c7a4",

    # Lights - Outdoor
    "porch light":         "1ca274a2-e73c-4055-9a13-6465ee302ac4",
    "porch":               "1ca274a2-e73c-4055-9a13-6465ee302ac4",
    "side light":          "afa51630-2007-4060-ba93-803b181589ee",
    "outdoor bottom":      "b7bce37f-7d62-42bc-8488-a6692b8d7f6f",
    "outdoor top":         "68107635-c833-4963-a51f-a24611821a72",
    "outdoor lights":      ["b7bce37f-7d62-42bc-8488-a6692b8d7f6f",
                            "68107635-c833-4963-a51f-a24611821a72"],
    "fence lights":        ["ac76fdcc-3117-4df9-abe7-fcd5366d99a6",
                            "18fe4aca-b0f6-494f-90a0-313a14e4fbb2"],
    "fence lights 1":      "18fe4aca-b0f6-494f-90a0-313a14e4fbb2",
    "fence lights 2":      "ac76fdcc-3117-4df9-abe7-fcd5366d99a6",
    "christmas lights":    "5fef7ac8-26b3-47d9-a2db-bbf462d37063",
    "xmas lights":         "5fef7ac8-26b3-47d9-a2db-bbf462d37063",
    "house lights":        "5fef7ac8-26b3-47d9-a2db-bbf462d37063",

    # Plugs
    "3d printer":          "4e0e1d40-782c-42ef-b606-95353e03da7d",
    "ender":               "4e0e1d40-782c-42ef-b606-95353e03da7d",
    "smart plug":          "43e6a353-ca31-419e-8a0b-26a40d19a6b7",

    # TV
    "tv":                  "b74db686-75ee-4e1e-9c3f-b0e5e07aa969",
    "samsung tv":          "b74db686-75ee-4e1e-9c3f-b0e5e07aa969",
    "television":          "b74db686-75ee-4e1e-9c3f-b0e5e07aa969",

    # Doors
    "front door":          "0488a0f4-4b90-4868-b895-260c8ecfd4f8",
    "side door":           "716a626d-18ae-4e5a-ae84-9a348e40d092",

    # Groups
    "garden lights":       [
                            "560745f4-5d30-4f94-96e5-e43af3582bb3",
                            "b4c09514-f82a-4930-b299-178a77f8e153",
                            "d2527491-ea77-4ea4-acfd-d72491df166c",
                            "19c6faba-cdef-4f9b-acf5-b7cf807f0836",
                        ],
    "garden":              [
                            "560745f4-5d30-4f94-96e5-e43af3582bb3",
                            "b4c09514-f82a-4930-b299-178a77f8e153",
                            "d2527491-ea77-4ea4-acfd-d72491df166c",
                            "19c6faba-cdef-4f9b-acf5-b7cf807f0836",
                        ],
    "all lights":          [
                            "ad212345-6112-4f99-941f-c16c4d8e70e5",
                            "665c2fe0-7ba5-4bf0-afa8-1b39a1c8eb0d",
                            "1aed10d7-f41c-46a4-a2c2-4010f193f712",
                            "1ca274a2-e73c-4055-9a13-6465ee302ac4",
                            "afa51630-2007-4060-ba93-803b181589ee",
                            "b8555dd9-7f4d-4f9b-983c-55c3f227c513",
                            "d831a1fa-acbb-40c3-a71a-621a00f19a49",
                            "49b1106f-fd21-4add-8e79-d9277dde9d0f",
                            "b7bce37f-7d62-42bc-8488-a6692b8d7f6f",
                            "68107635-c833-4963-a51f-a24611821a72",
                            "ac76fdcc-3117-4df9-abe7-fcd5366d99a6",
                            "18fe4aca-b0f6-494f-90a0-313a14e4fbb2",
                            "560745f4-5d30-4f94-96e5-e43af3582bb3",
                            "b4c09514-f82a-4930-b299-178a77f8e153",
                            "d2527491-ea77-4ea4-acfd-d72491df166c",
                            "19c6faba-cdef-4f9b-acf5-b7cf807f0836",
                            "044148fa-6c7c-4b17-8eee-206d71a9f6f5",
                            "229ec1af-4566-4d8b-a4bf-23bd4679c7a4",
                        ],
    "all outdoor lights":  [
                            "1ca274a2-e73c-4055-9a13-6465ee302ac4",
                            "afa51630-2007-4060-ba93-803b181589ee",
                            "b7bce37f-7d62-42bc-8488-a6692b8d7f6f",
                            "68107635-c833-4963-a51f-a24611821a72",
                            "ac76fdcc-3117-4df9-abe7-fcd5366d99a6",
                            "18fe4aca-b0f6-494f-90a0-313a14e4fbb2",
                        ],
    "all indoor lights":   [
                            "ad212345-6112-4f99-941f-c16c4d8e70e5",
                            "665c2fe0-7ba5-4bf0-afa8-1b39a1c8eb0d",
                            "1aed10d7-f41c-46a4-a2c2-4010f193f712",
                            "b8555dd9-7f4d-4f9b-983c-55c3f227c513",
                            "d831a1fa-acbb-40c3-a71a-621a00f19a49",
                            "49b1106f-fd21-4add-8e79-d9277dde9d0f",
                            "560745f4-5d30-4f94-96e5-e43af3582bb3",
                            "b4c09514-f82a-4930-b299-178a77f8e153",
                            "d2527491-ea77-4ea4-acfd-d72491df166c",
                            "19c6faba-cdef-4f9b-acf5-b7cf807f0836",
                        ],
}

ST_TOKEN = "71dde339-abb6-4621-920e-85a5ebca0f2b"
ST_BASE  = "https://api.smartthings.com/v1"

# ── SmartThings API ───────────────────────────────────────────────────────────
def st_command(device_id: str, capability: str, command: str, args: list = []) -> bool:
    url     = f"{ST_BASE}/devices/{device_id}/commands"
    payload = json.dumps({"commands": [{"component": "main", "capability": capability,
                          "command": command, "arguments": args}]}).encode()
    req     = urllib.request.Request(url, data=payload, method="POST",
                headers={"Authorization": f"Bearer {ST_TOKEN}",
                         "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception as e:
        print(f"[SmartThings Error]: {e}")
        return False

def turn_on(device_id: str) -> bool:
    return st_command(device_id, "switch", "on")

def turn_off(device_id: str) -> bool:
    return st_command(device_id, "switch", "off")

def set_dim(device_id: str, level: int) -> bool:
    level = max(1, min(100, level))
    return st_command(device_id, "switchLevel", "setLevel", [level])

# ── Voice command parser ──────────────────────────────────────────────────────
SMART_KEYWORDS = [
    "turn on", "turn off", "switch on", "switch off",
    "dim", "brighten", "set", "lights on", "lights off",
    "lock", "unlock", "plug", "on air"
]

def is_smart_command(text: str) -> bool:
    return any(kw in text.lower() for kw in SMART_KEYWORDS)

def find_device(text: str):
    t = text.lower()
    for name in sorted(DEVICES.keys(), key=len, reverse=True):
        if name in t:
            return name, DEVICES[name]
    return None, None

def handle_smart_command(text: str) -> str:
    t = text.lower()
    device_name, device_id = find_device(t)

    if device_id is None:
        return "I couldn't find that device. Try saying the device name more clearly."

    ids = device_id if isinstance(device_id, list) else [device_id]

    # Determine action - check "off" phrases first to avoid "on" matching inside "off"
    if "turn off" in t or "switch off" in t or "lights off" in t or t.endswith(" off"):
        action = "off"
    elif "turn on" in t or "switch on" in t or "lights on" in t or t.endswith(" on"):
        action = "on"
    elif "dim" in t or "percent" in t or "%" in t:
        action = "dim"
    elif "brighten" in t or "full" in t or "max" in t:
        action = "bright"
    else:
        action = "on"

    # Extract dim level
    dim_level = 50
    match = re.search(r'(\d+)\s*(%|percent)', t)
    if match:
        dim_level = int(match.group(1))

    # Execute commands
    success = True
    for did in ids:
        if action == "on":
            ok = turn_on(did)
        elif action == "off":
            ok = turn_off(did)
        elif action == "dim":
            ok = set_dim(did, dim_level)
        elif action == "bright":
            ok = set_dim(did, 100)
        else:
            ok = turn_on(did)
        if not ok:
            success = False

    label = device_name.title()
    if action == "on":
        return f"Turning on the {label}." if success else f"I had trouble turning on the {label}."
    elif action == "off":
        return f"Turning off the {label}." if success else f"I had trouble turning off the {label}."
    elif action == "dim":
        return f"Dimming the {label} to {dim_level} percent." if success else f"I had trouble dimming the {label}."
    elif action == "bright":
        return f"Setting the {label} to full brightness." if success else f"I had trouble adjusting the {label}."
    return "Done."
