"""
Dividend Yield Calculation Strategy
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from django.utils import timezone

from ..core.base_strategy import BaseKPIStrategy
from apps.asset.models.core import Asset
from .free_cash_flow_strategy import FreeCashFlowCalculationStrategy


class DividendYieldCalculationStrategy(BaseKPIStrategy):
    """
    Strategy para calcular Dividend Yield del activo.
    
    El retorno periódico (mensual/trimestral) que recibe un holder de tokens
    basado en las distribuciones de flujo de caja.
    
    Formula:
    Dividend Yield = (Dividendo Pagado / Valor Compra Token) × 100
    
    Donde:
    - Dividendo Pagado: Distribución por token del período
    - Valor Compra Token: Precio inicial de compra del token
    
    Interpretación:
    - Dividend Yield > 8% anualizado: Excelente rendimiento por distribuciones
    - Dividend Yield 5-8%: Buen rendimiento
    - Dividend Yield < 5%: Rendimiento moderado/bajo
    
    Example:
        >>> strategy = DividendYieldCalculationStrategy(asset)
        >>> result = strategy.calculate(period_year=2024, period_month=12)
        >>> print(f"Dividend Yield mensual: {result['dividend_yield_monthly_percentage']:.2f}%")
        >>> print(f"Dividend Yield anualizado: {result['dividend_yield_annualized_percentage']:.2f}%")
    """
    
    def __init__(self, asset: Asset):
        super().__init__(asset)
        self.fcf_strategy = FreeCashFlowCalculationStrategy(asset)
    
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
        period_type: str = 'monthly',
        period_year: Optional[int] = None,
        period_month: Optional[int] = None,
        period_quarter: Optional[int] = None,
        calculate_annualized: bool = True
    ) -> Dict[str, Any]:
        """
        Calcula Dividend Yield del activo.
        
        Args:
            period_type: Tipo de período ('monthly', 'quarterly')
            period_year: Año específico
            period_month: Mes específico
            period_quarter: Trimestre específico
            calculate_annualized: Si calcular yield anualizado
            
        Returns:
            dict: Resultado del Dividend Yield
        """
        
        # 1. Validar prerequisites
        prereq = self.validate_prerequisites()
        if not prereq['is_valid']:
            return {
                'error': 'Asset prerequisites not met',
                'asset_id': self.asset.id if self.asset else None,
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
            # 1. Obtener FCF del período usando FreeCashFlowCalculationStrategy
            fcf_result = self.fcf_strategy.calculate(
                period_type=period_type,
                period_year=period_year,
                period_month=period_month,
                period_quarter=period_quarter,
                include_breakdown=False
            )
            
            if 'error' in fcf_result:
                return {
                    'error': f'Error calculando FCF: {fcf_result["error"]}',
                    'asset_id': self.asset.id
                }
            
            fcf_period = Decimal(str(fcf_result.get('free_cash_flow', 0)))
            fcf_per_token = Decimal(str(fcf_result.get('fcf_per_token', 0)))
            
            # 2. Obtener valor de compra del token (acquisition_value / tokens)
            total_tokens = self.asset.total_tokens_issued
            acquisition_value = self.asset.acquisition_value
            valor_compra_token = acquisition_value / Decimal(str(total_tokens))
            
            # 3. Calcular Dividend Yield del período
            # Dividend Yield = (Dividendo por Token / Valor Compra Token) × 100
            if valor_compra_token > 0:
                dividend_yield_period = (fcf_per_token / valor_compra_token) * 100
            else:
                dividend_yield_period = Decimal('0.00')
            
            # 4. Calcular Dividend Yield anualizado (si se solicita)
            dividend_yield_annualized = None
            periods_per_year = None
            
            if calculate_annualized:
                if period_type == 'monthly':
                    periods_per_year = 12
                elif period_type == 'quarterly':
                    periods_per_year = 4
                else:
                    periods_per_year = 1
                
                dividend_yield_annualized = dividend_yield_period * periods_per_year
            
            # 5. Interpretación
            yield_to_interpret = dividend_yield_annualized if dividend_yield_annualized else dividend_yield_period
            interpretation = self._interpret_dividend_yield(
                float(yield_to_interpret), 
                is_annualized=bool(dividend_yield_annualized)
            )
            
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
                'period_display': fcf_result.get('period_display'),
                
                # Dividend Yield principal
                'dividend_yield_period_percentage': float(dividend_yield_period),
                'dividend_yield_annualized_percentage': float(dividend_yield_annualized) if dividend_yield_annualized else None,
                'dividendo_por_token': float(fcf_per_token),
                'valor_compra_token': float(valor_compra_token),
                
                # Métricas del período
                'period_metrics': {
                    'fcf_period': float(fcf_period),
                    'fcf_per_token': float(fcf_per_token),
                    'total_tokens': total_tokens,
                    'periods_per_year': periods_per_year
                },
                
                # Interpretación
                'interpretation': interpretation,
                'performance_level': self._get_performance_level(float(yield_to_interpret)),
                
                # Información del activo
                'asset_metrics': {
                    'acquisition_value': float(acquisition_value),
                    'valor_compra_token': float(valor_compra_token),
                    'total_tokens_issued': total_tokens
                },
                
                # Metadata
                'calculation_date': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': f'Error: {str(e)}',
                'asset_id': self.asset.id,
                'asset_code': self.asset.asset_code
            }
    
    def _calculate_annualized_yield(self) -> Dict[str, Any]:
        """Calcula Dividend Yield anualizado (últimos 12 meses)"""
        
        try:
            # 1. Obtener FCF de los últimos 12 meses
            fcf_result = self.fcf_strategy.calculate(
                months_back=12,
                include_breakdown=False
            )
            
            if 'error' in fcf_result:
                return {
                    'error': f'Error calculando FCF: {fcf_result["error"]}',
                    'asset_id': self.asset.id
                }
            
            fcf_12m = Decimal(str(fcf_result.get('total_fcf_12m', 0)))
            fcf_per_token = Decimal(str(fcf_result.get('fcf_per_token', 0)))
            
            # 2. Obtener valor de compra del token
            total_tokens = self.asset.total_tokens_issued
            acquisition_value = self.asset.acquisition_value
            valor_compra_token = acquisition_value / Decimal(str(total_tokens))
            
            # 3. Calcular Dividend Yield anualizado
            # Dividend Yield = (Dividendo Anual por Token / Valor Compra Token) × 100
            if valor_compra_token > 0:
                dividend_yield_annualized = (fcf_per_token / valor_compra_token) * 100
            else:
                dividend_yield_annualized = Decimal('0.00')
            
            # 4. Calcular yield mensual promedio
            dividend_yield_monthly_avg = dividend_yield_annualized / 12
            
            # 5. Interpretación
            interpretation = self._interpret_dividend_yield(
                float(dividend_yield_annualized), 
                is_annualized=True
            )
            
            return {
                'asset_id': self.asset.id,
                'asset_code': self.asset.asset_code,
                'asset_name': self.asset.name,
                'fund_id': self.asset.fund.id,
                'fund_name': self.asset.fund.name,
                'period_analyzed': fcf_result.get('period_analyzed'),
                
                # Dividend Yield principal
                'dividend_yield_annualized_percentage': float(dividend_yield_annualized),
                'dividend_yield_monthly_avg_percentage': float(dividend_yield_monthly_avg),
                'dividendo_anual_por_token': float(fcf_per_token),
                'valor_compra_token': float(valor_compra_token),
                
                # Métricas anuales
                'annual_metrics': {
                    'fcf_12m': float(fcf_12m),
                    'fcf_per_token': float(fcf_per_token),
                    'total_tokens': total_tokens,
                    'average_monthly_fcf': float(fcf_12m / 12)
                },
                
                # Interpretación
                'interpretation': interpretation,
                'performance_level': self._get_performance_level(float(dividend_yield_annualized)),
                
                # Información del activo
                'asset_metrics': {
                    'acquisition_value': float(acquisition_value),
                    'valor_compra_token': float(valor_compra_token),
                    'total_tokens_issued': total_tokens
                },
                
                # Metadata
                'calculation_date': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': f'Error: {str(e)}',
                'asset_id': self.asset.id,
                'asset_code': self.asset.asset_code
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
            return f"Excelente rendimiento {period_text}: El activo distribuye un flujo de caja significativo a los holders."
        elif dividend_yield >= 7:
            return f"Muy buen rendimiento {period_text}: Distribuciones sólidas y consistentes."
        elif dividend_yield >= 5:
            return f"Buen rendimiento {period_text}: Distribuciones aceptables, en línea con el mercado."
        elif dividend_yield >= 3:
            return f"Rendimiento moderado {period_text}: Distribuciones modestas."
        elif dividend_yield > 0:
            return f"Rendimiento bajo {period_text}: Distribuciones limitadas. Revisar eficiencia operativa."
        else:
            return f"Sin rendimiento {period_text}: El activo no está generando distribuciones."
    
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