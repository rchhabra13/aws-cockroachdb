def to_vector_literal(values: list[float]) -> str:
    """asyncpg has no codec for CockroachDB's VECTOR type — pass it as this
    literal string and cast with ::VECTOR in the query instead."""
    return "[" + ",".join(repr(v) for v in values) + "]"
