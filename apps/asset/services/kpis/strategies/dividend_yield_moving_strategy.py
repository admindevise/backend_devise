"""
Dividend Yield Moving Average Calculation Strategy
"""

from typing import Dict, Any, List
from decimal import Decimal
from django.utils import timezone

from ..core.base_strategy import BaseKPIStrategy
from apps.asset.models.core import Asset
from .dividend_yield_strategy import DividendYieldCalculationStrategy


class DividendYieldMovingAverageStrategy(BaseKPIStrategy):
    """
    Strategy para calcular Dividend Yield Promedio Móvil del activo.
    
    El promedio de los Dividend Yields pagados durante un período determinado.
    Muestra la consistencia y estabilidad de las distribuciones a lo largo del tiempo.
    
    Formula:
    Dividend Yield Promedio = Σ(Dividend Yields) / Número de Períodos
    
    Interpretación:
    - Mayor promedio = Distribuciones más consistentes y predecibles
    - Menor varianza = Mayor estabilidad en las distribuciones
    - Tendencia creciente = Mejora en rendimiento
    
    Example:
        >>> strategy = DividendYieldMovingAverageStrategy(asset)
        >>> result = strategy.calculate(months_back=12)
        >>> print(f"Dividend Yield Promedio: {result['average_dividend_yield_percentage']:.2f}%")
        >>> print(f"Desviación estándar: {result['standard_deviation_percentage']:.2f}%")
    """
    
    def __init__(self, asset: Asset):
        super().__init__(asset)
        self.dividend_yield_strategy = DividendYieldCalculationStrategy(asset)
    
    def validate_prerequisites(self) -> Dict[str, bool]:
        """Valida que el asset tenga los datos necesarios"""
        validations = {
            'asset_exists': self.asset is not None,
            'asset_has_id': bool(self.asset.pk if self.asset else False),
            'asset_is_active': self.asset.status == 'active' if self.asset else False,
            'has_tokens': bool(
                hasattr(self.asset, 'total_tokens_issued') and 
                self.asset.total_tokens_issued > 0
            ) if self.asset else False,
            'has_acquisition_value': bool(self.asset.acquisition_value) if self.asset else False
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
                'error': 'Asset prerequisites not met',
                'asset_id': self.asset.id if self.asset else None,
                'validations': prereq['validations']
            }
        
        try:
            # 2. Obtener FCF de los últimos N meses con desglose mensual
            from .free_cash_flow_strategy import FreeCashFlowCalculationStrategy
            fcf_strategy = FreeCashFlowCalculationStrategy(self.asset)
            
            fcf_result = fcf_strategy.calculate(
                months_back=months_back,
                include_breakdown=True  # Necesitamos desglose mensual
            )
            
            if 'error' in fcf_result:
                return {
                    'error': f'Error calculando FCF: {fcf_result["error"]}',
                    'asset_id': self.asset.id
                }
            
            # 3. Obtener valor de compra del token
            total_tokens = self.asset.total_tokens_issued
            acquisition_value = self.asset.acquisition_value
            valor_compra_token = acquisition_value / Decimal(str(total_tokens))
            
            # 4. Calcular Dividend Yield para cada mes
            monthly_breakdown = fcf_result.get('monthly_breakdown', [])
            
            if not monthly_breakdown:
                return {
                    'error': 'No hay datos mensuales disponibles para análisis',
                    'asset_id': self.asset.id
                }
            
            dividend_yields = []
            monthly_data = []
            
            for month_data in monthly_breakdown:
                fcf_per_token = Decimal(str(month_data.get('fcf_per_token', 0)))
                
                # Calcular Dividend Yield del mes
                if valor_compra_token > 0:
                    dividend_yield = (fcf_per_token / valor_compra_token) * 100
                else:
                    dividend_yield = Decimal('0.00')
                
                dividend_yields.append(float(dividend_yield))
                
                monthly_data.append({
                    'period_display': month_data.get('period_display'),
                    'period_year': month_data.get('period_year'),
                    'period_month': month_data.get('period_month'),
                    'fcf': month_data.get('fcf'),
                    'fcf_per_token': float(fcf_per_token),
                    'dividend_yield_percentage': float(dividend_yield),
                    'valor_compra_token': float(valor_compra_token)
                })
            
            # 5. Calcular métricas estadísticas
            num_periods = len(dividend_yields)
            
            if num_periods == 0:
                return {
                    'error': 'No hay períodos con datos para calcular promedio',
                    'asset_id': self.asset.id
                }
            
            # Promedio
            average_dividend_yield = sum(dividend_yields) / num_periods
            
            # Máximo y mínimo
            max_dividend_yield = max(dividend_yields) if dividend_yields else 0
            min_dividend_yield = min(dividend_yields) if dividend_yields else 0
            
            # Desviación estándar
            import math
            variance = sum((dy - average_dividend_yield) ** 2 for dy in dividend_yields) / num_periods
            std_deviation = math.sqrt(variance)
            
            # Coeficiente de variación (CV = desviación estándar / promedio)
            coefficient_of_variation = (std_deviation / average_dividend_yield * 100) if average_dividend_yield > 0 else 0
            
            # Tendencia (simple: comparar primera mitad vs segunda mitad)
            mid_point = num_periods // 2
            first_half_avg = sum(dividend_yields[:mid_point]) / mid_point if mid_point > 0 else 0
            second_half_avg = sum(dividend_yields[mid_point:]) / (num_periods - mid_point) if (num_periods - mid_point) > 0 else 0
            trend_percentage = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
            
            # 6. Anualizar el promedio
            average_dividend_yield_annualized = average_dividend_yield * 12
            
            # 7. Interpretación
            interpretation = self._interpret_moving_average(
                average_dividend_yield_annualized,
                std_deviation,
                coefficient_of_variation,
                trend_percentage
            )
            
            return {
                'asset_id': self.asset.id,
                'asset_code': self.asset.asset_code,
                'asset_name': self.asset.name,
                'fund_id': self.asset.fund.id,
                'fund_name': self.asset.fund.name,
                'period_analyzed': fcf_result.get('period_analyzed'),
                'months_analyzed': num_periods,
                
                # Dividend Yield Promedio principal
                'average_dividend_yield_percentage': average_dividend_yield,
                'average_dividend_yield_annualized_percentage': average_dividend_yield_annualized,
                'valor_compra_token': float(valor_compra_token),
                
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
                
                # Información del activo
                'asset_metrics': {
                    'total_tokens_issued': total_tokens,
                    'acquisition_value': float(acquisition_value)
                },
                
                # Desglose mensual (opcional)
                'monthly_breakdown': monthly_data if include_monthly_breakdown else None,
                
                # Metadata
                'calculation_date': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': f'Error: {str(e)}',
                'asset_id': self.asset.id,
                'asset_code': self.asset.asset_code
            }
    
    def _interpret_moving_average(
        self,
        avg_yield: float,
        std_dev: float,
        cv: float,
        trend: float
    ) -> str:
        """
        Interpreta el Dividend Yield Promedio Móvil.
        
        Args:
            avg_yield: Promedio anualizado
            std_dev: Desviación estándar
            cv: Coeficiente de variación
            trend: Tendencia porcentual
            
        Returns:
            str: Interpretación textual
        """
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
        """
        Determina el rating de consistencia basado en CV.
        
        Args:
            cv: Coeficiente de variación
            
        Returns:
            str: 'excellent', 'good', 'moderate', 'poor'
        """
        if cv < 10:
            return "excellent"
        elif cv < 20:
            return "good"
        elif cv < 30:
            return "moderate"
        else:
            return "poor"