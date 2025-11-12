"""
MOIC (Multiple on Invested Capital) Calculation Strategy para Fund
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from ..core.base_strategy import BaseKPIStrategy
from apps.fund.models.core import Fund


class MOICCalculationStrategy(BaseKPIStrategy):
    """
    Strategy para calcular MOIC (Múltiplo de Inversión / Multiple on Invested Capital) del fondo.
    
    Cuántas veces multiplicaste tu inversión inicial al final del período.
    
    Formula:
    MOIC = Total Recibido / Inversión Inicial
    
    Donde:
    - Total Recibido = Σ Dividendos + Valor de Salida del Token
    - Inversión Inicial = Capital invertido por token
    
    Interpretación:
    - MOIC < 1.0x = Pérdida (no recuperaste tu inversión)
    - MOIC = 1.0x = Recuperaste exactamente tu inversión (break-even)
    - MOIC > 1.0x = Ganancia (multiplicaste tu inversión)
    - MOIC > 2.0x = Excelente retorno (duplicaste o más)
    
    Example:
        >>> strategy = MOICCalculationStrategy(fund)
        >>> result = strategy.calculate(
        ...     total_dividends_received=Decimal('2000'),
        ...     exit_price_per_token=Decimal('4600'),
        ...     holding_period_years=5
        ... )
        >>> print(f"MOIC: {result['moic']:.2f}x")
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
            'has_acquisition_value': bool(
                hasattr(self.fund, 'acquisition_value') and 
                self.fund.acquisition_value
            ) if self.fund else False
        }
        
        return {
            'is_valid': all(validations.values()),
            'validations': validations
        }
    
    def calculate(
        self,
        total_dividends_received: Optional[Decimal] = None,
        exit_price_per_token: Optional[Decimal] = None,
        holding_period_years: int = 5,
        use_historical_dividends: bool = False
    ) -> Dict[str, Any]:
        """
        Calcula MOIC del fondo.
        
        Args:
            total_dividends_received: Suma total de dividendos recibidos por token (opcional)
            exit_price_per_token: Precio de venta final del token (opcional)
            holding_period_years: Años de tenencia (default: 5)
            use_historical_dividends: Usar dividendos históricos si están disponibles
            
        Returns:
            dict: Resultado del MOIC con desglose
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
            # 2. Obtener inversión inicial por token
            total_units = self.fund.amount_tokens
            
            # Usar initial_price_per_unit si existe, sino usar acquisition_value / units
            if hasattr(self.fund, 'initial_price_per_unit') and self.fund.initial_price_per_unit:
                initial_investment_per_token = self.fund.initial_price_per_unit
            else:
                acquisition_value = self.fund.acquisition_value
                initial_investment_per_token = acquisition_value / Decimal(str(total_units))
            
            # 3. Determinar suma de dividendos recibidos
            if use_historical_dividends:
                # Calcular dividendos históricos usando DistributionPeriod
                total_dividends = self._calculate_historical_total_dividends(holding_period_years)
            elif total_dividends_received is not None:
                total_dividends = total_dividends_received
            else:
                # Estimar dividendos desde FCF proyectado
                total_dividends = self._estimate_total_dividends(holding_period_years)
            
            # 4. Determinar precio de salida
            if exit_price_per_token:
                exit_price = exit_price_per_token
            else:
                # Usar Output Value proyectado
                exit_price = self._estimate_exit_price(holding_period_years)
            
            # 5. Calcular Total Recibido
            # Total Recibido = Suma dividendos + Valor de salida del token
            total_received = total_dividends + exit_price
            
            # 6. Calcular MOIC
            # MOIC = Total Recibido / Inversión Inicial
            if initial_investment_per_token > 0:
                moic = total_received / initial_investment_per_token
            else:
                return {
                    'error': 'Inversión inicial inválida o cero',
                    **self._get_fund_info(),
                    'initial_investment_per_token': float(initial_investment_per_token)
                }
            
            # 7. Calcular métricas adicionales
            # Ganancia/Pérdida absoluta
            absolute_gain_loss = total_received - initial_investment_per_token
            
            # Retorno porcentual
            return_percentage = ((total_received - initial_investment_per_token) / initial_investment_per_token) * 100
            
            # Desglose de contribuciones
            dividends_contribution_percentage = (total_dividends / total_received) * 100 if total_received > 0 else 0
            exit_value_contribution_percentage = (exit_price / total_received) * 100 if total_received > 0 else 0
            
            # 8. Interpretación
            interpretation = self._interpret_moic(float(moic))
            
            return {
                **self._get_fund_info(),
                
                # MOIC principal
                'moic': float(moic),
                'moic_display': f"{float(moic):.2f}x",
                
                # Componentes de entrada
                'investment_components': {
                    'initial_investment_per_token': float(initial_investment_per_token),
                    'total_dividends_received': float(total_dividends),
                    'exit_price_per_token': float(exit_price),
                    'total_received': float(total_received),
                    'holding_period_years': holding_period_years
                },
                
                # Métricas de retorno
                'return_metrics': {
                    'absolute_gain_loss': float(absolute_gain_loss),
                    'return_percentage': float(return_percentage),
                    'dividends_contribution_percentage': float(dividends_contribution_percentage),
                    'exit_value_contribution_percentage': float(exit_value_contribution_percentage)
                },
                
                # Interpretación
                'interpretation': interpretation,
                'performance_level': self._get_performance_level(float(moic)),
                'outcome': self._get_outcome(float(moic)),
                
                # Información del fondo
                'fund_metrics': {
                    'total_tokens_issued': total_units,
                    'acquisition_value': float(self.fund.acquisition_value) if hasattr(self.fund, 'acquisition_value') else None,
                    'current_price_per_unit': float(self.fund.price_per_unit) if hasattr(self.fund, 'price_per_unit') and self.fund.price_per_unit else None,
                    'initial_price_per_unit': float(self.fund.initial_price_per_unit) if hasattr(self.fund, 'initial_price_per_unit') and self.fund.initial_price_per_unit else None
                },
                
                # Metadata
                'calculation_date': timezone.now().isoformat(),
                'data_source': 'historical' if use_historical_dividends else 'projected'
            }
            
        except Exception as e:
            return {
                'error': f'Error: {str(e)}',
                **self._get_fund_info()
            }
    
    def _calculate_historical_total_dividends(self, years: int) -> Decimal:
        """Calcula suma total de dividendos históricos usando DistributionPeriod"""
        from apps.fund.models.distributions import DistributionPeriod
        from django.db.models import Sum
        
        # Obtener últimos N años
        end_date = timezone.now()
        start_date = end_date - timedelta(days=365 * years)
        
        # Sumar todas las distribuciones por token en el período
        distributions = DistributionPeriod.objects.filter(
            fund=self.fund,
            status='completed',
            period_year__gte=start_date.year,
            period_year__lte=end_date.year
        ).aggregate(
            total_per_token=Sum('distribution_per_token')
        )
        
        total_distributed_per_token = distributions.get('total_per_token') or Decimal('0.00')
        
        if total_distributed_per_token == 0:
            # Fallback: usar FCF como proyección
            return self._estimate_total_dividends(years)
        
        return total_distributed_per_token
    
    def _estimate_total_dividends(self, years: int) -> Decimal:
        """Estima suma total de dividendos desde FCF anual proyectado"""
        from .free_cash_flow_strategy import FreeCashFlowCalculationStrategy
        
        fcf_strategy = FreeCashFlowCalculationStrategy(self.fund)
        fcf_result = fcf_strategy.calculate(months_back=12, include_breakdown=False)
        
        if 'error' in fcf_result:
            return Decimal('0.00')
        
        # FCF anual por token
        annual_fcf_per_token = Decimal(str(fcf_result.get('fcf_per_unit', 0)))
        
        # Proyectar para N años
        total_dividends = annual_fcf_per_token * years
        return total_dividends
    
    def _estimate_exit_price(self, years: int) -> Decimal:
        """Estima precio de salida usando Output Value"""
        from .output_value_strategy import OutputValueCalculationStrategy
        
        output_value_strategy = OutputValueCalculationStrategy(self.fund)
        output_result = output_value_strategy.calculate(projection_years=years)
        
        if 'error' in output_result:
            # Fallback: usar precio actual
            if hasattr(self.fund, 'price_per_unit') and self.fund.price_per_unit:
                return self.fund.price_per_unit
            elif hasattr(self.fund, 'initial_price_per_unit') and self.fund.initial_price_per_unit:
                return self.fund.initial_price_per_unit
            else:
                acquisition_value = self.fund.acquisition_value
                total_units = self.fund.amount_tokens
                return acquisition_value / Decimal(str(total_units))
        
        output_value = Decimal(str(output_result.get('output_value', 0)))
        total_units = self.fund.amount_tokens
        exit_price_per_token = output_value / Decimal(str(total_units))
        
        return exit_price_per_token
    
    def _interpret_moic(self, moic: float) -> str:
        """
        Interpreta el MOIC según rangos estándar.
        
        Args:
            moic: Valor del MOIC en múltiplos
            
        Returns:
            str: Interpretación textual
        """
        if moic >= 3.0:
            return f"Excelente inversión: {moic:.2f}x - Triplicaste o más tu inversión inicial. Retorno excepcional considerando dividendos y apreciación."
        elif moic >= 2.0:
            return f"Muy buena inversión: {moic:.2f}x - Duplicaste tu inversión. Retorno sólido que supera ampliamente expectativas."
        elif moic >= 1.5:
            return f"Buena inversión: {moic:.2f}x - Incrementaste tu inversión en 50%+. Retorno positivo considerable."
        elif moic >= 1.0:
            return f"Inversión positiva: {moic:.2f}x - Recuperaste tu inversión y generaste ganancia. Retorno aceptable."
        elif moic >= 0.8:
            return f"Inversión con pérdida moderada: {moic:.2f}x - Recuperaste la mayor parte pero no toda tu inversión."
        else:
            return f"Inversión con pérdida significativa: {moic:.2f}x - No recuperaste tu inversión inicial. Requiere revisión de estrategia."
    
    def _get_performance_level(self, moic: float) -> str:
        """
        Determina el nivel de desempeño basado en MOIC.
        
        Args:
            moic: Valor del MOIC en múltiplos
            
        Returns:
            str: 'excellent', 'very_good', 'good', 'moderate', 'poor', 'loss'
        """
        if moic >= 3.0:
            return "excellent"
        elif moic >= 2.0:
            return "very_good"
        elif moic >= 1.5:
            return "good"
        elif moic >= 1.0:
            return "moderate"
        elif moic >= 0.8:
            return "poor"
        else:
            return "loss"
    
    def _get_outcome(self, moic: float) -> str:
        """
        Determina el resultado de la inversión.
        
        Args:
            moic: Valor del MOIC
            
        Returns:
            str: 'gain', 'break_even', 'loss'
        """
        if moic > 1.0:
            return "gain"
        elif moic == 1.0:
            return "break_even"
        else:
            return "loss"