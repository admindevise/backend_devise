"""
Sistema de Cálculo de KPIs para Assets Inmobiliarios

Este módulo proporciona un conjunto completo de herramientas para calcular,
validar y reportar KPIs (Key Performance Indicators) de activos inmobiliarios.

Uso básico:
    >>> from apps.asset.services.kpis import AssetKPIFacade
    >>> from apps.asset.models.core import Asset
    >>> 
    >>> asset = Asset.objects.get(id=1)
    >>> facade = AssetKPIFacade(asset)
    >>> 
    >>> # Calcular NOI
    >>> noi = facade.calculate_noi(months_back=12)
    >>> print(f"NOI: ${noi['net_operating_income']:,.2f}")

Arquitectura:
    - Strategy Pattern: Para diferentes tipos de KPIs
    - Repository Pattern: Para acceso a datos
    - Builder Pattern: Para construcción de reportes
    - Facade Pattern: Para simplificar la API pública
"""

# Exportar componentes principales
from .core.exceptions import (
    AssetKPIError,
    DataValidationError,
    PeriodValidationError,
    InsufficientDataError,
    CalculationError
)

from .facade import AssetKPIFacade
from .calculator import AssetKPICalculator

__version__ = '1.0.0'

__all__ = [
    # Main interfaces
    'AssetKPIFacade',
    'AssetKPICalculator',
    
    # Exceptions
    'AssetKPIError',
    'DataValidationError',
    'PeriodValidationError',
    'InsufficientDataError',
    'CalculationError',
]