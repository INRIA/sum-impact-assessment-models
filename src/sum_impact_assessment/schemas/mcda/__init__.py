"""
MCDA Schemas

Pydantic models for Multi-Criteria Decision Analysis inputs and outputs.
"""
from .goal import Goal
from .alternative import Alternative

__all__ = [
    'Goal',
    'Alternative',
]
