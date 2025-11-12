"""
Cash on Cash Return Calculation Strategy para Fund
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from django.utils import timezone

from ..core.base_strategy import BaseKPIStrategy
from apps.fund.models.core import Fund
from .free_cash_flow_strategy import FreeCashFlowCalculationStrategy


class CashOnCashCalculationStrategy(BaseKPIStrategy):
    """
    Strategy para calcular Cash on Cash Return de un fondo.
    
    El retorno anual en efectivo sobre el capital inicial invertido (sin deuda).
    
    Formula:
    Cash on Cash = (Flujo de Caja Libre Anual / Capital Invertido) × 100
    
    Donde:
    - Flujo de Caja Libre Anual: FCF de los últimos 12 meses
    - Capital Invertido: Equity inicial (acquisition_value - deuda inicial)
    
    Nota importante:
    - Este es el KPI del FONDO, no de la inversión individual
    - Usa el capital total del fondo (acquisition_value)
    - Si quisieras Cash on Cash de una inversión específica, usarías:
      Cash on Cash Inversión = (Distribuciones recibidas / Monto invertido) × 100
    
    Interpretación:
    - CoC > 8%: Excelente retorno en efectivo
    - CoC 5-8%: Buen retorno
    - CoC < 5%: Retorno bajo, revisar estructura
    
    Example:
        >>> strategy = CashOnCashCalculationStrategy(fund)
        >>> result = strategy.calculate()
        >>> print(f"Cash on Cash: {result['cash_on_cash_percentage']:.2f}%")
    """
    
    def __init__(self, fund: Fund):
        super().__init__(fund)
        self.fcf_strategy = FreeCashFlowCalculationStrategy(fund)
    
    def validate_prerequisites(self) -> Dict[str, bool]:
        """Valida que el fondo tenga los datos necesarios"""
        validations = {
            'fund_exists': self.fund is not None,
            'fund_has_id': bool(self.fund.pk if self.fund else False),
            'fund_is_active': self.fund.status == 'active' if self.fund else False,
            'has_acquisition_value': bool(self.fund.acquisition_value) if self.fund else False
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
        Calcula Cash on Cash Return del fondo.
        
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
                'error': 'Fund prerequisites not met',
                'fund_id': self.fund.id if self.fund else None,
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
                    **self._get_fund_info()
                }
            
            fcf_anual = Decimal(str(fcf_result.get('total_fcf_12m', 0)))
            
            # 3. Obtener capital invertido (equity inicial)
            # Capital invertido = acquisition_value (sin considerar deuda)
            capital_invertido = self.fund.acquisition_value
            
            # Validar que el capital invertido sea válido
            if not capital_invertido or capital_invertido <= 0:
                return {
                    'error': 'Capital invertido inválido o cero',
                    **self._get_fund_info(),
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
            
            result = {
                **self._get_fund_info(),
                
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
                'fcf_components': fcf_result.get('fcf_components', {}),
                
                # Metadata
                'calculation_date': timezone.now().isoformat(),
                'period_analyzed': f'últimos {months_back} meses',
                'calculation_note': 'KPI del fondo basado en capital total (acquisition_value)'
            }
            
            # Agregar información por área si existe
            total_area = getattr(self.fund, 'total_area_m2', None)
            rentable_area = getattr(self.fund, 'rentable_area_m2', None)
            
            if total_area and total_area > 0:
                result['fund_metrics'] = {
                    'total_area_m2': float(total_area),
                    'rentable_area_m2': float(rentable_area) if rentable_area else None,
                    'cash_on_cash_per_m2': float(fcf_anual / total_area)
                }
            
            # Agregar desglose si se solicitó
            if include_breakdown and 'monthly_breakdown' in fcf_result:
                result['monthly_breakdown'] = fcf_result['monthly_breakdown']
            
            return result
            
        except Exception as e:
            return {
                'error': f'Error calculando Cash on Cash: {str(e)}',
                **self._get_fund_info()
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
            return "Excelente retorno en efectivo: El fondo genera flujo de caja significativo sobre el capital invertido."
        elif coc >= 7:
            return "Muy buen retorno: El fondo produce flujo de caja sólido, típico de fondos bien gestionados."
        elif coc >= 5:
            return "Buen retorno: El fondo genera flujo de caja aceptable, en línea con mercado."
        elif coc >= 3:
            return "Retorno moderado: El fondo genera algo de efectivo, pero hay oportunidad de mejora."
        elif coc > 0:
            return "Retorno bajo: El fondo genera poco efectivo relativo al capital invertido. Revisar eficiencia operativa."
        else:
            return "Sin retorno o negativo: El fondo no genera efectivo o requiere inyección de capital."
    
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