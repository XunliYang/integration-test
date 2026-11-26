from __future__ import annotations

import hashlib
import json
import time

from utils.shell import curl_request

JSON_HEADERS = ["Content-Type: application/json"]


def make_sample_agent_card(name: str | None = None) -> dict:
    if name is None:
        name = f"e2e-installation-{hashlib.sha256(str(time.time_ns()).encode()).hexdigest()[:8]}"
    # a2a.types.AgentCard (lf.a2a.v1): organization lives under provider;
    # capabilities is a message, skills carry the capability list.
    return {
        "name": name,
        "description": "Minimal sample AgentCard used by openan-installation FIT verification",
        "version": "1.0.0",
        "provider": {"organization": "e2e-openan-installation"},
        "capabilities": {},
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
        "skills": [
            {"id": "e2e-verify", "name": "e2e-verify",
             "description": "Registry data persistence verification", "tags": ["e2e"]}
        ],
    }


def agent_path(card: dict) -> str:
    org = card.get("org") or card["provider"]["organization"]
    return f"agent-cards/{org}/{card['name']}"


def card_url(base: str, card: dict) -> str:
    return f"{base.rstrip('/')}/rest/v1/registry-center/{agent_path(card)}"


def register_card(base: str, card: dict, headers: list | None = None) -> tuple[str, str]:
    return curl_request(
        "POST",
        f"{base.rstrip('/')}/rest/v1/registry-center/agent-cards",
        data=json.dumps({"agentCards": [card]}),
        headers=JSON_HEADERS + list(headers or []),
    )


def fetch_card(base: str, card: dict, headers: list | None = None) -> tuple[str, str]:
    return curl_request("GET", card_url(base, card), headers=headers)


def delete_card(base: str, card: dict, headers: list | None = None) -> tuple[str, str]:
    return curl_request("DELETE", card_url(base, card), headers=headers)
