"""
Cap Rate Calculation Strategy para Fund
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from django.utils import timezone

from apps.fund.services.kpis.core.base_strategy import BaseKPIStrategy
from apps.fund.models.core import Fund
from .noi_strategy import NOICalculationStrategy


class CapRateCalculationStrategy(BaseKPIStrategy):
    """
    Strategy para calcular Cap Rate (Capitalization Rate) de un fondo.
    
    Cap Rate = (NOI Anual / Valor del Fondo) × 100
    
    Interpretación:
    - Cap Rate alto (8-12%): Mayor retorno potencial, mayor riesgo
    - Cap Rate moderado (5-8%): Retorno balanceado, típico de fondos establecidos
    - Cap Rate bajo (3-5%): Menor retorno, fondo más conservador
    
    Inputs:
    - NOI anual (agregado de los últimos 12 meses)
    - Valor del fondo (acquisition_value o NAV)
    
    Formula:
    Cap Rate = (NOI Anual / Valor del Fondo) × 100
    """
    
    def __init__(self, fund: Fund):
        super().__init__(fund)
        self.noi_strategy = NOICalculationStrategy(fund)
    
    def validate_prerequisites(self) -> Dict[str, bool]:
        """Valida que el fondo tenga los datos necesarios"""
        validations = {
            'fund_exists': self.fund is not None,
            'fund_has_id': bool(self.fund.pk if self.fund else False),
            'fund_is_active': self.fund.status == 'active' if self.fund else False,
            'has_acquisition_value': bool(
                getattr(self.fund, 'acquisition_value', None)
            ) if self.fund else False
        }
        
        return {
            'is_valid': all(validations.values()),
            'validations': validations
        }
    
    def calculate(
        self,
        months_back: int = 12,
        use_acquisition_value: bool = True,
        custom_fund_value: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Calcula Cap Rate del fondo usando NOI agregado.
        
        Args:
            months_back: Meses hacia atrás para calcular NOI (default: 12)
            use_acquisition_value: Si usar acquisition_value o NAV actual
            custom_fund_value: Valor personalizado del fondo (opcional)
        
        Returns:
            dict: {
                'cap_rate': float,
                'noi_anual': float,
                'fund_value': float,
                'interpretation': str,
                'risk_level': str,
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
            # 2. Obtener NOI anual usando NOICalculationStrategy
            noi_result = self.noi_strategy.calculate(
                months_back=months_back,
                include_breakdown=False
            )
            
            # Validar que el NOI se calculó correctamente
            if 'error' in noi_result:
                return {
                    'error': f"Error calculando NOI: {noi_result['error']}",
                    **self._get_fund_info()
                }
            
            # Obtener NOI anual
            noi_anual = Decimal(str(noi_result.get('total_noi_12m', 0)))
            
            # 3. Determinar valor del fondo
            if custom_fund_value:
                fund_value = custom_fund_value
                value_source = 'custom'
            elif use_acquisition_value:
                fund_value = self.fund.acquisition_value
                value_source = 'acquisition_value'
            else:
                # Usar NAV (Net Asset Value) si está disponible
                fund_value = getattr(self.fund, 'total_assets', None) or self.fund.acquisition_value
                value_source = 'nav'
            
            # Validar que el valor del fondo sea válido
            if not fund_value or fund_value <= 0:
                return {
                    'error': 'Valor del fondo inválido o cero',
                    **self._get_fund_info(),
                    'fund_value': float(fund_value) if fund_value else 0,
                    'value_source': value_source
                }
            
            # 4. Calcular Cap Rate
            # Cap Rate = (NOI Anual / Valor del Fondo) × 100
            cap_rate = (noi_anual / fund_value) * 100
            
            # 5. Interpretación del Cap Rate
            interpretation = self._interpret_cap_rate(float(cap_rate))
            
            # 6. Calcular métricas adicionales
            
            # Cap Rate comparado con mercado (si existe market_cap_rate)
            market_cap_rate = getattr(self.fund, 'market_cap_rate', None)
            spread_to_market = None
            if market_cap_rate:
                spread_to_market = float(cap_rate) - float(market_cap_rate)
            
            # Valor implícito del fondo si se tuviera un cap rate objetivo
            # Valor = NOI / (Cap Rate Objetivo / 100)
            target_cap_rates = [5.0, 7.0, 10.0]
            implied_values = {
                f'at_{rate}pct': float(noi_anual / (Decimal(str(rate)) / 100))
                for rate in target_cap_rates
            }
            
            # Métricas por unidad
            total_units = getattr(self.fund, 'amount_tokens', 0)
            cap_rate_per_unit = float(noi_anual / Decimal(str(total_units))) if total_units > 0 else None
            
            # Métricas por área (si existe)
            total_area = getattr(self.fund, 'total_area_m2', None)
            noi_per_sqm = None
            fund_value_per_sqm = None
            if total_area and total_area > 0:
                noi_per_sqm = float(noi_anual / total_area)
                fund_value_per_sqm = float(fund_value / total_area)
            
            return {
                **self._get_fund_info(),
                
                # Cap Rate principal
                'cap_rate': float(cap_rate),
                'cap_rate_display': f"{float(cap_rate):.2f}%",
                
                # Componentes del cálculo
                'calculation_components': {
                    'noi_anual': float(noi_anual),
                    'fund_value': float(fund_value),
                    'value_source': value_source,
                    'months_analyzed': months_back
                },
                
                # Interpretación y análisis
                'analysis': {
                    'interpretation': interpretation,
                    'risk_level': self._get_risk_level(float(cap_rate)),
                    'performance_rating': self._get_performance_rating(float(cap_rate))
                },
                
                # Métricas del NOI
                'noi_metrics': {
                    'noi_margin_percentage': noi_result.get('noi_margin_percentage', 0),
                    'total_operating_income': noi_result.get('components', {}).get('total_operating_income', 0),
                    'total_operating_expense': noi_result.get('components', {}).get('total_operating_expense', 0)
                },
                
                # Análisis de valoración
                'valuation_analysis': {
                    'implied_fund_values': implied_values,
                    'current_valuation_vs_5pct': self._get_valuation_assessment(
                        float(fund_value),
                        implied_values['at_5.0pct']
                    ),
                    'current_valuation_vs_7pct': self._get_valuation_assessment(
                        float(fund_value),
                        implied_values['at_7.0pct']
                    )
                },
                
                # Métricas por unidad
                'per_unit_metrics': {
                    'total_units_issued': total_units,
                    'noi_per_unit': cap_rate_per_unit,
                    'fund_value_per_unit': float(fund_value / Decimal(str(total_units))) if total_units > 0 else None
                },
                
                # Métricas por área
                'per_area_metrics': {
                    'total_area_m2': float(total_area) if total_area else None,
                    'noi_per_sqm': noi_per_sqm,
                    'fund_value_per_sqm': fund_value_per_sqm
                } if total_area else None,
                
                # Metadata
                'calculation_date': timezone.now().isoformat(),
                'noi_period': f'últimos {months_back} meses'
            }
            
        except Exception as e:
            return {
                'error': f'Error calculando Cap Rate: {str(e)}',
                **self._get_fund_info()
            }
    
    def _interpret_cap_rate(self, cap_rate: float) -> str:
        """
        Interpreta el Cap Rate según rangos estándar para fondos.
        
        Args:
            cap_rate: Valor del Cap Rate en porcentaje
            
        Returns:
            str: Interpretación textual
        """
        if cap_rate >= 10:
            return (
                f"Cap Rate alto ({cap_rate:.2f}%): El fondo genera un retorno significativo "
                "sobre su valor, típico de fondos con activos en desarrollo o mercados emergentes. "
                "Mayor retorno potencial con mayor riesgo."
            )
        elif cap_rate >= 7:
            return (
                f"Cap Rate moderado-alto ({cap_rate:.2f}%): Retorno atractivo con riesgo controlado. "
                "Típico de fondos inmobiliarios bien establecidos con activos estabilizados."
            )
        elif cap_rate >= 5:
            return (
                f"Cap Rate moderado ({cap_rate:.2f}%): Retorno balanceado para un fondo estable. "
                "Común en fondos de activos core en mercados maduros."
            )
        elif cap_rate >= 3:
            return (
                f"Cap Rate bajo ({cap_rate:.2f}%): El fondo genera retornos conservadores. "
                "Típico de fondos con activos premium en ubicaciones prime o fondos muy diversificados."
            )
        else:
            return (
                f"Cap Rate muy bajo ({cap_rate:.2f}%): Fondo de muy bajo riesgo con retornos mínimos, "
                "o posible sobrevaloración de los activos del fondo."
            )
    
    def _get_risk_level(self, cap_rate: float) -> str:
        """
        Determina el nivel de riesgo basado en el Cap Rate.
        
        Args:
            cap_rate: Valor del Cap Rate en porcentaje
            
        Returns:
            str: Nivel de riesgo
        """
        if cap_rate >= 10:
            return "high"
        elif cap_rate >= 7:
            return "moderate"
        elif cap_rate >= 5:
            return "low"
        elif cap_rate >= 3:
            return "very_low"
        else:
            return "minimal"
    
    def _get_performance_rating(self, cap_rate: float) -> str:
        """
        Determina el rating de performance basado en el Cap Rate.
        
        Args:
            cap_rate: Valor del Cap Rate en porcentaje
            
        Returns:
            str: Rating de performance
        """
        if cap_rate >= 10:
            return "excellent"
        elif cap_rate >= 7:
            return "very_good"
        elif cap_rate >= 5:
            return "good"
        elif cap_rate >= 3:
            return "fair"
        else:
            return "poor"
    
    def _get_relative_performance(self, spread: float) -> str:
        """
        Determina performance relativa vs mercado.
        
        Args:
            spread: Diferencia entre cap rate del fondo y mercado
            
        Returns:
            str: Performance relativa
        """
        if spread > 1.5:
            return "significantly_outperforming"
        elif spread > 0.5:
            return "outperforming"
        elif spread > -0.5:
            return "in_line"
        elif spread > -1.5:
            return "underperforming"
        else:
            return "significantly_underperforming"
    
    def _get_valuation_assessment(
        self,
        current_value: float,
        implied_value: float
    ) -> str:
        """
        Evalúa la valoración actual vs valor implícito.
        
        Args:
            current_value: Valor actual del fondo
            implied_value: Valor implícito a un cap rate objetivo
            
        Returns:
            str: Evaluación de valoración
        """
        diff_pct = ((current_value - implied_value) / implied_value) * 100
        
        if diff_pct > 20:
            return f"potentially_overvalued (current {diff_pct:+.1f}% above implied)"
        elif diff_pct > 10:
            return f"slightly_overvalued (current {diff_pct:+.1f}% above implied)"
        elif diff_pct > -10:
            return f"fairly_valued (current {diff_pct:+.1f}% vs implied)"
        elif diff_pct > -20:
            return f"slightly_undervalued (current {diff_pct:+.1f}% below implied)"
        else:
            return f"potentially_undervalued (current {diff_pct:+.1f}% below implied)"