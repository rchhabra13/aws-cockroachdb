"""Server-owned visibility rules for branch events."""

EVENT_VISIBILITY: dict[str, list[str]] = {
    "authorization": ["guard", "manager"],
    "vault_approach": ["guard", "manager"],
    "suspicion": ["guard", "manager", "teller", "loan_officer", "compliance"],
    # Excluding tellers prevents the alert from reaching the windows involved.
    "structuring": ["compliance", "manager", "guard"],
}


def roles_for(event_type: str) -> list[str]:
    if event_type not in EVENT_VISIBILITY:
        raise ValueError(f"unknown event type: {event_type}")
    return EVENT_VISIBILITY[event_type]
