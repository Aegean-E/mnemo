"""Every user-facing failure carries a message, a reason and a repair (PRINCIPLE-011 R6)."""


class MnemoError(Exception):
    """A failure the CLI reports as `Error:` / `Why:` / `Fix:` without a traceback."""

    def __init__(self, message: str, why: str, fix: str):
        super().__init__(message)
        self.message = message
        self.why = why
        self.fix = fix

    def render(self) -> str:
        """The three-line report the CLI prints on stderr."""
        return f"Error: {self.message}\nWhy: {self.why}\nFix: {self.fix}"
