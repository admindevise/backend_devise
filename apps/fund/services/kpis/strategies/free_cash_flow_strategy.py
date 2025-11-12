"""
Free Cash Flow Calculation Strategy para Fund
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum

from ..core.base_strategy import BaseKPIStrategy
from apps.fund.models.core import Fund
from apps.fund.models.operating import FundOperatingIncome, FundOperatingExpense
from .noi_strategy import NOICalculationStrategy
from ..repositories.operating_data_repository import OperatingDataRepository


class FreeCashFlowCalculationStrategy(BaseKPIStrategy):
    """
    Strategy para calcular Free Cash Flow (FCF) del fondo.
    
    FCF = NOI - CAPEX - Servicio de Deuda + Otros Ingresos No Operativos
    """
    
    def __init__(self, fund: Fund):
        super().__init__(fund)
        self.noi_strategy = NOICalculationStrategy(fund)
        self.repository = OperatingDataRepository()
    
    def validate_prerequisites(self) -> Dict[str, bool]:
        """Valida que el fund sea válido"""
        validations = {
            'fund_exists': self.fund is not None,
            'fund_has_id': bool(self.fund.pk if self.fund else False),
            'fund_is_active': self.fund.status == 'active' if self.fund else False
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
        """Calcula Free Cash Flow"""
        
        # 1. Validar fund
        prereq = self.validate_prerequisites()
        if not prereq['is_valid']:
            return {
                'error': 'Fund prerequisites not met',
                **self._get_fund_info()
            }
        
        # 2. Si tiene año + mes/trimestre = período específico
        if period_year and (period_month or period_quarter):
            return self._calculate_single_period(
                period_type, period_year, period_month, period_quarter
            )
        
        # 3. Si no = últimos 12 meses
        return self._calculate_last_12_months(months_back, include_breakdown)
    
    def _calculate_single_period(
        self,
        period_type: str,
        period_year: int,
        period_month: Optional[int],
        period_quarter: Optional[int]
    ) -> Dict[str, Any]:
        """Calcula FCF para UN período específico"""
        
        try:
            # 1. Obtener NOI del período
            noi_result = self.noi_strategy.calculate(
                period_type=period_type,
                period_year=period_year,
                period_month=period_month,
                period_quarter=period_quarter,
                include_breakdown=False
            )
            
            if 'error' in noi_result:
                return {
                    'error': f'Error obteniendo NOI: {noi_result["error"]}',
                    **self._get_fund_info()
                }
            
            noi = Decimal(str(noi_result.get('net_operating_income', 0)))
            
            # 2. Obtener registros de gastos del período
            expense_record = self.repository.get_expense_by_period(
                fund=self.fund,
                period_type=period_type,
                period_year=period_year,
                period_month=period_month,
                period_quarter=period_quarter
            )
            
            income_record = self.repository.get_income_by_period(
                fund=self.fund,
                period_type=period_type,
                period_year=period_year,
                period_month=period_month,
                period_quarter=period_quarter
            )
            
            # 3. Extraer componentes
            capex = Decimal('0.00')
            debt_service = Decimal('0.00')
            debt_principal = Decimal('0.00')
            debt_interest = Decimal('0.00')
            non_operating_income = Decimal('0.00')
            non_operating_expenses = Decimal('0.00')
            
            if expense_record:
                capex = expense_record.capex or Decimal('0.00')
                debt_principal = expense_record.debt_principal_payment or Decimal('0.00')
                debt_interest = expense_record.debt_interest_payment or Decimal('0.00')
                debt_service = debt_principal + debt_interest
                non_operating_expenses = expense_record.non_operating_expenses or Decimal('0.00')
            
            if income_record:
                non_operating_income = income_record.non_operating_income or Decimal('0.00')
            
            # 4. Formula
            # FCF = NOI + Ingresos no operativos - Gastos no operativos - CAPEX - Deuda
            fcf = noi + non_operating_income - non_operating_expenses - capex - debt_service
            
            # 5. Calcular FCF por unidad
            total_units = self.fund.amount_tokens or 0
            fcf_per_unit = self._safe_divide(fcf, Decimal(str(total_units))) if total_units > 0 else Decimal('0.00')
            
            return {
                **self._get_fund_info(),
                'period_type': period_type,
                'period_year': period_year,
                'period_month': period_month,
                'period_quarter': period_quarter,
                'period_display': self._format_period_display(period_type, period_year, period_month, period_quarter),
                
                # FCF principal
                'free_cash_flow': float(fcf),
                'fcf_per_unit': float(fcf_per_unit),
                
                # Componentes
                'fcf_components': {
                    'noi': float(noi),
                    'capex': float(capex),
                    'debt_service': float(debt_service),
                    'debt_principal': float(debt_principal) if expense_record else 0,
                    'debt_interest': float(debt_interest) if expense_record else 0,
                    'non_operating_income': float(non_operating_income)
                },
                
                # Metadata
                'total_units_issued': total_units,
                'calculation_date': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': f'Error: {str(e)}',
                **self._get_fund_info()
            }
    
    def _calculate_last_12_months(self, months_back: int, include_breakdown: bool) -> Dict[str, Any]:
        """Calcula FCF de los ÚLTIMOS N MESES"""
        
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
            
            # 1. Obtener NOI de los últimos N meses
            noi_result = self.noi_strategy.calculate(
                months_back=months_back,
                include_breakdown=False
            )
            
            if 'error' in noi_result:
                return {
                    'error': f'Error calculando NOI: {noi_result["error"]}',
                    **self._get_fund_info()
                }
            
            total_noi = Decimal(str(noi_result.get('total_noi_12m', 0)))
            
            # 2. Obtener gastos e ingresos agregados
            expenses = self.repository.get_expense_range(
                fund=self.fund,
                period_type='monthly',
                start_year=start_year,
                start_month=start_month,
                end_year=last_completed_year,
                end_month=last_completed_month
            )
            
            incomes = self.repository.get_income_range(
                fund=self.fund,
                period_type='monthly',
                start_year=start_year,
                start_month=start_month,
                end_year=last_completed_year,
                end_month=last_completed_month
            )
            
            # 3. Agregar componentes
            capex_sum = expenses.aggregate(total=Sum('capex'))['total'] or Decimal('0.00')
            
            debt_principal_sum = expenses.aggregate(total=Sum('debt_principal_payment'))['total'] or Decimal('0.00')
            debt_interest_sum = expenses.aggregate(total=Sum('debt_interest_payment'))['total'] or Decimal('0.00')
            debt_service_sum = debt_principal_sum + debt_interest_sum
            
            # ✅ AGREGADO: Sumar ingresos y gastos no operativos
            non_op_income_sum = incomes.aggregate(total=Sum('non_operating_income'))['total'] or Decimal('0.00')
            non_op_expense_sum = expenses.aggregate(total=Sum('non_operating_expenses'))['total'] or Decimal('0.00')
            
            # 4. ✅ FÓRMULA CORREGIDA
            # FCF = NOI + Ingresos no operativos - Gastos no operativos - CAPEX - Deuda
            total_fcf = total_noi + non_op_income_sum - non_op_expense_sum - capex_sum - debt_service_sum
            
            # 5. Calcular métricas
            total_units = self.fund.amount_tokens or 0
            fcf_per_unit = self._safe_divide(total_fcf, Decimal(str(total_units))) if total_units > 0 else Decimal('0.00')
            average_monthly_fcf = total_fcf / months_back
            
            result = {
                **self._get_fund_info(),
                'period_analyzed': f'{months_back} meses ({start_year}-{start_month:02d} a {last_completed_year}-{last_completed_month:02d})',
                'start_period': f'{start_year}-{start_month:02d}',
                'end_period': f'{last_completed_year}-{last_completed_month:02d}',
                'months_back': months_back,
                
                # FCF del período
                'total_fcf_12m': float(total_fcf),
                'fcf_per_unit': float(fcf_per_unit),
                'average_monthly_fcf': float(average_monthly_fcf),
                
                # Componentes
                'fcf_components': {
                    'total_noi': float(total_noi),
                    'total_capex': float(capex_sum),
                    'total_debt_service': float(debt_service_sum),
                    'debt_principal': float(debt_principal_sum),
                    'debt_interest': float(debt_interest_sum),
                    'non_operating_income': float(non_op_income_sum),
                    'non_operating_expenses': float(non_op_expense_sum)
                },
                
                # Metadata
                'total_units_issued': total_units,
                'expense_periods_count': expenses.count(),
                'income_periods_count': incomes.count(),
                'calculation_date': timezone.now().isoformat()
            }
            
            # 6. Desglose mensual
            if include_breakdown:
                expenses_dict = {(e.period_year, e.period_month): e for e in expenses}
                incomes_dict = {(i.period_year, i.period_month): i for i in incomes}
                
                # Obtener NOI mensual
                noi_monthly_result = self.noi_strategy.calculate(
                    months_back=months_back,
                    include_breakdown=True
                )
                
                monthly_breakdown = []
                
                if 'monthly_breakdown' in noi_monthly_result:
                    for noi_month in noi_monthly_result['monthly_breakdown']:
                        year = noi_month['period_year']
                        month = noi_month['period_month']
                        
                        expense = expenses_dict.get((year, month))
                        income = incomes_dict.get((year, month))
                        
                        month_noi = Decimal(str(noi_month['noi']))
                        month_capex = expense.capex or Decimal('0.00') if expense else Decimal('0.00')
                        
                        month_debt_principal = expense.debt_principal_payment or Decimal('0.00') if expense else Decimal('0.00')
                        month_debt_interest = expense.debt_interest_payment or Decimal('0.00') if expense else Decimal('0.00')
                        month_debt = month_debt_principal + month_debt_interest
                        
                        month_non_op_inc = income.non_operating_income or Decimal('0.00') if income else Decimal('0.00')
                        
                        month_fcf = month_noi - month_capex - month_debt + month_non_op_inc
                        
                        monthly_breakdown.append({
                            'period_display': noi_month['period_display'],
                            'period_year': year,
                            'period_month': month,
                            'noi': float(month_noi),
                            'capex': float(month_capex),
                            'debt_principal': float(month_debt_principal),
                            'debt_interest': float(month_debt_interest),
                            'debt_service': float(month_debt),
                            'non_operating_income': float(month_non_op_inc),
                            'fcf': float(month_fcf),
                            'fcf_per_unit': float(self._safe_divide(month_fcf, Decimal(str(total_units)))) if total_units > 0 else 0
                        })
                
                result['monthly_breakdown'] = monthly_breakdown
            
            return result
            
        except Exception as e:
            return {
                'error': f'Error: {str(e)}',
                **self._get_fund_info(),
                'total_fcf_12m': 0
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