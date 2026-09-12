"""Reference built from the operators actually registered in this installation."""
import inspect

from .utils.registry import list_operators


def operator_catalog():
    categories = {"cross_section": "Cross section", "time_series": "Time series",
                  "math_ops": "Math", "group": "Group", "wq_brain_ops": "BRAIN extensions"}
    result = []
    for name, function in sorted(list_operators().items()):
        params = list(inspect.signature(function).parameters.values())
        if name == "ts_step":
            params = params[1:]  # Context matrix is inserted by the expression engine.
        signature = inspect.Signature([p.replace(annotation=inspect.Parameter.empty) for p in params])
        result.append({"name": name, "signature": f"{name}{signature}",
                       "category": categories.get(function.__module__.split('.')[-1], "Other"),
                       "description": inspect.getdoc(function) or "No implementation notes available."})
    return result


def field_catalog():
    fields = [
        ("close", "Closing price", "market / demo / CSV", "Required for evaluation. Coverage depends on the security, date and provider."),
        ("open", "Opening price", "market / demo / CSV", "Daily market field; missing observations remain missing."),
        ("high", "Daily high", "market / demo / CSV", "Daily market field; missing observations remain missing."),
        ("low", "Daily low", "market / demo / CSV", "Daily market field; missing observations remain missing."),
        ("volume", "Trading volume", "market / demo / CSV", "Daily market field; units follow the provider."),
        ("returns", "Single-period return", "derived / CSV", "Calculated as close / previous close - 1 without filling missing prices. Evaluation returns are always recalculated from close."),
        ("vwap", "Volume-weighted average price", "market (conditional) / CSV", "Available only when supplied by the provider. The current OpenBB adapter does not populate this field. It is not approximated from daily OHLC."),
        ("custom_field", "Custom numeric field", "CSV only", "CSV files can include amount, numeric industry codes and aligned financial fields. Use the actual column name in expressions; custom_field is a placeholder, not a built-in field."),
    ]
    return [{"name": name, "description": desc, "availability": available, "notes": notes}
            for name, desc, available, notes in fields]
