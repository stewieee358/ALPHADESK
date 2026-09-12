"""
Auto-generate Anthropic tool specs from all BloombergFunction subclasses.
Import ALL_TOOLS and FUNCTIONS_BY_NAME into the orchestrator.
"""

from mini_bloomberg.functions.alpha import ALPHA
from mini_bloomberg.functions.anr  import ANR
from mini_bloomberg.functions.comp import COMP
from mini_bloomberg.functions.dcf  import DCF
from mini_bloomberg.functions.des  import DES
from mini_bloomberg.functions.fa   import FA
from mini_bloomberg.functions.gp   import GP
from mini_bloomberg.functions.news import NEWS
from mini_bloomberg.functions.qtr  import QTR
from mini_bloomberg.functions.rpt  import RPT
from mini_bloomberg.functions.rv   import RV

_INSTANCES = [ALPHA(), DES(), FA(), GP(), ANR(), COMP(), RPT(), RV(), NEWS(), DCF(), QTR()]

# List of tool spec dicts ready to pass to client.messages.create(tools=...)
ALL_TOOLS: list[dict] = [fn.tool_schema() for fn in _INSTANCES]

# Keyed by tool name (lowercase, matching tool_schema "name" field)
FUNCTIONS_BY_NAME: dict[str, object] = {fn.name.lower(): fn for fn in _INSTANCES}
