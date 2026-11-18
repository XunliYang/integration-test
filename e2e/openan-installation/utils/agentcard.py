from __future__ import annotations

import hashlib
import time


def make_sample_agent_card(name: str | None = None) -> dict:
    if name is None:
        name = f"e2e-installation-{hashlib.sha256(str(time.time_ns()).encode()).hexdigest()[:8]}"
    return {
        "org": "e2e-openan-installation",
        "name": name,
        "description": "Minimal sample AgentCard used by openan-installation FIT verification",
        "version": "1.0.0",
        "capabilities": [
            {"name": "e2e-verify", "description": "Registry data persistence verification"}
        ],
    }


def agent_path(card: dict) -> str:
    return f"agent-cards/{card['org']}/{card['name']}"
