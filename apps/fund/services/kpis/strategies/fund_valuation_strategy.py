"""
Fund Valuation Calculation Strategy
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from django.utils import timezone

from apps.fund.services.kpis.core.base_strategy import BaseKPIStrategy
from apps.fund.models.core import Fund
from .noi_strategy import NOICalculationStrategy


class FundValuationCalculationStrategy(BaseKPIStrategy):
    """
    Strategy para calcular el Valor del Fondo basado en NOI y Cap Rate.
    
    Formula:
    Valor del Fondo = (NOI Anual / Cap Rate) × 100
    
    Donde:
    - NOI Anual: Net Operating Income de los últimos 12 meses (o período especificado)
    - Cap Rate: Tasa de capitalización objetivo (proporcionada por el usuario)
    
    Este cálculo es la inversa del Cap Rate y permite determinar:
    - El valor implícito del fondo dado un cap rate de mercado
    - La valoración del fondo bajo diferentes escenarios de cap rate
    - El valor teórico que debería tener el fondo para ser atractivo
    
    Interpretación:
    - Cap Rate alto (10%) → Valor del fondo BAJO → Retorno alto, mayor riesgo
    - Cap Rate bajo (5%) → Valor del fondo ALTO → Retorno bajo, menor riesgo
    
    Example:
        >>> # NOI Anual: $3,500,000 COP
        >>> # Cap Rate Objetivo: 7%
        >>> # Valor del Fondo = (3,500,000 / 7) × 100 = $50,000,000 COP
        >>> 
        >>> strategy = FundValuationCalculationStrategy(fund)
        >>> result = strategy.calculate(target_cap_rate=7.0)
        >>> print(f"Valor del Fondo: ${result['fund_value']:,.2f}")
    """
    
    def __init__(self, fund: Fund):
        super().__init__(fund)
        self.noi_strategy = NOICalculationStrategy(fund)
    
    def validate_prerequisites(self) -> Dict[str, bool]:
        """Valida que el fondo tenga los datos necesarios"""
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
        target_cap_rate: Decimal,
        months_back: int = 12,
        noi_override: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Calcula el Valor del Fondo basado en NOI y Cap Rate objetivo.
        
        Args:
            target_cap_rate: Cap Rate objetivo en porcentaje (ej: 7.0 para 7%)
            months_back: Meses hacia atrás para calcular NOI (default: 12)
            noi_override: NOI manual (opcional, si se omite usa NOI calculado)
            
        Returns:
            dict: {
                'fund_value': float,
                'noi_anual': float,
                'target_cap_rate': float,
                'valuation_scenarios': dict,
                ...
            }
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
            # 2. Validar Cap Rate objetivo
            target_cap_rate_decimal = Decimal(str(target_cap_rate))
            
            if target_cap_rate_decimal <= 0:
                return {
                    'error': 'Cap Rate objetivo debe ser mayor a cero',
                    **self._get_fund_info(),
                    'target_cap_rate': float(target_cap_rate)
                }
            
            if target_cap_rate_decimal > 50:
                return {
                    'error': 'Cap Rate objetivo parece excesivamente alto (>50%)',
                    **self._get_fund_info(),
                    'target_cap_rate': float(target_cap_rate)
                }
            
            # 3. Obtener NOI Anual
            if noi_override is not None:
                # Usar NOI proporcionado manualmente
                noi_anual = Decimal(str(noi_override))
                noi_source = 'manual_override'
                noi_period = 'custom'
            else:
                # Calcular NOI usando NOICalculationStrategy
                noi_result = self.noi_strategy.calculate(
                    months_back=months_back,
                    include_breakdown=False
                )
                
                if 'error' in noi_result:
                    return {
                        'error': f"Error calculando NOI: {noi_result['error']}",
                        **self._get_fund_info()
                    }
                
                noi_anual = Decimal(str(noi_result.get('total_noi_12m', 0)))
                noi_source = 'calculated'
                noi_period = noi_result.get('period_analyzed', f'últimos {months_back} meses')
            
            # Validar NOI
            if noi_anual <= 0:
                return {
                    'error': 'NOI debe ser mayor a cero para calcular valoración',
                    **self._get_fund_info(),
                    'noi_anual': float(noi_anual),
                    'noi_source': noi_source
                }
                
            # 4. Calcular Valor del Fondo
            # ✅ SOLO depende de NOI y Cap Rate
            fund_value = (noi_anual / target_cap_rate_decimal) * 100
            
            # 5. ❌ ELIMINAR: No comparar con acquisition_value
            # (acquisition_value es irrelevante para valoración de mercado)
            
            # 6. Escenarios de valoración con diferentes cap rates
            valuation_scenarios = self._calculate_valuation_scenarios(noi_anual)
            
            # 7. Métricas por unidad
            total_units = self.fund.amount_tokens or 0
            value_per_unit = None
            
            if total_units > 0:
                value_per_unit = fund_value / Decimal(str(total_units))
            
            # 8. Métricas por área
            total_area = getattr(self.fund, 'total_area_m2', None)
            value_per_sqm = None
            
            if total_area and total_area > 0:
                value_per_sqm = fund_value / total_area
            
            return {
                **self._get_fund_info(),
                
                # Valoración principal
                'fund_value': float(fund_value),
                'fund_value_display': f"${float(fund_value):,.2f} COP",
                
                # Componentes del cálculo
                'calculation_components': {
                    'noi_anual': float(noi_anual),
                    'target_cap_rate': float(target_cap_rate_decimal),
                    'noi_source': noi_source,
                    'noi_period': noi_period
                },
                
                # ✅ NUEVO: Comparar con precio actual por unidad (más relevante)
                'market_comparison': {
                    'current_price_per_unit': float(self.fund.price_per_unit) if self.fund.price_per_unit else None,
                    'implied_value_per_unit': float(value_per_unit) if value_per_unit else None,
                    'unit_price_difference_pct': float(
                        ((value_per_unit - self.fund.price_per_unit) / self.fund.price_per_unit) * 100
                    ) if value_per_unit and self.fund.price_per_unit else None
                } if total_units > 0 and self.fund.price_per_unit else None,
                
                # Escenarios de valoración
                'valuation_scenarios': valuation_scenarios,
                
                # Métricas por unidad
                'per_unit_metrics': {
                    'total_units_issued': total_units,
                    'value_per_unit': float(value_per_unit) if value_per_unit else None
                } if total_units > 0 else None,
                
                # Métricas por área
                'per_area_metrics': {
                    'total_area_m2': float(total_area) if total_area else None,
                    'value_per_sqm': float(value_per_sqm) if value_per_sqm else None
                } if total_area else None,
                
                # Interpretación
                'interpretation': self._interpret_valuation(
                    float(fund_value),
                    float(target_cap_rate_decimal),
                    float(value_per_unit) if value_per_unit else None
                ),
                'valuation_level': self._get_valuation_level(float(target_cap_rate_decimal)),
                
                # Metadata
                'calculation_date': timezone.now().isoformat(),
                'calculation_method': 'noi_cap_rate_valuation'
            }
            
        except Exception as e:
            return {
                'error': f'Error calculando valoración del fondo: {str(e)}',
                **self._get_fund_info()
            }
    
    def _calculate_valuation_scenarios(self, noi_anual: Decimal) -> Dict[str, Any]:
        """
        Calcula valoración del fondo bajo diferentes escenarios de Cap Rate.
        
        Args:
            noi_anual: NOI anual del fondo
            
        Returns:
            dict: Escenarios de valoración con diferentes cap rates
        """
        scenarios = {}
        
        # Cap Rates típicos del mercado colombiano
        cap_rate_scenarios = [
            ('conservative', 4.0),      # Fondo muy conservador (prime)
            ('moderate_low', 5.0),      # Fondo moderado-bajo
            ('moderate', 6.0),          # Fondo moderado
            ('moderate_high', 7.0),     # Fondo moderado-alto
            ('aggressive', 8.0),        # Fondo agresivo
            ('high_risk', 10.0),        # Alto riesgo
            ('very_high_risk', 12.0)    # Muy alto riesgo
        ]
        
        for scenario_name, cap_rate in cap_rate_scenarios:
            fund_value = (noi_anual / Decimal(str(cap_rate))) * 100
            scenarios[scenario_name] = {
                'cap_rate': cap_rate,
                'fund_value': float(fund_value),
                'fund_value_display': f"${float(fund_value):,.2f} COP"
            }
        
        return scenarios
    
    def _assess_valuation(self, difference_pct: float) -> str:
        """
        Evalúa la valoración implícita vs valor actual.
        
        Args:
            difference_pct: Diferencia porcentual entre valor implícito y actual
            
        Returns:
            str: Evaluación de la valoración
        """
        if difference_pct > 30:
            return "significantly_undervalued"
        elif difference_pct > 15:
            return "undervalued"
        elif difference_pct > 5:
            return "slightly_undervalued"
        elif difference_pct > -5:
            return "fairly_valued"
        elif difference_pct > -15:
            return "slightly_overvalued"
        elif difference_pct > -30:
            return "overvalued"
        else:
            return "significantly_overvalued"
    
    def _interpret_valuation(
        self,
        fund_value: float,
        target_cap_rate: float,
        current_value: Optional[float]
    ) -> str:
        """
        Interpreta la valoración del fondo.
        
        Args:
            fund_value: Valor implícito calculado
            target_cap_rate: Cap rate objetivo usado
            current_value: Valor actual del fondo (opcional)
            
        Returns:
            str: Interpretación textual
        """
        base_interpretation = (
            f"Con un Cap Rate de {target_cap_rate:.2f}%, el valor implícito del fondo es "
            f"${fund_value:,.2f} COP basado en el NOI actual. "
        )
        
        if current_value:
            diff_pct = ((fund_value - current_value) / current_value) * 100
            
            if diff_pct > 15:
                comparison = (
                    f"El valor actual del fondo (${current_value:,.2f} COP) está {abs(diff_pct):.1f}% "
                    f"por DEBAJO del valor implícito, sugiriendo que el fondo podría estar subvaluado "
                    f"o que el mercado espera un cap rate mayor."
                )
            elif diff_pct < -15:
                comparison = (
                    f"El valor actual del fondo (${current_value:,.2f} COP) está {abs(diff_pct):.1f}% "
                    f"por ENCIMA del valor implícito, sugiriendo que el fondo podría estar sobrevaluado "
                    f"o que el mercado espera un cap rate menor (mejor desempeño)."
                )
            else:
                comparison = (
                    f"El valor actual del fondo (${current_value:,.2f} COP) está en línea con el "
                    f"valor implícito (diferencia: {diff_pct:+.1f}%)."
                )
            
            return base_interpretation + comparison
        else:
            return base_interpretation + "No hay valor de adquisición para comparar."
    
    def _get_valuation_level(self, cap_rate: float) -> str:
        """
        Determina el nivel de valoración basado en el cap rate.
        
        Args:
            cap_rate: Cap rate objetivo
            
        Returns:
            str: Nivel de valoración
        """
        if cap_rate <= 4:
            return "premium"
        elif cap_rate <= 6:
            return "moderate"
        elif cap_rate <= 8:
            return "value"
        else:
            return "opportunistic"