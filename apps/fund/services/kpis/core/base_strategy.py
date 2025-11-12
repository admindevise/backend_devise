"""
Clase base abstracta para todas las Strategies de KPIs
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Any, Optional
from apps.fund.models.core import Fund


class BaseKPIStrategy(ABC):
    """
    Strategy base para cálculos de KPIs.
    
    Todas las strategies concretas (NOI, Cap Rate, ROI, etc.)
    deben heredar de esta clase e implementar los métodos abstractos.
    """
    
    def __init__(self, fund: Fund):
        """
        Args:
            fund: Instancia del fund
        """
        if not fund:
            raise ValueError("fund is required")
        
        if not fund.pk:
            raise ValueError("fund must be saved to database")
        
        self.fund = fund
    
    @abstractmethod
    def calculate(self, **kwargs) -> Dict[str, Any]:
        """
        Método principal de cálculo.
        
        Returns:
            dict: Resultado del cálculo del KPI
        """
        pass
    
    @abstractmethod
    def validate_prerequisites(self) -> Dict[str, Any]:
        """
        Valida que existan los datos mínimos necesarios.
        
        Returns:
            dict: Estado de validación
        """
        pass
    
    def get_strategy_name(self) -> str:
        """Retorna el nombre de la strategy"""
        return self.__class__.__name__


    # ========================================
    # MÉTODOS HELPER
    # ========================================
    
    def _get_fund_info(self) -> Dict[str, Any]:
        """
        Retorna información básica del fund para incluir en respuestas.
        
        Returns:
            dict: Información del fund
        """
        if not self.fund:
            return {
                'fund_id': None,
                'fund_name': None,
                'fund_code': None,
                'status': None
            }
        
        return {
            'fund_id': self.fund.id,
            'fund_name': self.fund.name if hasattr(self.fund, 'name') else None,
            'fund_code': self.fund.code if hasattr(self.fund, 'code') else None,
            'status': self.fund.status if hasattr(self.fund, 'status') else None
        }
    
    def _safe_divide(self, numerator: Decimal, denominator: Decimal) -> Decimal:
        """
        División segura que retorna 0 si el denominador es 0.
        
        Args:
            numerator: Numerador
            denominator: Denominador
            
        Returns:
            Decimal: Resultado de la división o 0
        """
        if not denominator or denominator == 0:
            return Decimal('0.00')
        return numerator / denominator
    
    def _calculate_percentage(self, part: Decimal, total: Decimal) -> Decimal:
        """
        Calcula porcentaje de forma segura.
        
        Args:
            part: Parte
            total: Total
            
        Returns:
            Decimal: Porcentaje (0-100)
        """
        if not total or total == 0:
            return Decimal('0.00')
        return (part / total) * 100
    
    def _aggregate_operating_incomes(
        self,
        period_type: str = 'monthly',
        months_back: int = 12,
        period_year: Optional[int] = None,
        period_month: Optional[int] = None,
        period_quarter: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Agrega ingresos operativos del fondo.
        
        Las subclases pueden sobrescribir este método si necesitan
        lógica de agregación específica.
        """
        # Implementación base - puede ser sobrescrita
        return {
            'total_operating_income': Decimal('0.00'),
            'periods_count': 0
        }
    
    def _aggregate_operating_expenses(
        self,
        period_type: str = 'monthly',
        months_back: int = 12,
        period_year: Optional[int] = None,
        period_month: Optional[int] = None,
        period_quarter: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Agrega gastos operativos del fondo.
        
        Las subclases pueden sobrescribir este método si necesitan
        lógica de agregación específica.
        """
        # Implementación base - puede ser sobrescrita
        return {
            'total_operating_expense': Decimal('0.00'),
            'total_non_operating_expenses': Decimal('0.00'),
            'total_capex': Decimal('0.00'),
            'total_debt_service': Decimal('0.00'),
            'periods_count': 0
        }