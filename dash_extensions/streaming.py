from typing import Union

from pydantic import BaseModel


def sse_message(data: str = "[DONE]") -> str:
    """
    Given a string, formats it as an SSE event.
    """
    return f"data: {data}\n\n"


def sse_options(payload: Union[str, BaseModel], **kwargs):
    """
    Given a string or Pydantic base model, returns a dictionary that can be used as options for StreamingBuffer.
    """
    options = {"payload": payload}
    # For Pydantic models, convert to JSON and set the content type.
    if isinstance(payload, BaseModel):
        options = {
            "payload": payload.model_dump_json(),
            "headers": {"Content-Type": "application/json"},
        }
    # Merge with additional options.
    return {**options, **kwargs}
