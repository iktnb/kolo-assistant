class InputError(Exception):
    """An expected user error; no traceback should reach the terminal."""


class FieldError(InputError):
    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(f"{field}: {message}")


class StorageError(Exception):
    """The store could not safely complete an operation."""


class DuplicateId(Exception):
    """Internal signal for a retryable generated-ID collision."""
