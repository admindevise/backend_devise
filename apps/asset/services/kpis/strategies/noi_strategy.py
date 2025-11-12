"""
NOI Calculation Strategy - SIMPLIFICADO
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Q

from ..core.base_strategy import BaseKPIStrategy
from apps.asset.models.core import Asset
from apps.asset.models.operating import AssetOperatingIncome, AssetOperatingExpense
from ..repositories.operating_data_repository import OperatingDataRepository


class NOICalculationStrategy(BaseKPIStrategy):
    """
    Strategy para calcular NOI (Net Operating Income).
    
    NOI = Ingresos Operativos - Gastos Operativos
    """
    
    def __init__(self, asset: Asset):
        super().__init__(asset)
        self.repository = OperatingDataRepository()
    
    def validate_prerequisites(self) -> Dict[str, bool]:
        """Valida que el asset sea válido"""
        validations = {
            'asset_exists': self.asset is not None,
            'asset_has_id': bool(self.asset.pk if self.asset else False),
            'asset_is_active': self.asset.status == 'active' if self.asset else False
        }
        
        return {
            'is_valid': all(validations.values()),
            'validations': validations
        }
    
    def calculate(
        self,
        period_type: str = 'monthly',
        period_year: Optional[int] = None,
        period_month: Optional[int] = None,
        period_quarter: Optional[int] = None,
        months_back: int = 12,
        include_breakdown: bool = True
    ) -> Dict[str, Any]:
        """Calcula NOI"""
        
        # 1. Validar asset
        prereq = self.validate_prerequisites()
        if not prereq['is_valid']:
            return {
                'error': 'Asset prerequisites not met',
                'asset_id': self.asset.id if self.asset else None,
                'asset_code': self.asset.asset_code if self.asset else None
            }
        
        # 2. Si tiene año + mes/trimestre = período específico
        if period_year and (period_month or period_quarter):
            return self._calculate_single_period(
                period_type, period_year, period_month, period_quarter
            )
        
        # 3. Si no = últimos 12 meses
        return self._calculate_last_12_months(include_breakdown)
    
    def _calculate_single_period(
        self,
        period_type: str,
        period_year: int,
        period_month: Optional[int],
        period_quarter: Optional[int]
    ) -> Dict[str, Any]:
        """Calcula NOI para UN período específico"""
        
        try:
            # Obtener datos
            income_record = self.repository.get_income_by_period(
                asset=self.asset,
                period_type=period_type,
                period_year=period_year,
                period_month=period_month,
                period_quarter=period_quarter
            )
            
            expense_record = self.repository.get_expense_by_period(
                asset=self.asset,
                period_type=period_type,
                period_year=period_year,
                period_month=period_month,
                period_quarter=period_quarter
            )
            
            # Validar que haya datos
            if not income_record and not expense_record:
                return {
                    'error': 'No hay datos para el período especificado',
                    'asset_id': self.asset.id,
                    'asset_code': self.asset.asset_code,
                    'period_year': period_year,
                    'period_month': period_month,
                    'net_operating_income': 0
                }
            
            # Calcular NOI
            total_income = income_record.total_operating_income if income_record else Decimal('0.00')
            total_expenses = expense_record.total_operating_expense if expense_record else Decimal('0.00')
            noi = total_income - total_expenses
            noi_margin = (noi / total_income * 100) if total_income > 0 else Decimal('0.00')
            
            # Formatear resultado
            return {
                'asset_id': self.asset.id,
                'asset_code': self.asset.asset_code,
                'asset_name': self.asset.name,
                'fund_id': self.asset.fund.id,
                'fund_name': self.asset.fund.name,
                'period_type': period_type,
                'period_year': period_year,
                'period_month': period_month,
                'period_quarter': period_quarter,
                'period_display': self._format_period_display(period_type, period_year, period_month, period_quarter),
                'total_operating_income': float(total_income),
                'total_operating_expenses': float(total_expenses),
                'net_operating_income': float(noi),
                'noi_margin_percentage': float(noi_margin),
                'calculation_date': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': f'Error: {str(e)}',
                'asset_id': self.asset.id,
                'asset_code': self.asset.asset_code
            }
    
    def _calculate_last_12_months(self, include_breakdown: bool) -> Dict[str, Any]:
        """Calcula NOI de los ÚLTIMOS 12 MESES"""
        
        try:
            current_date = timezone.now()
            
            # Lógica día 30
            if current_date.day < 30:
                if current_date.month == 1:
                    last_completed_year = current_date.year - 1
                    last_completed_month = 12
                else:
                    last_completed_year = current_date.year
                    last_completed_month = current_date.month - 1
            else:
                last_completed_year = current_date.year
                last_completed_month = current_date.month
            
            start_month = last_completed_month
            start_year = last_completed_year - 1
            
            # Obtener datos
            incomes = self.repository.get_income_range(
                asset=self.asset,
                period_type='monthly',
                start_year=start_year,
                start_month=start_month,
                end_year=last_completed_year,
                end_month=last_completed_month
            )
            
            expenses = self.repository.get_expense_range(
                asset=self.asset,
                period_type='monthly',
                start_year=start_year,
                start_month=start_month,
                end_year=last_completed_year,
                end_month=last_completed_month
            )
            
            # Validar datos
            if not incomes.exists() and not expenses.exists():
                return {
                    'error': 'No hay datos en los últimos 12 meses',
                    'asset_id': self.asset.id,
                    'asset_code': self.asset.asset_code,
                    'total_noi_12m': 0
                }
            
            # Calcular totales
            total_income = incomes.aggregate(total=Sum('total_operating_income'))['total'] or Decimal('0.00')
            total_expenses = expenses.aggregate(total=Sum('total_operating_expense'))['total'] or Decimal('0.00')
            total_noi = total_income - total_expenses
            
            noi_margin = (total_noi / total_income * 100) if total_income > 0 else Decimal('0.00')
            average_monthly = total_noi / 12
            
            result = {
                'asset_id': self.asset.id,
                'asset_code': self.asset.asset_code,
                'asset_name': self.asset.name,
                'fund_id': self.asset.fund.id,
                'fund_name': self.asset.fund.name,
                'period_analyzed': f'12 meses ({start_year}-{start_month:02d} a {last_completed_year}-{last_completed_month:02d})',
                'start_period': f'{start_year}-{start_month:02d}',
                'end_period': f'{last_completed_year}-{last_completed_month:02d}',
                'total_operating_income_12m': float(total_income),
                'total_operating_expenses_12m': float(total_expenses),
                'total_noi_12m': float(total_noi),
                'noi_margin_percentage': float(noi_margin),
                'average_monthly_noi': float(average_monthly),
                'months_with_data': incomes.count(),
                'calculation_date': timezone.now().isoformat()
            }
            
            if include_breakdown:
                monthly_breakdown = []
                expenses_dict = {(e.period_year, e.period_month): e for e in expenses}
                
                for income in incomes:
                    expense = expenses_dict.get((income.period_year, income.period_month))
                    month_income = income.total_operating_income
                    month_expense = expense.total_operating_expense if expense else Decimal('0.00')
                    month_noi = month_income - month_expense
                    
                    monthly_breakdown.append({
                        'period_display': income.period_display,
                        'period_year': income.period_year,
                        'period_month': income.period_month,
                        'income': float(month_income),
                        'expenses': float(month_expense),
                        'noi': float(month_noi),
                        'noi_margin': float((month_noi / month_income * 100)) if month_income > 0 else 0
                    })
                
                result['monthly_breakdown'] = monthly_breakdown
            
            return result
            
        except Exception as e:
            return {
                'error': f'Error: {str(e)}',
                'asset_id': self.asset.id,
                'asset_code': self.asset.asset_code,
                'total_noi_12m': 0
            }
    
    def _format_period_display(
        self, period_type: str, period_year: int, 
        period_month: Optional[int], period_quarter: Optional[int]
    ) -> str:
        """Formatea período"""
        if period_type == 'monthly' and period_month:
            months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
            return f"{months[period_month - 1]} {period_year}"
        elif period_type == 'quarterly' and period_quarter:
            return f"Q{period_quarter} {period_year}"
        return str(period_year)