"""
Cash on Cash Return Calculation Strategy
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from django.utils import timezone

from ..core.base_strategy import BaseKPIStrategy
from apps.asset.models.core import Asset
from .free_cash_flow_strategy import FreeCashFlowCalculationStrategy


class CashOnCashCalculationStrategy(BaseKPIStrategy):
    """
    Strategy para calcular Cash on Cash Return del activo.
    
    El retorno anual en efectivo sobre el capital inicial invertido (sin deuda).
    
    Formula:
    Cash on Cash = (Flujo de Caja Libre Anual / Capital Invertido) × 100
    
    Donde:
    - Flujo de Caja Libre Anual: FCF de los últimos 12 meses
    - Capital Invertido: Equity inicial (acquisition_value - deuda inicial)
    
    Nota importante:
    - Este es el KPI del ACTIVO, no de la inversión individual
    - Usa el capital total del activo (acquisition_value)
    - Si quisieras Cash on Cash de una inversión específica, usarías:
      Cash on Cash Inversión = (Distribuciones recibidas / Monto invertido) × 100
    
    Interpretación:
    - CoC > 8%: Excelente retorno en efectivo
    - CoC 5-8%: Buen retorno
    - CoC < 5%: Retorno bajo, revisar estructura
    
    Example:
        >>> strategy = CashOnCashCalculationStrategy(asset)
        >>> result = strategy.calculate()
        >>> print(f"Cash on Cash: {result['cash_on_cash_percentage']:.2f}%")
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
            'has_acquisition_value': bool(self.asset.acquisition_value) if self.asset else False
        }
        
        return {
            'is_valid': all(validations.values()),
            'validations': validations
        }
    
    def calculate(
        self,
        months_back: int = 12,
        include_breakdown: bool = False
    ) -> Dict[str, Any]:
        """
        Calcula Cash on Cash Return del activo.
        
        Args:
            months_back: Meses hacia atrás para FCF (default: 12)
            include_breakdown: Incluir desglose mensual del FCF
            
        Returns:
            dict: Resultado del Cash on Cash con componentes
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
            # 2. Obtener FCF anual usando FreeCashFlowCalculationStrategy
            fcf_result = self.fcf_strategy.calculate(
                months_back=months_back,
                include_breakdown=include_breakdown
            )
            
            # Validar que el FCF se calculó correctamente
            if 'error' in fcf_result:
                return {
                    'error': f"Error calculando FCF: {fcf_result['error']}",
                    'asset_id': self.asset.id,
                    'asset_code': self.asset.asset_code
                }
            
            fcf_anual = Decimal(str(fcf_result.get('total_fcf_12m', 0)))
            
            # 3. Obtener capital invertido (equity inicial)
            # Capital invertido = acquisition_value (sin considerar deuda)
            capital_invertido = self.asset.acquisition_value
            
            # Validar que el capital invertido sea válido
            if not capital_invertido or capital_invertido <= 0:
                return {
                    'error': 'Capital invertido inválido o cero',
                    'asset_id': self.asset.id,
                    'asset_code': self.asset.asset_code,
                    'acquisition_value': float(capital_invertido) if capital_invertido else 0
                }
            
            # 4. Calcular Cash on Cash
            # Cash on Cash = (FCF Anual / Capital Invertido) × 100
            cash_on_cash = (fcf_anual / capital_invertido) * 100
            
            # 5. Interpretación del Cash on Cash
            interpretation = self._interpret_cash_on_cash(float(cash_on_cash))
            
            # 6. Métricas adicionales
            # FCF yield (similar a dividend yield pero usando FCF)
            fcf_yield = cash_on_cash  # Es lo mismo en este contexto
            
            # Payback period simple (años para recuperar inversión)
            payback_period = (capital_invertido / fcf_anual) if fcf_anual > 0 else None
            
            return {
                'asset_id': self.asset.id,
                'asset_code': self.asset.asset_code,
                'asset_name': self.asset.name,
                'fund_id': self.asset.fund.id,
                'fund_name': self.asset.fund.name,
                
                # Cash on Cash principal
                'cash_on_cash_percentage': float(cash_on_cash),
                'fcf_anual': float(fcf_anual),
                'capital_invertido': float(capital_invertido),
                
                # Interpretación
                'interpretation': interpretation,
                'performance_level': self._get_performance_level(float(cash_on_cash)),
                
                # Métricas adicionales
                'additional_metrics': {
                    'fcf_yield_percentage': float(fcf_yield),
                    'payback_period_years': float(payback_period) if payback_period else None,
                    'monthly_fcf_average': float(fcf_anual / 12),
                    'annual_cash_return': float(fcf_anual)
                },
                
                # Componentes del FCF (para contexto)
                'fcf_components': fcf_result.get('fcf_components_12m', {}),
                
                # Información del activo
                'asset_metrics': {
                    'total_area_m2': float(self.asset.total_area_m2),
                    'rentable_area_m2': float(self.asset.rentable_area_m2) if self.asset.rentable_area_m2 else None,
                    'cash_on_cash_per_m2': float(fcf_anual / self.asset.total_area_m2) if self.asset.total_area_m2 > 0 else None
                },
                
                # Metadata
                'calculation_date': timezone.now().isoformat(),
                'period_analyzed': f'últimos {months_back} meses',
                'calculation_note': 'KPI del activo basado en capital total (acquisition_value)'
            }
            
            # Agregar desglose si se solicitó
            if include_breakdown and 'monthly_breakdown' in fcf_result:
                result['monthly_breakdown'] = fcf_result['monthly_breakdown']
            
            return result
            
        except Exception as e:
            return {
                'error': f'Error calculando Cash on Cash: {str(e)}',
                'asset_id': self.asset.id,
                'asset_code': self.asset.asset_code
            }
    
    def _interpret_cash_on_cash(self, coc: float) -> str:
        """
        Interpreta el Cash on Cash según rangos estándar.
        
        Args:
            coc: Valor del Cash on Cash en porcentaje
            
        Returns:
            str: Interpretación textual
        """
        if coc >= 10:
            return "Excelente retorno en efectivo: El activo genera flujo de caja significativo sobre el capital invertido."
        elif coc >= 7:
            return "Muy buen retorno: El activo produce flujo de caja sólido, típico de propiedades bien gestionadas."
        elif coc >= 5:
            return "Buen retorno: El activo genera flujo de caja aceptable, en línea con mercado."
        elif coc >= 3:
            return "Retorno moderado: El activo genera algo de efectivo, pero hay oportunidad de mejora."
        elif coc > 0:
            return "Retorno bajo: El activo genera poco efectivo relativo al capital invertido. Revisar eficiencia operativa."
        else:
            return "Sin retorno o negativo: El activo no genera efectivo o requiere inyección de capital."
    
    def _get_performance_level(self, coc: float) -> str:
        """
        Determina el nivel de desempeño basado en Cash on Cash.
        
        Args:
            coc: Valor del Cash on Cash en porcentaje
            
        Returns:
            str: 'excellent', 'very_good', 'good', 'moderate', 'poor', 'negative'
        """
        if coc >= 10:
            return "excellent"
        elif coc >= 7:
            return "very_good"
        elif coc >= 5:
            return "good"
        elif coc >= 3:
            return "moderate"
        elif coc > 0:
            return "poor"
        else:
            return "negative"