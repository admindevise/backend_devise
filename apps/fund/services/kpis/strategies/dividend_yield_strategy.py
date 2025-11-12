"""
Dividend Yield Calculation Strategy para Fund
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Q

from ..core.base_strategy import BaseKPIStrategy
from apps.fund.models.core import Fund
from apps.fund.models.distributions import DistributionPeriod


class DividendYieldCalculationStrategy(BaseKPIStrategy):
    """
    Strategy para calcular Dividend Yield del fondo.
    
    El retorno periódico que recibe un holder de unidades basado en 
    las distribuciones reales pagadas.
    
    Formula:
    Dividend Yield = (Dividendo Pagado por Unidad / Valor Actual del Token) × 100
    
    Donde:
    - Dividendo Pagado: distribution_per_token del período
    - Valor Actual del Token: price_per_unit del fondo
    
    Example:
        Período específico:
        >>> strategy = DividendYieldCalculationStrategy(fund)
        >>> result = strategy.calculate(period_year=2024, period_month=12)
        
        Últimos 12 meses:
        >>> result = strategy.calculate()  # Sin parámetros = anualizado
    """
    
    def __init__(self, fund: Fund):
        super().__init__(fund)
    
    def validate_prerequisites(self) -> Dict[str, bool]:
        """Valida que el fondo tenga los datos necesarios"""
        validations = {
            'fund_exists': self.fund is not None,
            'fund_has_id': bool(self.fund.pk if self.fund else False),
            'fund_is_active': self.fund.status == 'active' if self.fund else False,
            'has_price_per_unit': bool(
                hasattr(self.fund, 'price_per_unit') and 
                self.fund.price_per_unit and
                self.fund.price_per_unit > 0
            ) if self.fund else False
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
        calculate_annualized: bool = True
    ) -> Dict[str, Any]:
        """
        Calcula Dividend Yield del fondo.
        
        Args:
            period_type: Tipo de período ('monthly', 'quarterly')
            period_year: Año específico (opcional)
            period_month: Mes específico (opcional)
            period_quarter: Trimestre específico (opcional)
            calculate_annualized: Si calcular yield anualizado
            
        Returns:
            dict: Resultado del Dividend Yield
        """
        
        # 1. Validar prerequisites
        prereq = self.validate_prerequisites()
        if not prereq['is_valid']:
            return {
                'error': 'Fund prerequisites not met',
                **self._get_fund_info(),
                'validations': prereq['validations']
            }
        
        # 2. Si no hay período específico, calcular últimos 12 meses
        if not period_year or not (period_month or period_quarter):
            return self._calculate_annualized_yield()
        
        # 3. Calcular para período específico
        return self._calculate_period_yield(
            period_type, period_year, period_month, period_quarter, calculate_annualized
        )
    
    def _calculate_period_yield(
        self,
        period_type: str,
        period_year: int,
        period_month: Optional[int],
        period_quarter: Optional[int],
        calculate_annualized: bool
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
                    'period_searched': {
                        'period_type': period_type,
                        'period_year': period_year,
                        'period_month': period_month,
                        'period_quarter': period_quarter
                    }
                }
            
            # 2. Obtener dividendo pagado por unidad del período
            dividendo_por_unidad = distribution_period.distribution_per_token
            
            # 3. Obtener valor actual del token/unidad del fondo
            valor_actual_token = self.fund.price_per_unit
            
            # 4. Calcular Dividend Yield del período
            # Dividend Yield = (Dividendo por Unidad / Valor Actual Token) × 100
            dividend_yield_period = (dividendo_por_unidad / valor_actual_token) * 100
            
            # 5. Calcular Dividend Yield anualizado (si se solicita)
            dividend_yield_annualized = None
            periods_per_year = None
            
            if calculate_annualized:
                if period_type == 'monthly':
                    periods_per_year = 12
                elif period_type == 'quarterly':
                    periods_per_year = 4
                elif period_type == 'semi_annually':
                    periods_per_year = 2
                else:  # annually
                    periods_per_year = 1
                
                dividend_yield_annualized = dividend_yield_period * periods_per_year
            
            # 6. Interpretación
            yield_to_interpret = dividend_yield_annualized if dividend_yield_annualized else dividend_yield_period
            interpretation = self._interpret_dividend_yield(
                float(yield_to_interpret), 
                is_annualized=bool(dividend_yield_annualized)
            )
            
            return {
                **self._get_fund_info(),
                
                # Información del período
                'period_info': {
                    'period_type': period_type,
                    'period_year': period_year,
                    'period_month': period_month,
                    'period_quarter': period_quarter,
                    'period_display': distribution_period.period_display,
                    'distribution_id': distribution_period.id,
                    'distribution_status': distribution_period.status
                },
                
                # Dividend Yield principal
                'dividend_yield_metrics': {
                    'dividend_yield_period_percentage': float(dividend_yield_period),
                    'dividend_yield_annualized_percentage': float(dividend_yield_annualized) if dividend_yield_annualized else None,
                    'dividendo_por_unidad': float(dividendo_por_unidad),
                    'valor_actual_token': float(valor_actual_token),
                    'interpretation': interpretation,
                    'performance_level': self._get_performance_level(float(yield_to_interpret))
                },
                
                # Métricas del período de distribución
                'distribution_metrics': {
                    'total_distribution_amount': float(distribution_period.total_distribution_amount),
                    'total_tokens_outstanding': distribution_period.total_tokens_outstanding,
                    'distribution_per_token': float(distribution_period.distribution_per_token),
                    'record_date': distribution_period.record_date.strftime("%Y-%m-%d"),
                    'payment_date': distribution_period.payment_date.strftime("%Y-%m-%d"),
                    'periods_per_year': periods_per_year
                },
                
                # Información del fondo
                'fund_metrics': {
                    'price_per_unit': float(valor_actual_token),
                    'total_tokens_issued': self.fund.amount_tokens
                },
                
                # Metadata
                'calculation_date': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': f'Error: {str(e)}',
                **self._get_fund_info()
            }
    
    def _calculate_annualized_yield(self) -> Dict[str, Any]:
        """Calcula Dividend Yield anualizado (últimos 12 meses completados)"""
        
        try:
            # 1. Determinar último mes completado (día 30)
            current_date = timezone.now()
            
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
            
            # Calcular mes de inicio (12 meses atrás)
            start_month = last_completed_month
            start_year = last_completed_year - 1
            
            # 2. Obtener distribuciones de los últimos 12 meses
            distributions = DistributionPeriod.objects.filter(
                fund=self.fund,
                distribution_type='monthly'
            ).filter(
                Q(period_year=start_year, period_month__gte=start_month) |
                Q(period_year__gt=start_year, period_year__lt=last_completed_year) |
                Q(period_year=last_completed_year, period_month__lte=last_completed_month)
            ).order_by('period_year', 'period_month')
            
            if not distributions.exists():
                return {
                    'error': 'No hay distribuciones en los últimos 12 meses',
                    **self._get_fund_info(),
                    'period_searched': f'{start_year}-{start_month:02d} a {last_completed_year}-{last_completed_month:02d}'
                }
            
            # 3. Sumar distribution_per_token de todos los períodos
            total_dividendo_12m = distributions.aggregate(
                total=Sum('distribution_per_token')
            )['total'] or Decimal('0.00')
            
            # 4. Obtener valor actual del token/unidad del fondo
            valor_actual_token = self.fund.price_per_unit
            
            # ✅ CORRECCIÓN: Calcular Dividend Yield anualizado
            # Dividend Yield = (Dividendo Anual por Unidad / Valor Actual Token) × 100
            if valor_actual_token and valor_actual_token > 0:
                dividend_yield_annualized = (total_dividendo_12m / valor_actual_token) * 100
            else:
                return {
                    'error': 'El valor actual del token (price_per_unit) es cero o inválido',
                    **self._get_fund_info(),
                    'valor_actual_token': float(valor_actual_token) if valor_actual_token else None
                }
            
            # 6. Calcular yield mensual promedio
            dividend_yield_monthly_avg = dividend_yield_annualized / 12
            
            # 7. Interpretación
            interpretation = self._interpret_dividend_yield(
                float(dividend_yield_annualized), 
                is_annualized=True
            )
            
            return {
                **self._get_fund_info(),
                
                # Información del período
                'period_info': {
                    'period_type': 'monthly',
                    'period_year': None,
                    'period_month': None,
                    'period_quarter': None,
                    'period_display': f'12 meses ({start_year}-{start_month:02d} a {last_completed_year}-{last_completed_month:02d})',
                    'start_period': f'{start_year}-{start_month:02d}',
                    'end_period': f'{last_completed_year}-{last_completed_month:02d}'
                },
                
                # Dividend Yield principal
                'dividend_yield_metrics': {
                    'dividend_yield_period_percentage': None,
                    'dividend_yield_annualized_percentage': float(dividend_yield_annualized),  # ✅ Ahora tiene valor
                    'dividend_yield_monthly_avg_percentage': float(dividend_yield_monthly_avg),  # ✅ Ahora tiene valor
                    'dividendo_por_unidad': float(total_dividendo_12m),
                    'valor_actual_token': float(valor_actual_token),
                    'interpretation': interpretation,  # ✅ Ahora tiene valor
                    'performance_level': self._get_performance_level(float(dividend_yield_annualized))  # ✅ Ahora tiene valor
                },
                
                # Métricas del período
                'period_metrics': {
                    'total_dividendo_12m': float(total_dividendo_12m),
                    'distributions_count': distributions.count(),
                    'average_distribution_per_token': float(total_dividendo_12m / distributions.count()) if distributions.count() > 0 else 0,
                    'total_distribution_amount_12m': float(distributions.aggregate(total=Sum('total_distribution_amount'))['total'] or 0)
                },
                
                # Información del fondo
                'fund_metrics': {
                    'price_per_unit': float(valor_actual_token),
                    'total_tokens_issued': self.fund.amount_tokens
                },
                
                # Metadata
                'calculation_date': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': f'Error: {str(e)}',
                **self._get_fund_info()
            }
    
    def _interpret_dividend_yield(self, dividend_yield: float, is_annualized: bool = False) -> str:
        """
        Interpreta el Dividend Yield.
        
        Args:
            dividend_yield: Valor del Dividend Yield en porcentaje
            is_annualized: Si el yield está anualizado
            
        Returns:
            str: Interpretación textual
        """
        period_text = "anualizado" if is_annualized else "del período"
        
        if dividend_yield >= 10:
            return f"Excelente rendimiento {period_text}: El fondo distribuye un flujo de caja significativo a los holders."
        elif dividend_yield >= 7:
            return f"Muy buen rendimiento {period_text}: Distribuciones sólidas y consistentes."
        elif dividend_yield >= 5:
            return f"Buen rendimiento {period_text}: Distribuciones aceptables, en línea con el mercado."
        elif dividend_yield >= 3:
            return f"Rendimiento moderado {period_text}: Distribuciones modestas."
        elif dividend_yield > 0:
            return f"Rendimiento bajo {period_text}: Distribuciones limitadas. Revisar eficiencia operativa."
        else:
            return f"Sin rendimiento {period_text}: El fondo no está generando distribuciones."
    
    def _get_performance_level(self, dividend_yield: float) -> str:
        """
        Determina el nivel de desempeño basado en Dividend Yield.
        
        Args:
            dividend_yield: Valor del Dividend Yield en porcentaje
            
        Returns:
            str: 'excellent', 'very_good', 'good', 'moderate', 'poor', 'none'
        """
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