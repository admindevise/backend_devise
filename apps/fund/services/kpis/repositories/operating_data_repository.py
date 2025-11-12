"""
Repository para acceso a datos operativos (ingresos y gastos)
"""

from typing import Optional
from decimal import Decimal
from django.db.models import Sum, Q, QuerySet

from apps.fund.models.core import Fund
from apps.fund.models.operating import FundOperatingExpense, FundOperatingIncome


class OperatingDataRepository:
    """
    Repository que centraliza el acceso a datos de ingresos y gastos operativos.
    
    Ventajas:
    - Separa lógica de acceso a datos de lógica de negocio
    - Facilita testing (se puede mockear)
    - Centraliza queries complejos
    
    Example:
        >>> repo = OperatingDataRepository()
        >>> income = repo.get_income_by_period(
        ...     fund=fund,
        ...     period_type='monthly',
        ...     period_year=2024,
        ...     period_month=6
        ... )
    """
    
    # ========================================
    # CONSULTAS DE PERÍODO ESPECÍFICO
    # ========================================
    
    @staticmethod
    def get_income_by_period(
        fund: Fund,
        period_type: str,
        period_year: int,
        period_month: Optional[int] = None,
        period_quarter: Optional[int] = None
    ) -> Optional[FundOperatingIncome]:
        """
        Obtiene el registro de ingresos para un período específico.
        
        Args:
            fund: Activo
            period_type: Tipo de período
            period_year: Año
            period_month: Mes (opcional)
            period_quarter: Trimestre (opcional)
            
        Returns:
            FundOperatingIncome o None
        """
        filters = Q(
            fund=fund,
            period_type=period_type,
            period_year=period_year
        )
        
        if period_month is not None:
            filters &= Q(period_month=period_month)
        
        if period_quarter is not None:
            filters &= Q(period_quarter=period_quarter)
        
        return FundOperatingIncome.objects.filter(filters).first()
    
    @staticmethod
    def get_expense_by_period(
        fund: Fund,
        period_type: str,
        period_year: int,
        period_month: Optional[int] = None,
        period_quarter: Optional[int] = None
    ) -> Optional[FundOperatingExpense]:
        """
        Obtiene el registro de gastos para un período específico.
        
        Args:
            Fund: Activo
            period_type: Tipo de período
            period_year: Año
            period_month: Mes (opcional)
            period_quarter: Trimestre (opcional)
            
        Returns:
            FundOperatingExpense o None
        """
        filters = Q(
            fund=fund,
            period_type=period_type,
            period_year=period_year
        )
        
        if period_month is not None:
            filters &= Q(period_month=period_month)
        
        if period_quarter is not None:
            filters &= Q(period_quarter=period_quarter)
        
        return FundOperatingExpense.objects.filter(filters).first()
    
    # ========================================
    # CONSULTAS DE RANGO
    # ========================================
    
    @staticmethod
    def get_income_range(
        fund: Fund,
        period_type: str,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int
    ) -> QuerySet[FundOperatingIncome]:
        """
        Obtiene ingresos en un rango de fechas.
        
        Args:
            fund: Activo
            period_type: Tipo de período
            start_year: Año de inicio
            start_month: Mes de inicio
            end_year: Año de fin
            end_month: Mes de fin
            
        Returns:
            QuerySet de FundOperatingIncome
        """
        return FundOperatingIncome.objects.filter(
            fund=fund,
            period_type=period_type
        ).filter(
            Q(
                Q(period_year=start_year, period_month__gte=start_month) |
                Q(period_year__gt=start_year)
            ) &
            Q(
                Q(period_year=end_year, period_month__lte=end_month) |
                Q(period_year__lt=end_year)
            )
        ).order_by('period_year', 'period_month')
    
    @staticmethod
    def get_expense_range(
        fund: Fund,
        period_type: str,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int
    ) -> QuerySet[FundOperatingExpense]:
        """
        Obtiene gastos en un rango de fechas.
        
        Args:
            fund: Activo
            period_type: Tipo de período
            start_year: Año de inicio
            start_month: Mes de inicio
            end_year: Año de fin
            end_month: Mes de fin
            
        Returns:
            QuerySet de FundOperatingExpense
        """
        return FundOperatingExpense.objects.filter(
            fund=fund,
            period_type=period_type
        ).filter(
            Q(
                Q(period_year=start_year, period_month__gte=start_month) |
                Q(period_year__gt=start_year)
            ) &
            Q(
                Q(period_year=end_year, period_month__lte=end_month) |
                Q(period_year__lt=end_year)
            )
        ).order_by('period_year', 'period_month')
    
    # ========================================
    # AGREGACIONES
    # ========================================
    
    @staticmethod
    def get_total_income(incomes: QuerySet[FundOperatingIncome]) -> Decimal:
        """
        Calcula el total de ingresos de un QuerySet.
        
        Args:
            incomes: QuerySet de ingresos
            
        Returns:
            Total de ingresos
        """
        result = incomes.aggregate(total=Sum('total_operating_income'))
        return result['total'] or Decimal('0.00')
    
    @staticmethod
    def get_total_expenses(expenses: QuerySet[FundOperatingExpense]) -> Decimal:
        """
        Calcula el total de gastos de un QuerySet.
        
        Args:
            expenses: QuerySet de gastos
            
        Returns:
            Total de gastos
        """
        result = expenses.aggregate(total=Sum('total_operating_expense'))
        return result['total'] or Decimal('0.00')
    
    # ========================================
    # VERIFICACIÓN DE EXISTENCIA
    # ========================================
    
    @staticmethod
    def has_data_for_period(
        fund: Fund,
        period_type: str,
        period_year: int,
        period_month: Optional[int] = None,
        period_quarter: Optional[int] = None
    ) -> bool:
        """
        Verifica si existen datos (ingresos o gastos) para un período.
        
        Returns:
            True si hay al menos un registro
        """
        income = OperatingDataRepository.get_income_by_period(
            fund, period_type, period_year, period_month, period_quarter
        )
        
        expense = OperatingDataRepository.get_expense_by_period(
            fund, period_type, period_year, period_month, period_quarter
        )
        
        return income is not None or expense is not None