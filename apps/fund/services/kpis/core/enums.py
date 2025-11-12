"""
Enumeraciones para KPIs
"""

from enum import Enum


class PeriodType(str, Enum):
    """Tipos de períodos"""
    MONTHLY = 'monthly'
    QUARTERLY = 'quarterly'
    SEMI_ANNUAL = 'semi_annual'
    ANNUAL = 'annual'
    
    @classmethod
    def choices(cls):
        return [(item.value, item.name) for item in cls]
    
    @classmethod
    def values(cls):
        return [item.value for item in cls]