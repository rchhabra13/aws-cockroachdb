def to_vector_literal(values: list[float]) -> str:
    """Format a VECTOR literal because asyncpg has no CockroachDB VECTOR codec."""
    return "[" + ",".join(repr(v) for v in values) + "]"
