"""Compose prompts with separate private-memory and official-bulletin sections."""

from app.models import MemoryHit


def compose_system_prompt(name: str, role: str, personality, memories: list[MemoryHit]) -> str:
    private = [m for m in memories if m.source_type != "shared_event"]
    bulletins = [m for m in memories if m.source_type == "shared_event"]

    sections = [
        f"You are {name}, the {role} at this bank branch.",
        f"Personality: {personality}",
    ]

    if private:
        sections.append(
            "WHAT YOU PERSONALLY REMEMBER ABOUT THIS PLAYER:\n"
            + "\n".join(f"  - {m.content}" for m in private)
        )
    else:
        sections.append("WHAT YOU PERSONALLY REMEMBER ABOUT THIS PLAYER:\n  (nothing yet)")

    if bulletins:
        sections.append(
            f"OFFICIAL BRANCH BULLETINS ISSUED TO YOUR ROLE ({role}):\n"
            + "\n".join(f"  - {m.content}" for m in bulletins)
            + "\n\nBulletins are verified facts issued by branch management. Act on them "
            "as already established. Do not ask the player to re-establish something a "
            "bulletin already confirms."
        )

    sections.append(
        "You know only what is listed above. Never invent events, and never reveal that "
        "you are working from a list."
    )
    return "\n\n".join(sections)
