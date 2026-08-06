"""Which roles may see which kind of branch event.

Server owned on purpose. Callers name an event type; they never choose the audience,
so a compromised or hallucinating caller cannot widen visibility.
"""

EVENT_VISIBILITY: dict[str, list[str]] = {
    "authorization": ["guard", "manager"],
    "vault_approach": ["guard", "manager"],
    "suspicion": ["guard", "manager", "teller"],
}


def roles_for(event_type: str) -> list[str]:
    if event_type not in EVENT_VISIBILITY:
        raise ValueError(f"unknown event type: {event_type}")
    return EVENT_VISIBILITY[event_type]
