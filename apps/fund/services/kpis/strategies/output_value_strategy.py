"""
Output Value Calculation Strategy for Fund
"""

from typing import Dict, Any, Optional, List
from decimal import Decimal
from django.utils import timezone

from ..core.base_strategy import BaseKPIStrategy
from apps.fund.models.core import Fund
from .noi_strategy import NOICalculationStrategy


class OutputValueCalculationStrategy(BaseKPIStrategy):
    """
    Strategy para calcular Output Value (Valor de Salida) del fondo.
    
    El valor de salida es el precio estimado al que se podrá vender el portafolio
    completo o liquidar el fondo.
    
    Formula:
    Valor de Salida = (NOI Estabilizado / Cap Rate de Salida) × 100
    
    Valor de Adquisición = (NOI / Cap Rate Actual) × 100  # ✅ CALCULADO DINÁMICAMENTE
    
    Donde:
    - NOI Estabilizado = NOI de año base (proyectado con crecimiento variable)
    - Cap Rate de Salida = Tasa de capitalización esperada al momento de venta (REQUERIDO)
    - Cap Rate Actual = Tasa de capitalización actual del fondo (REQUERIDO, digitado)
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
        exit_cap_rate: Decimal,  # ✅ REQUERIDO: Cap rate de salida
        current_cap_rate: Optional[Decimal] = None,  # ✅ NUEVO: Cap rate actual (para calcular acquisition_value)
        projected_noi: Optional[Decimal] = None,
        use_projection: bool = False,
        projection_start_year: Optional[int] = None,
        projection_years: int = 5,
        annual_noi_growth_rate: Optional[Decimal] = None,
        growth_rates_by_year: Optional[Dict[int, Decimal]] = None
    ) -> Dict[str, Any]:
        """
        Calcula el Valor de Salida del fondo.
        
        Args:
            exit_cap_rate: Cap rate de salida esperado (REQUERIDO, digitado por usuario)
            current_cap_rate: Cap rate actual del fondo (OPCIONAL, digitado por usuario)
                             Si se provee, se usa para calcular acquisition_value dinámicamente
            projected_noi: NOI estabilizado manual (opcional)
            use_projection: Si usar proyección con crecimiento (default: False)
            projection_start_year: Año base para empezar proyección (ej: 2024)
            projection_years: Número de años a proyectar (default: 5)
            annual_noi_growth_rate: Tasa de crecimiento uniforme %
            growth_rates_by_year: Dict con tasas de crecimiento específicas por año
            
        Returns:
            dict: Resultado del Output Value con métricas
            
        Modos de Proyección:
        1. Sin proyección: NOI últimos 12 meses (estabilizado)
        2. Proyección uniforme: Crecimiento constante cada año
        3. Proyección variable: Crecimiento específico por año
        """
        
        # 1. Validar prerequisites
        prereq = self.validate_prerequisites()
        if not prereq['is_valid']:
            return {
                'error': 'Fund prerequisites not met',
                **self._get_fund_info()
            }
        
        try:
            # 2. ✅ Validar exit_cap_rate (REQUERIDO)
            exit_cap_rate = Decimal(str(exit_cap_rate))
            
            if exit_cap_rate <= 0:
                return {
                    'error': 'Cap Rate de salida debe ser mayor a cero',
                    **self._get_fund_info(),
                    'exit_cap_rate': float(exit_cap_rate)
                }
            
            if exit_cap_rate > 50:
                return {
                    'error': 'Cap Rate de salida parece excesivamente alto (>50%)',
                    **self._get_fund_info(),
                    'exit_cap_rate': float(exit_cap_rate)
                }
            
            # 3. ✅ Validar current_cap_rate (OPCIONAL)
            if current_cap_rate is not None:
                current_cap_rate = Decimal(str(current_cap_rate))
                
                if current_cap_rate <= 0:
                    return {
                        'error': 'Cap Rate actual debe ser mayor a cero',
                        **self._get_fund_info(),
                        'current_cap_rate': float(current_cap_rate)
                    }
                
                if current_cap_rate > 50:
                    return {
                        'error': 'Cap Rate actual parece excesivamente alto (>50%)',
                        **self._get_fund_info(),
                        'current_cap_rate': float(current_cap_rate)
                    }
            
            # 4. ✅ Validar año de inicio de proyección
            if use_projection and projection_start_year is None:
                projection_start_year = timezone.now().year
            
            # 5. Obtener NOI (estabilizado o proyectado)
            if projected_noi is None:
                if use_projection:
                    noi_calculation = self._calculate_projected_noi(
                        projection_start_year=projection_start_year,
                        projection_years=projection_years,
                        annual_growth_rate=annual_noi_growth_rate,
                        growth_rates_by_year=growth_rates_by_year
                    )
                else:
                    noi_calculation = self._calculate_stabilized_noi()
                
                if 'error' in noi_calculation:
                    return noi_calculation
                
                projected_noi = noi_calculation['projected_noi']
                noi_current = noi_calculation['noi_current']
                growth_rate_used = noi_calculation.get('growth_rate_used')
                calculation_method = noi_calculation.get('method', 'stabilized')
                projection_breakdown = noi_calculation.get('projection_breakdown', [])
            else:
                projected_noi = Decimal(str(projected_noi))
                noi_current = projected_noi
                growth_rate_used = None
                calculation_method = 'manual'
                projection_breakdown = []
            
            # 6. Validar NOI
            if projected_noi <= 0:
                return {
                    'error': 'NOI estabilizado debe ser mayor a cero',
                    **self._get_fund_info(),
                    'projected_noi': float(projected_noi)
                }
            
            # 7. ✅ Calcular Acquisition Value DINÁMICAMENTE (si se provee current_cap_rate)
            acquisition_value = None
            cap_rate_spread = None
            acquisition_value_source = None
            
            if current_cap_rate is not None:
                # Formula: Valor de Adquisición = (NOI / Cap Rate Actual) × 100
                acquisition_value = (noi_current / current_cap_rate) * 100
                acquisition_value_source = 'calculated_from_current_cap_rate'
                cap_rate_spread = exit_cap_rate - current_cap_rate
            
            # 8. Calcular Output Value
            # Formula: Output Value = (NOI Estabilizado / Cap Rate de Salida) × 100
            output_value = (projected_noi / exit_cap_rate) * 100
            
            # 9. Métricas adicionales (solo si hay acquisition_value calculado)
            capital_gain_loss = None
            capital_gain_percentage = None
            moic = None
            
            if acquisition_value is not None and acquisition_value > 0:
                capital_gain_loss = output_value - acquisition_value
                capital_gain_percentage = (capital_gain_loss / acquisition_value) * 100
                moic = output_value / acquisition_value
            
            # Métricas por unidad
            total_units = self.fund.amount_tokens or 0
            output_value_per_unit = (output_value / total_units) if total_units > 0 else None
            
            initial_price_per_unit = self.fund.initial_price_per_unit
            unit_price_appreciation = None
            unit_price_appreciation_pct = None
            
            if output_value_per_unit and initial_price_per_unit and initial_price_per_unit > 0:
                unit_price_appreciation = output_value_per_unit - initial_price_per_unit
                unit_price_appreciation_pct = (unit_price_appreciation / initial_price_per_unit) * 100
            
            # 10. ✅ Descripción del método de proyección
            if use_projection:
                if growth_rates_by_year:
                    projection_description = (
                        f'NOI proyectado desde {projection_start_year} por {projection_years} años '
                        f'con crecimiento variable por año'
                    )
                else:
                    projection_description = (
                        f'NOI proyectado desde {projection_start_year} por {projection_years} años '
                        f'con crecimiento uniforme de {growth_rate_used}%'
                    )
            else:
                projection_description = 'NOI estabilizado (últimos 12 meses sin proyección)'
            
            # 11. Interpretación
            interpretation = self._interpret_output_value(
                float(output_value),
                float(exit_cap_rate),
                float(acquisition_value) if acquisition_value else None
            )
            
            return {
                **self._get_fund_info(),
                
                # Output Value principal
                'output_value': float(output_value),
                'output_value_display': f"${float(output_value):,.2f} COP",
                
                # Componentes del cálculo
                'calculation_components': {
                    'projected_noi': float(projected_noi),
                    'exit_cap_rate': float(exit_cap_rate),
                    'exit_cap_rate_source': 'user_input',
                    'current_cap_rate': float(current_cap_rate) if current_cap_rate else None,
                    'current_cap_rate_source': 'user_input' if current_cap_rate else None,
                    'noi_source': calculation_method,
                    'use_projection': use_projection,
                    'projection_start_year': projection_start_year if use_projection else None,
                    'projection_years': projection_years if use_projection else 0
                },
                
                # Contexto de cálculo
                'calculation_context': {
                    'method': calculation_method,
                    'noi_current_12m': float(noi_current) if noi_current else None,
                    'annual_noi_growth_rate': float(growth_rate_used) if growth_rate_used and not growth_rates_by_year else None,
                    'growth_rates_by_year': {year: float(rate) for year, rate in growth_rates_by_year.items()} if growth_rates_by_year else None,
                    'cap_rate_spread': float(cap_rate_spread) if cap_rate_spread else None,
                    'description': projection_description
                },
                
                # ✅ NUEVO: Desglose año por año de la proyección
                'projection_breakdown': projection_breakdown,
                
                # Métricas de retorno (solo si hay current_cap_rate)
                'return_metrics': {
                    'acquisition_value': float(acquisition_value) if acquisition_value else None,
                    'acquisition_value_source': acquisition_value_source,
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
                
                # Comparación con mercado (escenarios)
                'market_comparison': self._calculate_market_scenarios(projected_noi),
                
                # Interpretación
                'interpretation': interpretation,
                'valuation_assessment': self._assess_valuation(float(exit_cap_rate)),
                
                # Metadata
                'calculation_date': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': f'Error calculando Output Value: {str(e)}',
                **self._get_fund_info()
            }
    
    def _calculate_stabilized_noi(self) -> Dict[str, Any]:
        """
        Calcula NOI Estabilizado (últimos 12 meses SIN proyección).
        
        Este es el NOI anualizado basado en los últimos 12 meses de operación,
        sin aplicar factores de crecimiento.
        
        Returns:
            dict: NOI estabilizado y datos de contexto
        """
        
        # Obtener NOI de últimos 12 meses
        noi_result = self.noi_strategy.calculate(months_back=12, include_breakdown=False)
        
        if 'error' in noi_result:
            return {
                'error': f'Error obteniendo NOI estabilizado: {noi_result["error"]}',
                **self._get_fund_info()
            }
        
        # NOI estabilizado = NOI de últimos 12 meses (ya está anualizado)
        projected_noi = Decimal(str(noi_result.get('total_noi_12m', 0)))
        
        if projected_noi <= 0:
            return {
                'error': 'NOI estabilizado debe ser mayor a cero',
                **self._get_fund_info(),
                'projected_noi': float(projected_noi)
            }
        
        return {
            'projected_noi': projected_noi,
            'noi_current': projected_noi,
            'method': 'stabilized',
            'period_analyzed': noi_result.get('period_analyzed'),
            'months_with_data': noi_result.get('months_with_data', 12)
        }
    
    def _calculate_projected_noi(
        self,
        projection_start_year: int,
        projection_years: int,
        annual_growth_rate: Optional[Decimal],
        growth_rates_by_year: Optional[Dict[int, Decimal]]
    ) -> Dict[str, Any]:
        """
        Calcula NOI Proyectado (con crecimiento variable o uniforme).
        
        Soporta dos modos:
        1. Crecimiento uniforme: Misma tasa cada año
        2. Crecimiento variable: Tasa específica por año
        
        Formula (Uniforme):
        NOI_año_n = NOI_base × (1 + tasa)^n
        
        Formula (Variable):
        NOI_año_n = NOI_base × (1 + tasa_2024) × (1 + tasa_2025) × ... × (1 + tasa_año_n)
        
        Args:
            projection_start_year: Año base de proyección
            projection_years: Número de años a proyectar
            annual_growth_rate: Tasa uniforme (si no hay growth_rates_by_year)
            growth_rates_by_year: Dict con tasas por año específico
            
        Returns:
            dict: NOI proyectado con desglose año por año
        """
        
        # 1. Obtener NOI base (año de inicio)
        noi_result = self.noi_strategy.calculate(months_back=12, include_breakdown=False)
        
        if 'error' in noi_result:
            return {
                'error': f'Error obteniendo NOI base: {noi_result["error"]}',
                **self._get_fund_info()
            }
        
        noi_base = Decimal(str(noi_result.get('total_noi_12m', 0)))
        
        if noi_base <= 0:
            return {
                'error': 'NOI base debe ser mayor a cero para proyección',
                **self._get_fund_info(),
                'noi_base': float(noi_base)
            }
        
        # 2. ✅ Determinar método de proyección
        if growth_rates_by_year:
            # Modo: Crecimiento variable por año
            return self._project_with_variable_growth(
                noi_base=noi_base,
                projection_start_year=projection_start_year,
                projection_years=projection_years,
                growth_rates_by_year=growth_rates_by_year
            )
        else:
            # Modo: Crecimiento uniforme
            return self._project_with_uniform_growth(
                noi_base=noi_base,
                projection_start_year=projection_start_year,
                projection_years=projection_years,
                annual_growth_rate=annual_growth_rate
            )
    
    def _project_with_uniform_growth(
        self,
        noi_base: Decimal,
        projection_start_year: int,
        projection_years: int,
        annual_growth_rate: Optional[Decimal]
    ) -> Dict[str, Any]:
        """
        Proyecta NOI con tasa de crecimiento UNIFORME.
        
        Formula: NOI_año_n = NOI_base × (1 + tasa)^n
        
        Args:
            noi_base: NOI del año base
            projection_start_year: Año inicial
            projection_years: Años a proyectar
            annual_growth_rate: Tasa de crecimiento uniforme %
            
        Returns:
            dict: NOI proyectado con desglose
        """
        
        # Tasa de crecimiento (default: 3%)
        if annual_growth_rate is None:
            if (hasattr(self.fund, 'annual_income_increase_rate') and 
                self.fund.annual_income_increase_rate and 
                self.fund.annual_income_increase_rate > 0):
                annual_growth_rate = self.fund.annual_income_increase_rate
            else:
                annual_growth_rate = Decimal('3.0')
        else:
            annual_growth_rate = Decimal(str(annual_growth_rate))
        
        # Proyección año por año
        projection_breakdown = []
        noi_current = noi_base
        
        for year_offset in range(projection_years + 1):
            year = projection_start_year + year_offset
            
            if year_offset == 0:
                # Año base (sin crecimiento)
                noi_year = noi_base
                growth_applied = Decimal('0.00')
            else:
                # Aplicar crecimiento compuesto
                growth_factor = (1 + (annual_growth_rate / 100)) ** year_offset
                noi_year = noi_base * growth_factor
                growth_applied = annual_growth_rate
            
            projection_breakdown.append({
                'year': year,
                'noi': float(noi_year),
                'growth_rate_applied': float(growth_applied),
                'cumulative_growth_factor': float((noi_year / noi_base) if noi_base > 0 else 1)
            })
            
            noi_current = noi_year
        
        # NOI final proyectado
        growth_factor_total = (1 + (annual_growth_rate / 100)) ** projection_years
        noi_proyectado = noi_base * growth_factor_total
        
        return {
            'projected_noi': noi_proyectado,
            'noi_current': noi_base,
            'growth_rate_used': annual_growth_rate,
            'projection_start_year': projection_start_year,
            'projection_years': projection_years,
            'growth_factor_total': float(growth_factor_total),
            'method': 'projected_uniform',
            'projection_breakdown': projection_breakdown
        }
    
    def _project_with_variable_growth(
        self,
        noi_base: Decimal,
        projection_start_year: int,
        projection_years: int,
        growth_rates_by_year: Dict[int, Decimal]
    ) -> Dict[str, Any]:
        """
        Proyecta NOI con tasas de crecimiento VARIABLES por año.
        
        Formula: NOI_año_n = NOI_base × Π(1 + tasa_año_i) para i desde año_base hasta año_n
        
        Args:
            noi_base: NOI del año base
            projection_start_year: Año inicial
            projection_years: Años a proyectar
            growth_rates_by_year: Dict {año: tasa_crecimiento}
            
        Returns:
            dict: NOI proyectado con desglose
        """
        
        # Convertir todas las tasas a Decimal
        growth_rates = {
            int(year): Decimal(str(rate)) 
            for year, rate in growth_rates_by_year.items()
        }
        
        # Proyección año por año
        projection_breakdown = []
        noi_current = noi_base
        cumulative_factor = Decimal('1.0')
        
        for year_offset in range(projection_years + 1):
            year = projection_start_year + year_offset
            
            if year_offset == 0:
                # Año base (sin crecimiento)
                noi_year = noi_base
                growth_applied = Decimal('0.00')
            else:
                # Obtener tasa de crecimiento para este año específico
                growth_rate = growth_rates.get(year, Decimal('0.00'))
                
                # Aplicar crecimiento acumulativo
                year_factor = 1 + (growth_rate / 100)
                cumulative_factor *= year_factor
                noi_year = noi_base * cumulative_factor
                growth_applied = growth_rate
            
            projection_breakdown.append({
                'year': year,
                'noi': float(noi_year),
                'growth_rate_applied': float(growth_applied),
                'cumulative_growth_factor': float(cumulative_factor)
            })
            
            noi_current = noi_year
        
        # NOI final proyectado (último año)
        noi_proyectado = noi_current
        
        # Calcular tasa de crecimiento promedio ponderada
        avg_growth_rate = (
            (cumulative_factor ** (Decimal('1.0') / projection_years) - 1) * 100
            if projection_years > 0 
            else Decimal('0.00')
        )
        
        return {
            'projected_noi': noi_proyectado,
            'noi_current': noi_base,
            'growth_rate_used': avg_growth_rate,  # Promedio ponderado
            'growth_rates_by_year': {year: float(rate) for year, rate in growth_rates.items()},
            'projection_start_year': projection_start_year,
            'projection_years': projection_years,
            'growth_factor_total': float(cumulative_factor),
            'method': 'projected_variable',
            'projection_breakdown': projection_breakdown
        }

    def _calculate_market_scenarios(self, projected_noi: Decimal) -> Dict[str, Any]:
        """
        Calcula valoración del fondo bajo diferentes escenarios de Cap Rate.
        
        Args:
            projected_noi: NOI proyectado/estabilizado
            
        Returns:
            dict: Escenarios de valoración con diferentes cap rates
        """
        scenarios = {}
        
        # Cap Rates típicos del mercado colombiano
        cap_rate_scenarios = [
            ('conservative_4pct', 4.0),
            ('moderate_low_5pct', 5.0),
            ('moderate_6pct', 6.0),
            ('moderate_high_7pct', 7.0),
            ('aggressive_8pct', 8.0),
            ('high_risk_10pct', 10.0)
        ]
        
        for scenario_name, cap_rate in cap_rate_scenarios:
            output_value = (projected_noi / Decimal(str(cap_rate))) * 100
            scenarios[scenario_name] = {
                'cap_rate': cap_rate,
                'output_value': float(output_value),
                'output_value_display': f"${float(output_value):,.2f} COP"
            }
        
        return scenarios
    
    def _interpret_output_value(
        self,
        output_value: float,
        exit_cap_rate: float,
        acquisition_value: Optional[float]
    ) -> str:
        """
        Interpreta el Output Value calculado.
        
        Args:
            output_value: Valor de salida calculado
            exit_cap_rate: Cap rate de salida usado
            acquisition_value: Valor de adquisición del fondo (calculado dinámicamente)
            
        Returns:
            str: Interpretación textual
        """
        base_interpretation = (
            f"Con un Cap Rate de salida de {exit_cap_rate:.2f}%, el valor estimado del fondo es "
            f"${output_value:,.2f} COP. "
        )
        
        if acquisition_value:
            diff = output_value - acquisition_value
            diff_pct = (diff / acquisition_value) * 100
            
            if diff_pct > 50:
                comparison = (
                    f"Esto representa una **apreciación excepcional de {diff_pct:.1f}%** "
                    f"({diff:+,.2f} COP) sobre el valor de adquisición calculado."
                )
            elif diff_pct > 20:
                comparison = (
                    f"Esto representa una **apreciación significativa de {diff_pct:.1f}%** "
                    f"({diff:+,.2f} COP) sobre el valor de adquisición calculado."
                )
            elif diff_pct > 0:
                comparison = (
                    f"Esto representa una apreciación moderada de {diff_pct:.1f}% "
                    f"({diff:+,.2f} COP) sobre el valor de adquisición calculado."
                )
            elif diff_pct > -10:
                comparison = (
                    f"Esto representa una **leve depreciación de {abs(diff_pct):.1f}%** "
                    f"({diff:+,.2f} COP) sobre el valor de adquisición calculado."
                )
            else:
                comparison = (
                    f"Esto representa una **depreciación significativa de {abs(diff_pct):.1f}%** "
                    f"({diff:+,.2f} COP) sobre el valor de adquisición calculado."
                )
            
            return base_interpretation + comparison
        else:
            return base_interpretation + "No se proporcionó Cap Rate actual para calcular valor de adquisición."
    
    def _assess_valuation(self, exit_cap_rate: float) -> str:
        """
        Evalúa la valoración basada en el cap rate de salida.
        
        Args:
            exit_cap_rate: Cap rate de salida usado
            
        Returns:
            str: Evaluación de la valoración
        """
        if exit_cap_rate <= 4:
            return "premium_valuation"
        elif exit_cap_rate <= 6:
            return "moderate_valuation"
        elif exit_cap_rate <= 8:
            return "value_oriented"
        else:
            return "opportunistic"
    
    def _interpret_moic(self, moic: Decimal) -> str:
        """
        Interpreta el MOIC (Multiple on Invested Capital).
        
        Args:
            moic: MOIC calculado
            
        Returns:
            str: Interpretación del MOIC
        """
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