"""
Cap Rate Calculation Strategy
"""

from typing import Dict, Any
from decimal import Decimal
from django.utils import timezone

from ..core.base_strategy import BaseKPIStrategy
from apps.asset.models.core import Asset
from .noi_strategy import NOICalculationStrategy


class CapRateCalculationStrategy(BaseKPIStrategy):
    """
    Strategy para calcular Cap Rate (Capitalization Rate).
    
    Cap Rate = (NOI Anual / Valor del Activo) * 100
    
    Interpretación:
    - Cap Rate alto (8-12%): Mayor retorno, mayor riesgo
    - Cap Rate bajo (4-6%): Menor retorno, activo más estable
    
    Inputs:
    - NOI anual (de los últimos 12 meses)
    - Valor del activo (acquisition_value o valor de mercado actual)
    
    Formula:
    Cap Rate = (noi_anual / valor_activo) * 100
    """
    
    def __init__(self, asset: Asset):
        super().__init__(asset)
        self.noi_strategy = NOICalculationStrategy(asset)
    
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
    
    def calculate(self, **kwargs) -> Dict[str, Any]:
        """
        Calcula Cap Rate usando NOI de los últimos 12 meses.
        
        Returns:
            dict: {
                'cap_rate': float,
                'noi_anual': float,
                'valor_activo': float,
                'interpretation': str,
                ...
            }
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
            # 2. Obtener NOI anual (últimos 12 meses) usando NOICalculationStrategy
            noi_result = self.noi_strategy.calculate(
                months_back=12,
                include_breakdown=False
            )
            
            # Validar que el NOI se calculó correctamente
            if 'error' in noi_result:
                return {
                    'error': f"Error calculando NOI: {noi_result['error']}",
                    'asset_id': self.asset.id,
                    'asset_code': self.asset.asset_code
                }
            
            noi_anual = Decimal(str(noi_result.get('total_noi_12m', 0)))
            
            # 3. Obtener valor del activo (acquisition_value)
            valor_activo = self.asset.acquisition_value
            
            # Validar que el valor del activo sea válido
            if not valor_activo or valor_activo <= 0:
                return {
                    'error': 'Valor del activo inválido o cero',
                    'asset_id': self.asset.id,
                    'asset_code': self.asset.asset_code,
                    'acquisition_value': float(valor_activo) if valor_activo else 0
                }
            
            # 4. Calcular Cap Rate
            # Cap Rate = (NOI Anual / Valor del Activo) * 100
            cap_rate = (noi_anual / valor_activo) * 100
            
            # 5. Interpretación del Cap Rate
            interpretation = self._interpret_cap_rate(float(cap_rate))
            
            # 6. Métricas adicionales
            # Si el cap rate es conocido, podemos deducir el valor del activo
            # Valor Activo = NOI / Cap Rate
            # O deducir NOI requerido para un cap rate objetivo
            
            return {
                'asset_id': self.asset.id,
                'asset_code': self.asset.asset_code,
                'asset_name': self.asset.name,
                'fund_id': self.asset.fund.id,
                'fund_name': self.asset.fund.name,
                
                # Métricas principales
                'cap_rate': float(cap_rate),
                'noi_anual': float(noi_anual),
                'valor_activo': float(valor_activo),
                
                # Interpretación
                'interpretation': interpretation,
                'risk_level': self._get_risk_level(float(cap_rate)),
                
                # Métricas del NOI
                'noi_margin_percentage': noi_result.get('noi_margin_percentage', 0),
                'average_monthly_noi': noi_result.get('average_monthly_noi', 0),
                
                # Información del activo
                'asset_metrics': {
                    'total_area_m2': float(self.asset.total_area_m2),
                    'rentable_area_m2': float(self.asset.rentable_area_m2) if self.asset.rentable_area_m2 else None,
                    'cap_rate_per_m2': float(cap_rate / self.asset.total_area_m2) if self.asset.total_area_m2 > 0 else None
                },
                
                # Metadata
                'calculation_date': timezone.now().isoformat(),
                'noi_period': noi_result.get('period_analyzed', 'últimos 12 meses')
            }
            
        except Exception as e:
            return {
                'error': f'Error calculando Cap Rate: {str(e)}',
                'asset_id': self.asset.id,
                'asset_code': self.asset.asset_code
            }
    
    def _interpret_cap_rate(self, cap_rate: float) -> str:
        """
        Interpreta el Cap Rate según rangos estándar.
        
        Args:
            cap_rate: Valor del Cap Rate en porcentaje
            
        Returns:
            str: Interpretación textual
        """
        if cap_rate >= 10:
            return "Cap Rate alto: Mayor retorno potencial, mayor riesgo. Activo con posibles desafíos o en mercados emergentes."
        elif cap_rate >= 7:
            return "Cap Rate moderado-alto: Retorno atractivo con riesgo controlado. Típico de activos bien establecidos."
        elif cap_rate >= 5:
            return "Cap Rate moderado: Retorno balanceado, activo estable. Común en mercados maduros."
        elif cap_rate >= 3:
            return "Cap Rate bajo: Menor retorno, activo muy estable. Típico de ubicaciones prime o activos premium."
        else:
            return "Cap Rate muy bajo: Activo de muy bajo riesgo o posible sobrevaloración."
    
    def _get_risk_level(self, cap_rate: float) -> str:
        """
        Determina el nivel de riesgo basado en el Cap Rate.
        
        Args:
            cap_rate: Valor del Cap Rate en porcentaje
            
        Returns:
            str: 'low', 'moderate', 'high', 'very_high'
        """
        if cap_rate >= 10:
            return "high"
        elif cap_rate >= 7:
            return "moderate"
        elif cap_rate >= 4:
            return "low"
        else:
            return "very_low"