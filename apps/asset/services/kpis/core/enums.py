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


class KPIType(str, Enum):
    """Tipos de KPIs calculables"""
    NOI = 'noi'                          # Net Operating Income
    CAP_RATE = 'cap_rate'                # Capitalization Rate
    ROI = 'roi'                          # Return on Investment
    CASH_FLOW = 'cash_flow'              # Cash Flow Analysis
    OCCUPANCY = 'occupancy'              # Occupancy Rate
    DSCR = 'dscr'                        # Debt Service Coverage Ratio
    IRR = 'irr'                          # Internal Rate of Return
    CASH_ON_CASH = 'cash_on_cash'        # Cash on Cash Return
    GRM = 'grm'                          # Gross Rent Multiplier
    NOI_MARGIN = 'noi_margin'            # NOI Margin Percentage


class CalculationStatus(str, Enum):
    """Estados de cálculo"""
    PENDING = 'pending'
    SUCCESS = 'success'
    ERROR = 'error'
    INSUFFICIENT_DATA = 'insufficient_data'
    VALIDATION_FAILED = 'validation_failed'


class TrendDirection(str, Enum):
    """Dirección de tendencia"""
    UPWARD = 'upward'
    DOWNWARD = 'downward'
    STABLE = 'stable'
    VOLATILE = 'volatile'


class AlertLevel(str, Enum):
    """Niveles de alerta"""
    INFO = 'info'
    WARNING = 'warning'
    CRITICAL = 'critical'