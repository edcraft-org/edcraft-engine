class QueryEngineError(Exception):
    """Base exception for all query engine errors."""
    def __init__(self, message: str):
        super().__init__(message)


class InvalidOperatorError(QueryEngineError):
    """Raised when an unsupported operator is used."""
    def __init__(self, operator: str):
        super().__init__(f"Unsupported operator: {operator}")


class InvalidFieldError(QueryEngineError):
    """Raised when a requested field does not exist in the object."""
    def __init__(self, field: str):
        super().__init__(f"Invalid field: {field}")
