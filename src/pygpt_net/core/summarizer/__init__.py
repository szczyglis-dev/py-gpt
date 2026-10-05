from .summarizer import Summarizer, ContextBudget

__all__ = ["Summarizer", "ContextBudget"]


def model_payload(value):
    """Select model summaries while preserving raw tool response transport data."""
    if isinstance(value, dict):
        result = {key: model_payload(child) for key, child in value.items() if key != "model_result"}
        if "model_result" in value:
            result["result"] = value["model_result"]
        return result
    if isinstance(value, list):
        return [model_payload(child) for child in value]
    if isinstance(value, tuple):
        return tuple(model_payload(child) for child in value)
    return value
