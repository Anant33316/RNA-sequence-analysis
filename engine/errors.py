"""Domain errors raised by the engine. The API maps them to HTTP 400/422."""


class EngineError(ValueError):
    """A user-facing validation or semantic error.

    `field` points at the offending part of the request (e.g.
    "automaton.transitions[3].to") so the UI can show it next to the input.
    """

    def __init__(self, message: str, field: str | None = None, code: str = "invalid_input"):
        super().__init__(message)
        self.message = message
        self.field = field
        self.code = code

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "field": self.field}
