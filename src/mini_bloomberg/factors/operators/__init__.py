"Factor research package exports. Importing the operators package registers its built-in functions."

# Import submodules to trigger operator registration
from . import cross_section
from . import time_series
from . import math_ops
from . import group
from . import wq_brain_ops  # WQ BRAIN operator extension package

from .base import Operator, validate_matrix

# Familiar BRAIN spellings for the recovered implementations.
from ..utils.registry import register_operator, get_operator
for alias, original in {"ts_delay": "delay", "ts_delta": "delta", "ts_std_dev": "ts_std", "ts_covariance": "ts_cov", "ts_decay_linear": "decay_linear", "inverse": "inv", "quantile": "quantile_cs"}.items():
    register_operator(alias)(get_operator(original))

for alias, original in {"max": "max_of", "min": "min_of", "ts_kurtosis": "ts_kurt", "ts_arg_max": "ts_argmax", "ts_arg_min": "ts_argmin", "group_neutralize": "group_demean"}.items():
    register_operator(alias)(get_operator(original))
