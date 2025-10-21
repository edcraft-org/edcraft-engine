from typing import Any

from src.core.query_engine.query_engine_exception import InvalidFieldError


def get_field_value(obj: Any, field_path: str) -> Any:
    """Extract field value from object."""
    from src.core.query_engine.pipeline_steps import JoinResult  # Avoid circular import

    fields = field_path.split(".")
    curr_obj = obj

    for field in fields:
        if isinstance(curr_obj, JoinResult):
            curr_obj = curr_obj.get(field)
            if curr_obj is None:
                # For outer joins, return None if alias doesn't exist or is None
                return None
        elif isinstance(curr_obj, object) and hasattr(curr_obj, field):
            curr_obj = getattr(curr_obj, field)
        elif isinstance(curr_obj, dict) and field in curr_obj:
            curr_obj = curr_obj[field]  # type: ignore
        else:
            raise InvalidFieldError(field)

    return curr_obj  # type: ignore
