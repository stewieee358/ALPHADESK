"Global operator registry. Use @register_operator(\"name\") to expose a function to the expression engine."

from typing import Callable, Dict, Any

# Global operator registry
_OPERATOR_REGISTRY: Dict[str, Callable] = {}


def register_operator(name: str):
    "Decorator registering a function under a name accessible to factor expressions."
    def decorator(func: Callable) -> Callable:
        if name in _OPERATOR_REGISTRY:
            import warnings
            warnings.warn(f"Operator '{name}' is being overridden.")
        _OPERATOR_REGISTRY[name] = func
        func._op_name = name
        return func
    return decorator


def get_operator(name: str) -> Callable:
    "Look up a registered operator by name; raise KeyError for an unknown name."
    if name not in _OPERATOR_REGISTRY:
        raise KeyError(f"Unknown operator: '{name}'. Available: {list(_OPERATOR_REGISTRY.keys())}")
    return _OPERATOR_REGISTRY[name]


def list_operators() -> Dict[str, Callable]:
    "Return a copy of the registered operator mapping."
    return dict(_OPERATOR_REGISTRY)
