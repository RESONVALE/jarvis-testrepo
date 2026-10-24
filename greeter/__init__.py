"""A tiny package that greets people by name."""

MAX_NAME_LENGTH = 100


def greet(name: str) -> str:
    """Return a greeting for ``name``.

    Leading and trailing whitespace is removed. Raises ``TypeError`` if
    ``name`` is not a string, and ``ValueError`` if it is empty or longer
    than ``MAX_NAME_LENGTH`` characters.
    """
    if not isinstance(name, str):
        raise TypeError(f"name must be a str, not {type(name).__name__}")
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("name must not be empty")
    if len(cleaned) > MAX_NAME_LENGTH:
        raise ValueError(f"name must be at most {MAX_NAME_LENGTH} characters")
    return f"Hello, {cleaned}!"
