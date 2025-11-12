"""
Free Cash Flow Calculation Strategy
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from django.utils import timezone

from ..core.base_strategy import BaseKPIStrategy
from apps.asset.models.core import Asset
from .noi_strategy import NOICalculationStrategy
from ..repositories.operating_data_repository import OperatingDataRepository


class FreeCashFlowCalculationStrategy(BaseKPIStrategy):
    """
    Strategy para calcular Free Cash Flow (Flujo de Caja Libre).
    
    El dinero real disponible para distribuir a los inversionistas después de pagar
    TODOS los gastos, incluyendo deuda.
    
    Formula:
    FCF = NOI + Ingresos no operativos - Gastos no operativos - CAPEX - Pago de Deuda
    
    Donde:
    - NOI: Ingreso Operativo Neto
    - Ingresos no operativos: Ingresos ocasionales (multas de arrendamiento, etc)
    - Gastos no operativos: Gastos no necesarios para mantener el inmueble (ej: 4x1000, bancarios, asset management)
    - CAPEX: Gastos de capital (mejoras mayores)
    - Pago de Deuda: Principal + Intereses
    
    Interpretación:
    - FCF positivo: El activo genera efectivo disponible para distribución
    - FCF negativo: El activo requiere inyección de capital
    - FCF por token: Efectivo disponible por cada unidad de inversión
    
    Example:
        >>> strategy = FreeCashFlowCalculationStrategy(asset)
        >>> result = strategy.calculate(period_year=2024, period_month=6)
        >>> print(f"FCF: ${result['free_cash_flow']:,.2f}")
        >>> print(f"FCF por Token: ${result['fcf_per_token']:,.2f}")
    """
    
    def __init__(self, asset: Asset):
        super().__init__(asset)
        self.noi_strategy = NOICalculationStrategy(asset)
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
        """
        Calcula Free Cash Flow.
        
        Args:
            period_type: Tipo de período ('monthly', 'quarterly', 'annual')
            period_year: Año específico
            period_month: Mes específico
            period_quarter: Trimestre específico
            months_back: Meses hacia atrás (default: 12)
            include_breakdown: Incluir desglose mensual
            
        Returns:
            dict: Resultado del FCF con componentes
        """
        
        # 1. Validar prerequisites
        prereq = self.validate_prerequisites()
        if not prereq['is_valid']:
            return {
                'error': 'Asset prerequisites not met',
                'asset_id': self.asset.id if self.asset else None,
                'validations': prereq['validations']
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
        """Calcula FCF para UN período específico"""
        
        try:
            # 1. Obtener NOI usando NOICalculationStrategy
            noi_result = self.noi_strategy.calculate(
                period_type=period_type,
                period_year=period_year,
                period_month=period_month,
                period_quarter=period_quarter,
                include_breakdown=False
            )
            
            if 'error' in noi_result:
                return {
                    'error': f'Error calculando NOI: {noi_result["error"]}',
                    'asset_id': self.asset.id
                }
            
            noi = Decimal(str(noi_result.get('net_operating_income', 0)))
            
            # 2. Obtener registros de ingresos y gastos
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
            
            # 3. Extraer componentes no operativos
            non_operating_income = Decimal('0.00')
            non_operating_expenses = Decimal('0.00')
            capex = Decimal('0.00')
            debt_payment = Decimal('0.00')
            
            if income_record:
                # Ingresos no operativos (si existen campos específicos en tu modelo)
                non_operating_income = getattr(income_record, 'non_operating_income', Decimal('0.00')) or Decimal('0.00')
            
            if expense_record:
                # Gastos no operativos (ej: 4x1000, bancarios, asset management)
                non_operating_expenses = getattr(expense_record, 'non_operating_expenses', Decimal('0.00')) or Decimal('0.00')
                
                # CAPEX (gastos de capital, mejoras mayores)
                capex = getattr(expense_record, 'capex', Decimal('0.00')) or Decimal('0.00')
                
                # Pago de deuda (principal + intereses)
                debt_payment = getattr(expense_record, 'debt_payment', Decimal('0.00')) or Decimal('0.00')
            
            # 4. Calcular FCF
            # FCF = NOI + Ingresos no operativos - Gastos no operativos - CAPEX - Deuda
            fcf = noi + non_operating_income - non_operating_expenses - capex - debt_payment
            
            # 5. Calcular FCF por token
            total_tokens = self.asset.total_tokens_issued if hasattr(self.asset, 'total_tokens_issued') else 1
            fcf_per_token = fcf / Decimal(str(total_tokens)) if total_tokens > 0 else Decimal('0.00')
            
            # 6. Calcular margen de FCF
            total_income = noi_result.get('total_operating_income', 0)
            fcf_margin = (fcf / Decimal(str(total_income)) * 100) if total_income > 0 else Decimal('0.00')
            
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
                
                # FCF principal
                'free_cash_flow': float(fcf),
                'fcf_per_token': float(fcf_per_token),
                'fcf_margin_percentage': float(fcf_margin),
                
                # Componentes del cálculo
                'fcf_components': {
                    'noi': float(noi),
                    'non_operating_income': float(non_operating_income),
                    'non_operating_expenses': float(non_operating_expenses),
                    'capex': float(capex),
                    'debt_payment': float(debt_payment)
                },
                
                # Información adicional
                'total_tokens': total_tokens,
                'calculation_date': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': f'Error: {str(e)}',
                'asset_id': self.asset.id,
                'asset_code': self.asset.asset_code
            }
    
    def _calculate_last_12_months(self, include_breakdown: bool) -> Dict[str, Any]:
        """Calcula FCF de los ÚLTIMOS 12 MESES"""
        
        try:
            # 1. Obtener NOI anual usando NOICalculationStrategy
            noi_result = self.noi_strategy.calculate(
                months_back=12,
                include_breakdown=include_breakdown
            )
            
            if 'error' in noi_result:
                return {
                    'error': f'Error calculando NOI: {noi_result["error"]}',
                    'asset_id': self.asset.id
                }
            
            total_noi = Decimal(str(noi_result.get('total_noi_12m', 0)))
            
            # 2. Obtener rangos de ingresos y gastos
            current_date = timezone.now()
            
            # Lógica día 30
            if current_date.day < 30:
                if current_date.month == 1:
                    last_year = current_date.year - 1
                    last_month = 12
                else:
                    last_year = current_date.year
                    last_month = current_date.month - 1
            else:
                last_year = current_date.year
                last_month = current_date.month
            
            start_year = last_year - 1
            start_month = last_month
            
            incomes = self.repository.get_income_range(
                asset=self.asset,
                period_type='monthly',
                start_year=start_year,
                start_month=start_month,
                end_year=last_year,
                end_month=last_month
            )
            
            expenses = self.repository.get_expense_range(
                asset=self.asset,
                period_type='monthly',
                start_year=start_year,
                start_month=start_month,
                end_year=last_year,
                end_month=last_month
            )
            
            # 3. Sumar componentes no operativos
            from django.db.models import Sum
            
            non_op_income_sum = incomes.aggregate(
                total=Sum('non_operating_income')
            )['total'] or Decimal('0.00')
            
            expense_aggregates = expenses.aggregate(
                non_op_exp=Sum('non_operating_expenses'),
                capex_sum=Sum('capex'),
                debt_sum=Sum('debt_payment')
            )
            
            non_op_expenses_sum = expense_aggregates['non_op_exp'] or Decimal('0.00')
            capex_sum = expense_aggregates['capex_sum'] or Decimal('0.00')
            debt_sum = expense_aggregates['debt_sum'] or Decimal('0.00')
            
            # 4. Calcular FCF anual
            total_fcf = total_noi + non_op_income_sum - non_op_expenses_sum - capex_sum - debt_sum
            
            # 5. Calcular FCF por token
            total_tokens = self.asset.total_tokens_issued if hasattr(self.asset, 'total_tokens_issued') else 1
            fcf_per_token = total_fcf / Decimal(str(total_tokens)) if total_tokens > 0 else Decimal('0.00')
            
            # 6. Calcular métricas
            total_income = Decimal(str(noi_result.get('total_operating_income_12m', 0)))
            fcf_margin = (total_fcf / total_income * 100) if total_income > 0 else Decimal('0.00')
            average_monthly_fcf = total_fcf / 12
            
            result = {
                'asset_id': self.asset.id,
                'asset_code': self.asset.asset_code,
                'asset_name': self.asset.name,
                'fund_id': self.asset.fund.id,
                'fund_name': self.asset.fund.name,
                'period_analyzed': f'12 meses ({start_year}-{start_month:02d} a {last_year}-{last_month:02d})',
                'start_period': f'{start_year}-{start_month:02d}',
                'end_period': f'{last_year}-{last_month:02d}',
                
                # FCF anual
                'total_fcf_12m': float(total_fcf),
                'fcf_per_token': float(fcf_per_token),
                'fcf_margin_percentage': float(fcf_margin),
                'average_monthly_fcf': float(average_monthly_fcf),
                
                # Componentes
                'fcf_components_12m': {
                    'total_noi': float(total_noi),
                    'non_operating_income': float(non_op_income_sum),
                    'non_operating_expenses': float(non_op_expenses_sum),
                    'capex': float(capex_sum),
                    'debt_payment': float(debt_sum)
                },
                
                # Información adicional
                'total_tokens': total_tokens,
                'months_with_data': incomes.count(),
                'calculation_date': timezone.now().isoformat()
            }
            
            # 7. Agregar desglose mensual si se solicita
            if include_breakdown:
                monthly_breakdown = []
                expenses_dict = {(e.period_year, e.period_month): e for e in expenses}
                
                for income in incomes:
                    expense = expenses_dict.get((income.period_year, income.period_month))
                    
                    # NOI del mes
                    month_noi = income.total_operating_income - (
                        expense.total_operating_expense if expense else Decimal('0.00')
                    )
                    
                    # Componentes no operativos
                    month_non_op_inc = getattr(income, 'non_operating_income', Decimal('0.00')) or Decimal('0.00')
                    month_non_op_exp = getattr(expense, 'non_operating_expenses', Decimal('0.00')) or Decimal('0.00') if expense else Decimal('0.00')
                    month_capex = getattr(expense, 'capex', Decimal('0.00')) or Decimal('0.00') if expense else Decimal('0.00')
                    month_debt = getattr(expense, 'debt_payment', Decimal('0.00')) or Decimal('0.00') if expense else Decimal('0.00')
                    
                    # FCF del mes
                    month_fcf = month_noi + month_non_op_inc - month_non_op_exp - month_capex - month_debt
                    
                    monthly_breakdown.append({
                        'period_display': income.period_display,
                        'period_year': income.period_year,
                        'period_month': income.period_month,
                        'noi': float(month_noi),
                        'non_operating_income': float(month_non_op_inc),
                        'non_operating_expenses': float(month_non_op_exp),
                        'capex': float(month_capex),
                        'debt_payment': float(month_debt),
                        'fcf': float(month_fcf),
                        'fcf_per_token': float(month_fcf / Decimal(str(total_tokens))) if total_tokens > 0 else 0
                    })
                
                result['monthly_breakdown'] = monthly_breakdown
            
            return result
            
        except Exception as e:
            return {
                'error': f'Error: {str(e)}',
                'asset_id': self.asset.id,
                'asset_code': self.asset.asset_code,
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