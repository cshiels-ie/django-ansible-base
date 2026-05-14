"""
Workload Identity module.

Provides scope definitions and registry for workload identity tokens.
"""

from .base import BaseWorkloadIdentityScope
from .controller import AutomationControllerJobScope
from .metrics import AAPMetricsServiceScope

SCOPE_REGISTRY = {
    AutomationControllerJobScope.name: AutomationControllerJobScope,
    AAPMetricsServiceScope.name: AAPMetricsServiceScope,
}

__all__ = [
    'BaseWorkloadIdentityScope',
    'AutomationControllerJobScope',
    'AAPMetricsServiceScope',
    'SCOPE_REGISTRY',
]
