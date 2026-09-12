"Factor research package exports. Importing the operators package registers its built-in functions."

# Import operators first to register all built-ins
from . import operators

from .core import Context, ExpressionEngine
from .data import DataLoader
from .backtest import FactorEvaluator
from .utils import list_operators
