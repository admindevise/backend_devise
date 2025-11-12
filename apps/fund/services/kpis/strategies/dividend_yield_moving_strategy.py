"""
Dividend Yield Moving Average Calculation Strategy para Fund
"""

from typing import Dict, Any, List
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Q
import math

from ..core.base_strategy import BaseKPIStrategy
from apps.fund.models.core import Fund
from apps.fund.models.distributions import DistributionPeriod


class DividendYieldMovingAverageStrategy(BaseKPIStrategy):
    """
    Strategy para calcular Dividend Yield Promedio Móvil del fondo.
    
    El promedio de los Dividend Yields pagados durante un período determinado.
    Muestra la consistencia y estabilidad de las distribuciones a lo largo del tiempo.
    
    Formula:
    Dividend Yield Promedio = Σ(Dividend Yields) / Número de Períodos
    
    Donde cada Dividend Yield = (distribution_per_token / price_per_unit) × 100
    
    Example:
        >>> strategy = DividendYieldMovingAverageStrategy(fund)
        >>> result = strategy.calculate(months_back=12)
        >>> print(f"Dividend Yield Promedio: {result['average_dividend_yield_percentage']:.2f}%")
    """
    
    def __init__(self, fund: Fund):
        super().__init__(fund)
    
    def validate_prerequisites(self) -> Dict[str, bool]:
        """Valida que el fondo tenga los datos necesarios"""
        validations = {
            'fund_exists': self.fund is not None,
            'fund_has_id': bool(self.fund.pk if self.fund else False),
            'fund_is_active': self.fund.status == 'active' if self.fund else False,
            'has_units': bool(
                hasattr(self.fund, 'amount_tokens') and 
                self.fund.amount_tokens > 0
            ) if self.fund else False,
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
        months_back: int = 12,
        include_monthly_breakdown: bool = True
    ) -> Dict[str, Any]:
        """
        Calcula Dividend Yield Promedio Móvil.
        
        Args:
            months_back: Meses hacia atrás para análisis (default: 12)
            include_monthly_breakdown: Incluir desglose mensual
            
        Returns:
            dict: Resultado del Dividend Yield Promedio con métricas estadísticas
        """
        
        # 1. Validar prerequisites
        prereq = self.validate_prerequisites()
        if not prereq['is_valid']:
            return {
                'error': 'Fund prerequisites not met',
                **self._get_fund_info(),
                'validations': prereq['validations']
            }
        
        try:
            # 2. Determinar último mes completado (día 30)
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
            
            # Calcular mes de inicio
            start_month = last_completed_month
            start_year = last_completed_year - 1
            
            # 3. Obtener distribuciones de los últimos N meses
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
            
            # 4. Obtener valor actual del token
            valor_actual_token = self.fund.price_per_unit
            
            # 5. Calcular Dividend Yield para cada mes
            dividend_yields = []
            monthly_data = []
            
            for distribution in distributions:
                distribution_per_token = distribution.distribution_per_token
                
                # Calcular Dividend Yield del mes
                # Dividend Yield = (Dividendo por Token / Valor Actual Token) × 100
                if valor_actual_token and valor_actual_token > 0:
                    dividend_yield = (distribution_per_token / valor_actual_token) * 100
                else:
                    dividend_yield = Decimal('0.00')
                
                dividend_yields.append(float(dividend_yield))
                
                monthly_data.append({
                    'period_display': distribution.period_display,
                    'period_year': distribution.period_year,
                    'period_month': distribution.period_month,
                    'distribution_per_token': float(distribution_per_token),
                    'total_distribution_amount': float(distribution.total_distribution_amount),
                    'dividend_yield_percentage': float(dividend_yield),
                    'valor_actual_token': float(valor_actual_token),
                    'distribution_status': distribution.status
                })
            
            # 6. Calcular métricas estadísticas
            num_periods = len(dividend_yields)
            
            if num_periods == 0:
                return {
                    'error': 'No hay períodos con datos para calcular promedio',
                    **self._get_fund_info()
                }
            
            # Promedio
            average_dividend_yield = sum(dividend_yields) / num_periods
            
            # Máximo y mínimo
            max_dividend_yield = max(dividend_yields) if dividend_yields else 0
            min_dividend_yield = min(dividend_yields) if dividend_yields else 0
            
            # Desviación estándar
            variance = sum((dy - average_dividend_yield) ** 2 for dy in dividend_yields) / num_periods
            std_deviation = math.sqrt(variance)
            
            # Coeficiente de variación (CV = desviación estándar / promedio)
            coefficient_of_variation = (std_deviation / average_dividend_yield * 100) if average_dividend_yield > 0 else 0
            
            # Tendencia (simple: comparar primera mitad vs segunda mitad)
            mid_point = num_periods // 2
            first_half_avg = sum(dividend_yields[:mid_point]) / mid_point if mid_point > 0 else 0
            second_half_avg = sum(dividend_yields[mid_point:]) / (num_periods - mid_point) if (num_periods - mid_point) > 0 else 0
            trend_percentage = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
            
            # 7. Anualizar el promedio
            average_dividend_yield_annualized = average_dividend_yield * 12
            
            # 8. Calcular total distribuido en el período
            total_distributed = distributions.aggregate(
                total=Sum('total_distribution_amount')
            )['total'] or Decimal('0.00')
            
            total_per_token = distributions.aggregate(
                total=Sum('distribution_per_token')
            )['total'] or Decimal('0.00')
            
            # 9. Interpretación
            interpretation = self._interpret_moving_average(
                average_dividend_yield_annualized,
                std_deviation,
                coefficient_of_variation,
                trend_percentage
            )
            
            return {
                **self._get_fund_info(),
                
                # Información del período
                'period_info': {
                    'period_analyzed': f'{months_back} meses ({start_year}-{start_month:02d} a {last_completed_year}-{last_completed_month:02d})',
                    'start_period': f'{start_year}-{start_month:02d}',
                    'end_period': f'{last_completed_year}-{last_completed_month:02d}',
                    'months_analyzed': num_periods
                },
                
                # Dividend Yield Promedio principal
                'dividend_yield_metrics': {  # <-- Cambiar nombre aquí
                    'average_dividend_yield_percentage': average_dividend_yield,
                    'average_dividend_yield_annualized_percentage': average_dividend_yield_annualized,
                    'valor_actual_token': float(self.fund.price_per_unit),
                    'total_distributed_in_period': float(total_distributed),
                    'total_per_token_in_period': float(total_per_token),
                    'interpretation': interpretation,
                    'consistency_rating': self._get_consistency_rating(coefficient_of_variation)
                },
                
                # Métricas estadísticas
                'statistical_metrics': {
                    'max_dividend_yield_percentage': max_dividend_yield,
                    'min_dividend_yield_percentage': min_dividend_yield,
                    'range_percentage': max_dividend_yield - min_dividend_yield,
                    'standard_deviation_percentage': std_deviation,
                    'coefficient_of_variation_percentage': coefficient_of_variation,
                    'variance': variance
                },
                
                # Análisis de tendencia
                'trend_analysis': {
                    'first_half_average_percentage': first_half_avg,
                    'second_half_average_percentage': second_half_avg,
                    'trend_percentage': trend_percentage,
                    'trend_direction': 'increasing' if trend_percentage > 5 else ('decreasing' if trend_percentage < -5 else 'stable')
                },
                
                # Interpretación
                'interpretation': interpretation,
                'consistency_rating': self._get_consistency_rating(coefficient_of_variation),
                
                # Información del fondo
                'fund_metrics': {
                    'price_per_unit': float(valor_actual_token),
                    'total_tokens_issued': self.fund.amount_tokens
                },
                
                # Desglose mensual (opcional)
                'monthly_breakdown': monthly_data if include_monthly_breakdown else None,
                
                # Metadata
                'calculation_date': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': f'Error: {str(e)}',
                **self._get_fund_info()
            }
    
    def _interpret_moving_average(
        self,
        avg_yield: float,
        std_dev: float,
        cv: float,
        trend: float
    ) -> str:
        """Interpreta el Dividend Yield Promedio Móvil"""
        
        # Análisis de rendimiento promedio
        if avg_yield >= 10:
            yield_analysis = "Excelente rendimiento promedio"
        elif avg_yield >= 7:
            yield_analysis = "Buen rendimiento promedio"
        elif avg_yield >= 5:
            yield_analysis = "Rendimiento aceptable"
        else:
            yield_analysis = "Rendimiento bajo"
        
        # Análisis de consistencia (basado en CV)
        if cv < 10:
            consistency_analysis = "con distribuciones muy consistentes y predecibles"
        elif cv < 20:
            consistency_analysis = "con distribuciones moderadamente consistentes"
        elif cv < 30:
            consistency_analysis = "con cierta variabilidad en las distribuciones"
        else:
            consistency_analysis = "con alta variabilidad en las distribuciones"
        
        # Análisis de tendencia
        if trend > 5:
            trend_analysis = "La tendencia es creciente, lo que indica mejora en el rendimiento."
        elif trend < -5:
            trend_analysis = "La tendencia es decreciente, requiere revisión."
        else:
            trend_analysis = "La tendencia es estable."
        
        return f"{yield_analysis} ({avg_yield:.2f}% anualizado), {consistency_analysis}. {trend_analysis}"
    
    def _get_consistency_rating(self, cv: float) -> str:
        """Determina el rating de consistencia basado en CV"""
        if cv < 10:
            return "excellent"
        elif cv < 20:
            return "good"
        elif cv < 30:
            return "moderate"
        else:
            return "poor"