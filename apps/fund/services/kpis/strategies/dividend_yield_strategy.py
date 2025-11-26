"""
Dividend Yield Calculation Strategy para Fund Investment
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Q

from ..core.base_strategy import BaseKPIStrategy
from apps.fund.models.core import Fund
from apps.fund.models.membership import FundInvestment
from apps.fund.models.distributions import DistributionPeriod, InvestmentDistributionRecord


class DividendYieldCalculationStrategy(BaseKPIStrategy):
    """
    Strategy para calcular Dividend Yield de una inversión específica.
    
    El retorno periódico que recibe un inversionista individual basado en 
    las distribuciones REALES pagadas a su inversión.
    
    Formula:
    Dividend Yield = (Dividendo Pagado / Valor Compra Inicial) × 100
    
    Donde:
    - Dividendo Pagado: net_distribution_amount_cop de InvestmentDistributionRecord
    - Valor Compra Inicial: investment_amount de FundInvestment
    """
    
    def __init__(self, fund: Fund):
        super().__init__(fund)
    
    def validate_prerequisites(self) -> Dict[str, bool]:
        """Valida que el fondo sea válido"""
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
        investment_id: int,
        period_type: str = 'monthly',
        period_year: Optional[int] = None,
        period_month: Optional[int] = None,
        period_quarter: Optional[int] = None,
        months_back: Optional[int] = None  # ✅ NUEVO PARÁMETRO
    ) -> Dict[str, Any]:
        """Calcula Dividend Yield para una inversión específica"""
        
        # 1. Validar prerequisites
        prereq = self.validate_prerequisites()
        if not prereq['is_valid']:
            return {
                'error': 'Fund prerequisites not met',
                **self._get_fund_info(),
                'validations': prereq['validations']
            }
        
        # 2. Obtener la inversión
        try:
            investment = FundInvestment.objects.select_related(
                'application__fund',
                'application__user'
            ).get(
                id=investment_id,
                application__fund=self.fund
            )
        except FundInvestment.DoesNotExist:
            return {
                'error': f'Inversión con ID {investment_id} no encontrada o no pertenece al fondo',
                **self._get_fund_info(),
                'investment_id': investment_id
            }
        
        # ✅ NUEVA LÓGICA: Si especifica months_back, calcular últimos N meses
        if months_back:
            return self._calculate_rolling_period_yield(investment, months_back)
        
        # 3. Si hay período específico, calcular para ese período
        if period_year and (period_month or period_quarter):
            return self._calculate_period_yield(investment, period_type, period_year, period_month, period_quarter)
        
        # 4. Si no, calcular acumulado desde el inicio de la inversión
        return self._calculate_total_yield(investment)
    
    def _calculate_period_yield(
        self,
        investment: FundInvestment,
        period_type: str,
        period_year: int,
        period_month: Optional[int],
        period_quarter: Optional[int]
    ) -> Dict[str, Any]:
        """Calcula Dividend Yield para UN período específico"""
        
        try:
            # 1. Buscar el DistributionPeriod correspondiente
            filters = {
                'fund': self.fund,
                'distribution_type': period_type,
                'period_year': period_year
            }
            
            if period_type == 'monthly' and period_month:
                filters['period_month'] = period_month
            elif period_type == 'quarterly' and period_quarter:
                filters['period_quarter'] = period_quarter
            
            distribution_period = DistributionPeriod.objects.filter(**filters).first()
            
            if not distribution_period:
                return {
                    'error': 'No existe distribución para el período especificado',
                    **self._get_fund_info(),
                    'investment_id': investment.id,
                    'period_searched': {
                        'period_type': period_type,
                        'period_year': period_year,
                        'period_month': period_month,
                        'period_quarter': period_quarter
                    }
                }
            
            # 2. Obtener el registro de distribución para esta inversión específica
            distribution_record = InvestmentDistributionRecord.objects.filter(
                distribution_period=distribution_period,
                investment=investment
            ).first()
            
            if not distribution_record:
                return {
                    'error': 'No hay registro de distribución para esta inversión en el período',
                    **self._get_fund_info(),
                    'investment_id': investment.id,
                    'investor_name': investment.application.user.get_full_name(),
                    'distribution_period_id': distribution_period.id
                }
            
            # 3. ✅ CORRECCIÓN: Usar net_distribution_amount_cop
            dividendo_pagado_periodo = distribution_record.net_distribution_amount_cop or Decimal('0.00')
            
            # 4. Obtener valor de compra inicial de la inversión
            valor_compra_inicial = investment.final_invested_amount
            
            # 5. Calcular Dividend Yield del período
            dividend_yield_period = (dividendo_pagado_periodo / valor_compra_inicial) * 100 if valor_compra_inicial > 0 else Decimal('0.00')
            
            # 6. Anualizar si es necesario
            dividend_yield_annualized = None
            periods_per_year = None
            
            if period_type == 'monthly':
                periods_per_year = 12
                dividend_yield_annualized = dividend_yield_period * 12
            elif period_type == 'quarterly':
                periods_per_year = 4
                dividend_yield_annualized = dividend_yield_period * 4
            
            # 7. Interpretación
            yield_to_interpret = dividend_yield_annualized if dividend_yield_annualized else dividend_yield_period
            interpretation = self._interpret_dividend_yield(
                float(yield_to_interpret), 
                is_annualized=bool(dividend_yield_annualized)
            )
            
            return {
                **self._get_fund_info(),
                
                # Información de la inversión
                'investment_info': {
                    'investment_id': investment.id,
                    'investor_id': investment.application.user.id,
                    'investor_name': investment.application.user.get_full_name(),
                    'investor_email': investment.application.user.email,
                    'investment_date': investment.created_at.strftime("%Y-%m-%d"),
                    'tokens_owned': investment.units_owned,
                    'investment_amount': float(valor_compra_inicial)
                },
                
                # Información del período
                'period_info': {
                    'period_type': period_type,
                    'period_year': period_year,
                    'period_month': period_month,
                    'period_quarter': period_quarter,
                    'period_display': distribution_period.period_display,
                    'distribution_period_id': distribution_period.id
                },
                
                # Dividend Yield principal
                'dividend_yield_metrics': {
                    'dividend_yield_period_percentage': float(dividend_yield_period),
                    'dividend_yield_annualized_percentage': float(dividend_yield_annualized) if dividend_yield_annualized else None,
                    'dividendo_pagado_periodo': float(dividendo_pagado_periodo),
                    'valor_compra_inicial': float(valor_compra_inicial),
                    'interpretation': interpretation,
                    'performance_level': self._get_performance_level(float(yield_to_interpret))
                },
                
                # ✅ CORRECCIÓN: Campos reales del modelo
                'distribution_metrics': {
                    'gross_amount_cop': float(distribution_record.gross_distribution_amount_cop or 0),
                    'withholding_tax_cop': float(distribution_record.withholding_tax_cop or 0),
                    'net_amount_cop': float(distribution_record.net_distribution_amount_cop or 0),
                    'tokens_held_on_record_date': distribution_record.tokens_held_on_record_date,
                    'participation_percentage': float(distribution_record.participation_percentage),
                    'payment_date': distribution_record.payment_date.strftime("%Y-%m-%d") if distribution_record.payment_date else None,
                    'payment_status': distribution_record.payment_status
                },
                
                # Metadata
                'calculation_date': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': f'Error: {str(e)}',
                **self._get_fund_info(),
                'investment_id': investment.id
            }
    
    def _calculate_total_yield(self, investment: FundInvestment) -> Dict[str, Any]:
        """Calcula Dividend Yield acumulado desde el inicio de la inversión"""
        
        try:
            # 1. Obtener TODAS las distribuciones de esta inversión
            distribution_records = InvestmentDistributionRecord.objects.filter(
                investment=investment
            ).select_related('distribution_period').order_by(
                'distribution_period__period_year', 
                'distribution_period__period_month'
            )
            
            if not distribution_records.exists():
                return {
                    'error': 'No hay distribuciones para esta inversión',
                    **self._get_fund_info(),
                    'investment_id': investment.id,
                    'investor_name': investment.application.user.get_full_name()
                }
            
            # 2. ✅ CORRECCIÓN: Sumar net_distribution_amount_cop
            total_dividendo_pagado = distribution_records.aggregate(
                total=Sum('net_distribution_amount_cop')
            )['total'] or Decimal('0.00')
            
            # 3. Obtener valor de compra inicial
            valor_compra_inicial = investment.final_invested_amount
            
            # 4. Calcular Dividend Yield acumulado
            dividend_yield_total = (total_dividendo_pagado / valor_compra_inicial) * 100 if valor_compra_inicial > 0 else Decimal('0.00')
            
            # 5. Calcular promedio mensual
            months_count = distribution_records.count()
            dividend_yield_monthly_avg = dividend_yield_total / months_count if months_count > 0 else Decimal('0.00')
            
            # 6. Anualizar el promedio mensual
            dividend_yield_annualized = dividend_yield_monthly_avg * 12
            
            # 7. Calcular días desde la inversión
            days_since_investment = (timezone.now().date() - investment.created_at.date()).days
            
            # 8. Interpretación
            interpretation = self._interpret_dividend_yield(
                float(dividend_yield_annualized), 
                is_annualized=True
            )
            
            # 9. Obtener primer y último período
            first_distribution = distribution_records.first()
            last_distribution = distribution_records.last()
            
            return {
                **self._get_fund_info(),
                
                # Información de la inversión
                'investment_info': {
                    'investment_id': investment.id,
                    'investor_id': investment.application.user.id,
                    'investor_name': investment.application.user.get_full_name(),
                    'investor_email': investment.application.user.email,
                    'investment_date': investment.created_at.strftime("%Y-%m-%d"),
                    'days_since_investment': days_since_investment,
                    'tokens_owned': investment.units_owned,
                    'investment_amount': float(valor_compra_inicial)
                },
                
                # Información del período analizado
                'period_info': {
                    'period_type': 'cumulative',
                    'period_display': f'Desde {first_distribution.distribution_period.period_display} hasta {last_distribution.distribution_period.period_display}',
                    'first_distribution_date': first_distribution.distribution_period.payment_date.strftime("%Y-%m-%d"),
                    'last_distribution_date': last_distribution.distribution_period.payment_date.strftime("%Y-%m-%d"),
                    'total_distributions_count': months_count
                },
                
                # Dividend Yield principal
                'dividend_yield_metrics': {
                    'dividend_yield_total_percentage': float(dividend_yield_total),
                    'dividend_yield_annualized_percentage': float(dividend_yield_annualized),
                    'dividend_yield_monthly_avg_percentage': float(dividend_yield_monthly_avg),
                    'total_dividendo_pagado': float(total_dividendo_pagado),
                    'valor_compra_inicial': float(valor_compra_inicial),
                    'interpretation': interpretation,
                    'performance_level': self._get_performance_level(float(dividend_yield_annualized))
                },
                
                # Métricas acumuladas
                'cumulative_metrics': {
                    'total_distributions_received': months_count,
                    'total_amount_received': float(total_dividendo_pagado),
                    'average_distribution_amount': float(total_dividendo_pagado / months_count) if months_count > 0 else 0,
                    'roi_to_date': float((total_dividendo_pagado / valor_compra_inicial) * 100) if valor_compra_inicial > 0 else 0
                },
                
                # Metadata
                'calculation_date': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': f'Error: {str(e)}',
                **self._get_fund_info(),
                'investment_id': investment.id
            }
            
    def _calculate_rolling_period_yield(
        self, 
        investment: FundInvestment, 
        months_back: int
    ) -> Dict[str, Any]:
        """Calcula Dividend Yield de los últimos N meses"""
        
        try:
            from datetime import timedelta
            from dateutil.relativedelta import relativedelta
            
            # 1. Calcular fecha de inicio (N meses atrás desde hoy)
            end_date = timezone.now().date()
            start_date = end_date - relativedelta(months=months_back)
            
            # 2. Obtener distribuciones de los últimos N meses
            distribution_records = InvestmentDistributionRecord.objects.filter(
                investment=investment,
                distribution_period__payment_date__gte=start_date,
                distribution_period__payment_date__lte=end_date
            ).select_related('distribution_period').order_by(
                'distribution_period__period_year', 
                'distribution_period__period_month'
            )
            
            if not distribution_records.exists():
                return {
                    'error': f'No hay distribuciones en los últimos {months_back} meses para esta inversión',
                    **self._get_fund_info(),
                    'investment_id': investment.id,
                    'investor_name': investment.application.user.get_full_name(),
                    'months_back': months_back,
                    'start_date': start_date.strftime("%Y-%m-%d"),
                    'end_date': end_date.strftime("%Y-%m-%d")
                }
            
            # 3. Sumar distribuciones del período
            total_dividendo_periodo = distribution_records.aggregate(
                total=Sum('net_distribution_amount_cop')
            )['total'] or Decimal('0.00')
            
            # 4. Obtener valor de compra inicial
            valor_compra_inicial = investment.final_invested_amount
            
            # 5. Calcular Dividend Yield del período
            dividend_yield_period = (total_dividendo_periodo / valor_compra_inicial) * 100 if valor_compra_inicial > 0 else Decimal('0.00')
            
            # 6. Anualizar (proyectar a 12 meses)
            dividend_yield_annualized = (dividend_yield_period / months_back) * 12
            
            # 7. Calcular promedio mensual
            months_count = distribution_records.count()
            dividend_yield_monthly_avg = dividend_yield_period / months_count if months_count > 0 else Decimal('0.00')
            
            # 8. Interpretación
            interpretation = self._interpret_dividend_yield(
                float(dividend_yield_annualized), 
                is_annualized=True
            )
            
            # 9. Obtener primer y último período
            first_distribution = distribution_records.first()
            last_distribution = distribution_records.last()
            
            return {
                **self._get_fund_info(),
                
                # Información de la inversión
                'investment_info': {
                    'investment_id': investment.id,
                    'investor_id': investment.application.user.id,
                    'investor_name': investment.application.user.get_full_name(),
                    'investor_email': investment.application.user.email,
                    'investment_date': investment.created_at.strftime("%Y-%m-%d"),
                    'tokens_owned': investment.units_owned,
                    'investment_amount': float(valor_compra_inicial)
                },
                
                # Información del período analizado
                'period_info': {
                    'period_type': 'rolling',
                    'months_back': months_back,
                    'start_date': start_date.strftime("%Y-%m-%d"),
                    'end_date': end_date.strftime("%Y-%m-%d"),
                    'period_display': f'Últimos {months_back} meses',
                    'first_distribution_date': first_distribution.distribution_period.payment_date.strftime("%Y-%m-%d"),
                    'last_distribution_date': last_distribution.distribution_period.payment_date.strftime("%Y-%m-%d"),
                    'total_distributions_count': months_count
                },
                
                # Dividend Yield principal
                'dividend_yield_metrics': {
                    'dividend_yield_period_percentage': float(dividend_yield_period),
                    'dividend_yield_annualized_percentage': float(dividend_yield_annualized),
                    'dividend_yield_monthly_avg_percentage': float(dividend_yield_monthly_avg),
                    'total_dividendo_pagado': float(total_dividendo_periodo),
                    'valor_compra_inicial': float(valor_compra_inicial),
                    'interpretation': interpretation,
                    'performance_level': self._get_performance_level(float(dividend_yield_annualized))
                },
                
                # Métricas del período
                'period_metrics': {
                    'distributions_in_period': months_count,
                    'total_amount_received': float(total_dividendo_periodo),
                    'average_distribution_amount': float(total_dividendo_periodo / months_count) if months_count > 0 else 0
                },
                
                # Metadata
                'calculation_date': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': f'Error: {str(e)}',
                **self._get_fund_info(),
                'investment_id': investment.id
            }            
    
    def _interpret_dividend_yield(self, dividend_yield: float, is_annualized: bool = False) -> str:
        """Interpreta el Dividend Yield"""
        period_text = "anualizado" if is_annualized else "del período"
        
        if dividend_yield >= 10:
            return f"Excelente rendimiento {period_text}: La inversión genera distribuciones significativas."
        elif dividend_yield >= 7:
            return f"Muy buen rendimiento {period_text}: Distribuciones sólidas y consistentes."
        elif dividend_yield >= 5:
            return f"Buen rendimiento {period_text}: Distribuciones aceptables, en línea con el mercado."
        elif dividend_yield >= 3:
            return f"Rendimiento moderado {period_text}: Distribuciones modestas."
        elif dividend_yield > 0:
            return f"Rendimiento bajo {period_text}: Distribuciones limitadas."
        else:
            return f"Sin rendimiento {period_text}: No se han recibido distribuciones."
    
    def _get_performance_level(self, dividend_yield: float) -> str:
        """Determina el nivel de desempeño"""
        if dividend_yield >= 10:
            return "excellent"
        elif dividend_yield >= 7:
            return "very_good"
        elif dividend_yield >= 5:
            return "good"
        elif dividend_yield >= 3:
            return "moderate"
        elif dividend_yield > 0:
            return "poor"
        else:
            return "none"