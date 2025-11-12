"""
Output Value Calculation Strategy for Fund
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from django.utils import timezone

from ..core.base_strategy import BaseKPIStrategy
from apps.fund.models.core import Fund
from .noi_strategy import NOICalculationStrategy


class OutputValueCalculationStrategy(BaseKPIStrategy):
    """
    Strategy para calcular Output Value (Valor de Salida) del fondo.
    
    El valor de salida es el precio estimado al que se podrá vender el portafolio
    completo o liquidar el fondo en el futuro.
    
    Formula:
    Valor de Salida = NOI Proyectado / Cap Rate de Salida
    """
    
    def __init__(self, fund: Fund):
        super().__init__(fund)
        self.noi_strategy = NOICalculationStrategy(fund)
    
    def validate_prerequisites(self) -> Dict[str, bool]:
        """Valida que el fund tenga los datos necesarios"""
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
        projected_noi: Optional[Decimal] = None,
        exit_cap_rate: Optional[Decimal] = None,
        projection_years: int = 5,
        annual_noi_growth_rate: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Calcula el Valor de Salida del fondo"""
        
        # 1. Validar prerequisites
        prereq = self.validate_prerequisites()
        if not prereq['is_valid']:
            return {
                'error': 'Fund prerequisites not met',
                **self._get_fund_info()
            }
        
        try:
            # 2. Obtener NOI proyectado
            if projected_noi is None:
                noi_calculation = self._calculate_projected_noi(
                    projection_years=projection_years,
                    annual_growth_rate=annual_noi_growth_rate
                )
                
                if 'error' in noi_calculation:
                    return noi_calculation
                
                projected_noi = noi_calculation['projected_noi']
                noi_current = noi_calculation['noi_current']
                growth_rate_used = noi_calculation['growth_rate_used']
            else:
                projected_noi = Decimal(str(projected_noi))
                noi_current = None
                growth_rate_used = None
            
            # 3. Validar projected_noi
            if projected_noi <= 0:
                return {
                    'error': 'NOI proyectado debe ser mayor a cero',
                    **self._get_fund_info(),
                    'projected_noi': float(projected_noi)
                }
            
            # 4. Obtener Cap Rate de salida
            if exit_cap_rate is None:
                cap_rate_calculation = self._estimate_exit_cap_rate()
                
                if 'error' in cap_rate_calculation:
                    return cap_rate_calculation
                
                exit_cap_rate = cap_rate_calculation['exit_cap_rate']
                current_cap_rate = cap_rate_calculation['current_cap_rate']
                cap_rate_spread = cap_rate_calculation['spread']
            else:
                exit_cap_rate = Decimal(str(exit_cap_rate))
                current_cap_rate = None
                cap_rate_spread = None
            
            # 5. Validar exit_cap_rate
            if exit_cap_rate <= 0:
                return {
                    'error': 'Cap Rate de salida debe ser mayor a cero',
                    **self._get_fund_info(),
                    'exit_cap_rate': float(exit_cap_rate)
                }
            
            # 6. Calcular Output Value
            output_value = (projected_noi / exit_cap_rate) * 100
            
            # 7. Métricas adicionales
            acquisition_value = self.fund.acquisition_value or Decimal('0')
            
            capital_gain_loss = output_value - acquisition_value if acquisition_value > 0 else None
            capital_gain_percentage = (
                (capital_gain_loss / acquisition_value * 100) if acquisition_value > 0 else None
            )
            
            moic = (output_value / acquisition_value) if acquisition_value > 0 else None
            
            # Métricas por unidad
            total_units = self.fund.amount_tokens or 0
            output_value_per_unit = (output_value / total_units) if total_units > 0 else None
            
            initial_price_per_unit = self.fund.initial_price_per_unit
            unit_price_appreciation = None
            unit_price_appreciation_pct = None
            
            if output_value_per_unit and initial_price_per_unit and initial_price_per_unit > 0:
                unit_price_appreciation = output_value_per_unit - initial_price_per_unit
                unit_price_appreciation_pct = (unit_price_appreciation / initial_price_per_unit) * 100
            
            return {
                **self._get_fund_info(),
                
                # Output Value principal
                'output_value': float(output_value),
                'projected_noi': float(projected_noi),
                'exit_cap_rate': float(exit_cap_rate),
                
                # Contexto de proyección
                'projection_context': {
                    'projection_years': projection_years,
                    'noi_current': float(noi_current) if noi_current else None,
                    'annual_noi_growth_rate': float(growth_rate_used) if growth_rate_used else None,
                    'current_cap_rate': float(current_cap_rate) if current_cap_rate else None,
                    'cap_rate_spread': float(cap_rate_spread) if cap_rate_spread else None
                },
                
                # Métricas de retorno
                'return_metrics': {
                    'acquisition_value': float(acquisition_value),
                    'capital_gain_loss': float(capital_gain_loss) if capital_gain_loss else None,
                    'capital_gain_percentage': float(capital_gain_percentage) if capital_gain_percentage else None,
                    'moic': float(moic) if moic else None,
                    'interpretation': self._interpret_moic(moic) if moic else None
                },
                
                # Métricas por unidad
                'per_unit_metrics': {
                    'total_units_issued': total_units,
                    'output_value_per_unit': float(output_value_per_unit) if output_value_per_unit else None,
                    'initial_price_per_unit': float(initial_price_per_unit) if initial_price_per_unit else None,
                    'unit_price_appreciation': float(unit_price_appreciation) if unit_price_appreciation else None,
                    'unit_price_appreciation_pct': float(unit_price_appreciation_pct) if unit_price_appreciation_pct else None
                },
                
                # Métricas del portafolio
                'portfolio_metrics': {
                    'total_area_m2': float(self.fund.total_area_m2) if self.fund.total_area_m2 else None,
                    'output_value_per_m2': float(output_value / self.fund.total_area_m2) if self.fund.total_area_m2 and self.fund.total_area_m2 > 0 else None
                },
                
                # Comparación con mercado
                'market_comparison': self._get_market_comparison(output_value, exit_cap_rate),
                
                # Metadata
                'calculation_date': timezone.now().isoformat(),
                'calculation_method': 'projected_noi' if noi_current else 'provided_noi'
            }
            
        except Exception as e:
            return {
                'error': f'Error calculando Output Value: {str(e)}',
                **self._get_fund_info()
            }
    
    def _calculate_projected_noi(
        self,
        projection_years: int,
        annual_growth_rate: Optional[Decimal]
    ) -> Dict[str, Any]:
        """Calcula el NOI proyectado"""
        
        # Obtener NOI actual (últimos 12 meses)
        noi_result = self.noi_strategy.calculate(months_back=12, include_breakdown=False)
        
        if 'error' in noi_result:
            return {
                'error': f'Error obteniendo NOI actual: {noi_result["error"]}',
                **self._get_fund_info()
            }
        
        # ✅ USAR EL CAMPO QUE DEVUELVE NOI STRATEGY
        noi_current = Decimal(str(noi_result.get('total_noi_12m', 0)))
        
        if noi_current <= 0:
            return {
                'error': 'NOI actual debe ser mayor a cero para proyección',
                **self._get_fund_info(),
                'noi_current': float(noi_current)
            }
        
        # Tasa de crecimiento
        if annual_growth_rate is None:
            if hasattr(self.fund, 'annual_income_increase_rate') and self.fund.annual_income_increase_rate and self.fund.annual_income_increase_rate > 0:
                annual_growth_rate = self.fund.annual_income_increase_rate
            else:
                annual_growth_rate = Decimal('3.0')
        else:
            annual_growth_rate = Decimal(str(annual_growth_rate))
        
        # Calcular NOI proyectado
        growth_factor = (1 + (annual_growth_rate / 100)) ** projection_years
        projected_noi = noi_current * Decimal(str(growth_factor))
        
        return {
            'projected_noi': projected_noi,
            'noi_current': noi_current,
            'growth_rate_used': annual_growth_rate,
            'projection_years': projection_years,
            'growth_factor': float(growth_factor)
        }

    def _estimate_exit_cap_rate(self) -> Dict[str, Any]:
        """Estima el Cap Rate de salida"""
        
        noi_result = self.noi_strategy.calculate(months_back=12, include_breakdown=False)
        
        if 'error' in noi_result:
            return {
                'error': f'Error obteniendo NOI para cap rate: {noi_result["error"]}',
                **self._get_fund_info()
            }
        
        # ✅ USAR EL CAMPO QUE DEVUELVE NOI STRATEGY
        noi_current = Decimal(str(noi_result.get('total_noi_12m', 0)))
        acquisition_value = self.fund.acquisition_value
        
        if not acquisition_value or acquisition_value <= 0:
            return {
                'error': 'Valor de adquisición no disponible',
                **self._get_fund_info()
            }
        
        if noi_current <= 0:
            return {
                'error': 'NOI actual es cero, no se puede calcular cap rate',
                **self._get_fund_info()
            }
        
        # Calcular cap rate actual
        current_cap_rate = (noi_current / acquisition_value) * 100
        
        # Spread de salida
        spread = Decimal('0.5')
        exit_cap_rate = current_cap_rate + spread
        
        return {
            'exit_cap_rate': exit_cap_rate,
            'current_cap_rate': current_cap_rate,
            'spread': spread
        }

    def _get_market_comparison(self, output_value: Decimal, exit_cap_rate: Decimal) -> Dict[str, Any]:
        """Compara el valor de salida con mercado"""
        market_scenarios = {}
        
        if hasattr(self.fund, 'market_cap_rate') and self.fund.market_cap_rate and self.fund.market_cap_rate > 0:
            noi_result = self.noi_strategy.calculate(months_back=12, include_breakdown=False)
            if 'error' not in noi_result:
                # ✅ USAR EL CAMPO QUE DEVUELVE NOI STRATEGY
                noi_current = Decimal(str(noi_result.get('total_noi_12m', 0)))
                
                if noi_current > 0:
                    market_implied_value = (noi_current / self.fund.market_cap_rate) * 100
                    market_scenarios['market_cap_rate'] = {
                        'cap_rate': float(self.fund.market_cap_rate),
                        'implied_value': float(market_implied_value),
                        'vs_output_value': float(output_value - market_implied_value),
                        'vs_output_value_pct': float((output_value - market_implied_value) / market_implied_value * 100) if market_implied_value > 0 else None
                    }
        
        return market_scenarios
    
    def _interpret_moic(self, moic: Decimal) -> str:
        """Interpreta el MOIC"""
        if moic >= 2.5:
            return "Excelente retorno: 2.5x o más sobre la inversión inicial"
        elif moic >= 2.0:
            return "Muy buen retorno: Duplica la inversión inicial"
        elif moic >= 1.5:
            return "Buen retorno: 50% o más sobre la inversión"
        elif moic >= 1.2:
            return "Retorno moderado: 20% o más sobre la inversión"
        elif moic >= 1.0:
            return "Retorno positivo: Recupera la inversión con ganancia"
        else:
            return "Pérdida de capital: No recupera la inversión inicial"