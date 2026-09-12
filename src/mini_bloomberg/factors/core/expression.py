"""Restricted factor expression interpreter; never executes Python code."""
import ast
import operator
import re
import numpy as np
import pandas as pd
from ..utils.registry import get_operator

_BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
           ast.Div: operator.truediv, ast.Pow: operator.pow, ast.BitAnd: operator.and_,
           ast.BitOr: operator.or_}
_COMPARE = {ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt,
            ast.GtE: operator.ge, ast.Eq: operator.eq, ast.NotEq: operator.ne}

class ExpressionEngine:
    def __init__(self, context):
        self.context = context

    def evaluate(self, expr):
        if not isinstance(expr, str) or not expr.strip() or len(expr) > 4000:
            raise ValueError("Expression must contain 1?4000 characters")
        # Python keywords are legal BRAIN operator names.
        expr = re.sub(r"\b(and|or|not)\s*(?=\()", r"wq_\1", expr)
        tree = ast.parse(expr, mode="exec")
        if sum(1 for _ in ast.walk(tree)) > 500:
            raise ValueError("Expression is too complex")
        local = {}
        result = None
        for stmt in tree.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                result = self._eval(stmt.value, local)
                local[stmt.targets[0].id] = result
            elif isinstance(stmt, ast.Expr):
                result = self._eval(stmt.value, local)
            else:
                raise ValueError("Only expressions and named factor assignments are supported")
        return result

    def _eval(self, node, local):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str, bool)):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in {"true", "false"}: return node.id == "true"
            return local[node.id] if node.id in local else self.context[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
            a, b = self._eval(node.left, local), self._eval(node.right, local)
            if isinstance(node.op, ast.Pow) and (not np.isscalar(b) or abs(b) > 100):
                raise ValueError("Power exponent must be a scalar between -100 and 100")
            if isinstance(node.op, ast.Div):
                b = b.replace(0, np.nan) if isinstance(b, pd.DataFrame) else (np.nan if b == 0 else b)
            return _BINARY[type(node.op)](a, b)
        if isinstance(node, ast.UnaryOp):
            val = self._eval(node.operand, local)
            if isinstance(node.op, ast.USub): return -val
            if isinstance(node.op, ast.UAdd): return val
            if isinstance(node.op, (ast.Not, ast.Invert)): return np.logical_not(val)
        if isinstance(node, ast.Compare):
            a = self._eval(node.left, local)
            result = True
            for op, rhs in zip(node.ops, node.comparators):
                if type(op) not in _COMPARE: raise ValueError("Unsupported comparison")
                b = self._eval(rhs, local)
                result = result & _COMPARE[type(op)](a, b)
                a = b
            return result
        if isinstance(node, ast.BoolOp):
            vals = [self._eval(v, local) for v in node.values]
            result = vals[0]
            for val in vals[1:]:
                result = np.logical_and(result, val) if isinstance(node.op, ast.And) else np.logical_or(result, val)
            return result
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = node.func.id
            if name in {"wq_and", "wq_or", "wq_not"}: name = name[3:]
            args = [self._eval(a, local) for a in node.args]
            if any(k.arg is None for k in node.keywords): raise ValueError("Keyword unpacking is not supported")
            kwargs = {k.arg: self._eval(k.value, local) for k in node.keywords}
            for key in ("d", "lookback", "lag"):
                if key in kwargs and (not isinstance(kwargs[key], int) or kwargs[key] < 0):
                    raise ValueError("Lookback and lag must be nonnegative integers")
            if name in {"delay", "delta", "ts_delay", "ts_delta", "ts_returns"} and len(args) > 1 and args[1] < 0:
                raise ValueError("Negative lag would read future data")
            if name == "ts_regression" and len(args) > 3 and args[3] < 0:
                raise ValueError("Negative lag would read future data")
            if name == "ts_step": args.insert(0, self.context[self.context.fields[0]])
            aliases = {"filter": "filter_nan", "range": "range_str", "buckets": "buckets_str", "hump": "hump_val"}
            kwargs = {aliases.get(k, k): v for k, v in kwargs.items()}
            return get_operator(name)(*args, **kwargs)
        raise ValueError(f"Unsupported expression syntax: {type(node).__name__}")

    def batch_evaluate(self, exprs):
        return {name: self.evaluate(expr) for name, expr in exprs.items()}
