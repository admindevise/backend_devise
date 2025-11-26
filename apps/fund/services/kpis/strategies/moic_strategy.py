"""
MOIC (Multiple on Invested Capital) Calculation Strategy para Fund Investment
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta

from ..core.base_strategy import BaseKPIStrategy
from apps.fund.models.core import Fund
from apps.fund.models.membership import FundInvestment
from apps.fund.models.distributions import InvestmentDistributionRecord


class MOICCalculationStrategy(BaseKPIStrategy):
    """
    Strategy para calcular MOIC (Múltiplo de Inversión) de una inversión específica.
    
    Cuántas veces multiplicó el inversionista su inversión inicial.
    
    Formula:
    MOIC = (Total Distribuciones Recibidas + Valor Actual Inversión) / Inversión Inicial
    
    Donde:
    - Total Distribuciones = Σ net_distribution_amount_cop de InvestmentDistributionRecord
    - Valor Actual = units_owned × current_unit_value (o purchase_price_per_unit)
    - Inversión Inicial = final_invested_amount
    
    Interpretación:
    - MOIC < 1.0x = Pérdida (no recuperó su inversión)
    - MOIC = 1.0x = Break-even (recuperó exactamente su inversión)
    - MOIC > 1.0x = Ganancia (multiplicó su inversión)
    - MOIC > 2.0x = Excelente retorno (duplicó o más)
    
    Example:
        >>> investment = FundInvestment.objects.get(id=5)
        >>> strategy = MOICCalculationStrategy(investment.application.fund)
        >>> result = strategy.calculate(investment_id=investment.id)
    """
    
    def __init__(self, fund: Fund):
        super().__init__(fund)
    
    def validate_prerequisites(self) -> Dict[str, bool]:
        """Valida que el fondo sea válido"""
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
        investment_id: int,
        exit_price_per_unit: Optional[Decimal] = None  # ✅ NUEVO: Precio de salida/venta
    ) -> Dict[str, Any]:
        """
        Calcula MOIC de una inversión específica.
        
        Formula:
        MOIC = (Total Distribuciones + Valor de Salida) / Inversión Inicial
        
        Args:
            investment_id: ID de FundInvestment
            exit_price_per_unit: Precio de salida/venta del token (opcional, si no se provee usa precio actual)
            
        Returns:
            dict: Resultado del MOIC con desglose completo
        """
        
        # 1. Validar prerequisites
        prereq = self.validate_prerequisites()
        if not prereq['is_valid']:
            return {
                'error': 'Fund prerequisites not met',
                **self._get_fund_info(),
                'validations': prereq['validations']
            }
        
        # 2. Obtener la inversión
        try:
            investment = FundInvestment.objects.select_related(
                'application__fund',
                'application__user'
            ).get(
                id=investment_id,
                application__fund=self.fund
            )
        except FundInvestment.DoesNotExist:
            return {
                'error': f'Inversión con ID {investment_id} no encontrada o no pertenece al fondo',
                **self._get_fund_info(),
                'investment_id': investment_id
            }
        
        try:
            # 3. Obtener inversión inicial
            initial_investment = investment.final_invested_amount or Decimal('0.00')
            
            if initial_investment == 0:
                return {
                    'error': 'Inversión inicial es cero o inválida',
                    **self._get_fund_info(),
                    'investment_id': investment.id,
                    'final_invested_amount': float(initial_investment)
                }
            
            # 4. Calcular total de distribuciones REALES recibidas
            distributions = InvestmentDistributionRecord.objects.filter(
                investment=investment
            )
            
            total_distributions_received = distributions.aggregate(
                total=Sum('net_distribution_amount_cop')
            )['total'] or Decimal('0.00')
            
            # 5. ✅ CORRECCIÓN: Calcular valor de salida del token
            units_owned = investment.units_owned
            
            # Usar precio de salida provisto, o precio actual como default
            if exit_price_per_unit:
                price_per_unit = exit_price_per_unit
                price_source = 'exit_price_provided'
            elif investment.current_unit_value:
                price_per_unit = investment.current_unit_value
                price_source = 'current_market_price'
            elif investment.application.fund.price_per_unit:
                price_per_unit = investment.application.fund.price_per_unit
                price_source = 'fund_current_price'
            else:
                price_per_unit = investment.purchase_price_per_unit
                price_source = 'purchase_price'
            
            exit_value = Decimal(str(units_owned)) * price_per_unit
            
            # 6. ✅ FÓRMULA CORRECTA: Total Recibido = Distribuciones + Valor de Salida
            total_received = total_distributions_received + exit_value
            
            # 7. ✅ CALCULAR MOIC
            moic = total_received / initial_investment
            
            # 8. Calcular métricas adicionales
            absolute_gain_loss = total_received - initial_investment
            return_percentage = ((total_received - initial_investment) / initial_investment) * 100
            
            # Desglose de contribuciones
            distributions_contribution_pct = (total_distributions_received / total_received) * 100 if total_received > 0 else Decimal('0.00')
            exit_value_contribution_pct = (exit_value / total_received) * 100 if total_received > 0 else Decimal('0.00')
            
            # Calcular días de tenencia
            investment_date = investment.created_at.date()
            days_held = (timezone.now().date() - investment_date).days
            years_held = Decimal(str(days_held)) / Decimal('365.25')
            
            # Retorno anualizado
            annualized_return = (return_percentage / years_held) if years_held > 0 else Decimal('0.00')
            
            # 9. Interpretación
            interpretation = self._interpret_moic(float(moic))
            
            return {
                **self._get_fund_info(),
                
                # Información de la inversión
                'investment_info': {
                    'investment_id': investment.id,
                    'investor_id': investment.application.user.id,
                    'investor_name': investment.application.user.get_full_name(),
                    'investor_email': investment.application.user.email,
                    'investment_date': investment.created_at.strftime("%Y-%m-%d"),
                    'days_held': days_held,
                    'years_held': float(years_held),
                    'units_owned': units_owned,
                    'investment_status': investment.investment_status
                },
                
                # MOIC principal
                'moic_metrics': {
                    'moic': float(moic),
                    'moic_display': f"{float(moic):.2f}x",
                    'calculation_method': 'equity_multiple'
                },
                
                # Componentes de entrada
                'investment_components': {
                    'initial_investment': float(initial_investment),
                    'total_distributions_received': float(total_distributions_received),
                    'exit_value': float(exit_value),
                    'exit_price_per_unit': float(price_per_unit),
                    'price_source': price_source,
                    'purchase_price_per_unit': float(investment.purchase_price_per_unit),
                    'total_received': float(total_received)
                },
                
                # Métricas de retorno
                'return_metrics': {
                    'absolute_gain_loss': float(absolute_gain_loss),
                    'return_percentage': float(return_percentage),
                    'annualized_return_percentage': float(annualized_return),
                    'distributions_contribution_percentage': float(distributions_contribution_pct),
                    'exit_value_contribution_percentage': float(exit_value_contribution_pct)
                },
                
                # Desglose de distribuciones
                'distributions_summary': {
                    'total_distributions_count': distributions.count(),
                    'total_amount_received': float(total_distributions_received),
                    'average_distribution': float(total_distributions_received / distributions.count()) if distributions.count() > 0 else 0
                },
                
                # Interpretación
                'interpretation': interpretation,
                'performance_level': self._get_performance_level(float(moic)),
                'outcome': self._get_outcome(float(moic)),
                
                # Metadata
                'calculation_date': timezone.now().isoformat(),
                'calculation_note': 'MOIC = (Distribuciones Recibidas + Valor de Salida del Token) / Inversión Inicial'
            }
            
        except Exception as e:
            return {
                'error': f'Error: {str(e)}',
                **self._get_fund_info(),
                'investment_id': investment.id
            }

    def _interpret_moic(self, moic: float) -> str:
        """Interpreta el MOIC según rangos estándar"""
        
        if moic >= 3.0:
            return f"Excelente inversión ({moic:.2f}x): Triplicó su inversión inicial. Por cada $1 invertido, recibió ${moic:.2f}."
        elif moic >= 2.0:
            return f"Muy buena inversión ({moic:.2f}x): Duplicó su inversión. Por cada $1 invertido, recibió ${moic:.2f}."
        elif moic >= 1.5:
            return f"Buena inversión ({moic:.2f}x): Incrementó su inversión en {(moic-1)*100:.0f}%. Por cada $1 invertido, recibió ${moic:.2f}."
        elif moic >= 1.0:
            return f"Inversión positiva ({moic:.2f}x): Recuperó su inversión y generó {(moic-1)*100:.0f}% de ganancia."
        elif moic >= 0.5:
            return f"Inversión con pérdida moderada ({moic:.2f}x): Recuperó {moic*100:.0f}% de su inversión."
        else:
            return f"Inversión con pérdida significativa ({moic:.2f}x): Solo recuperó {moic*100:.0f}% de su inversión."
    
    def _get_performance_level(self, moic: float) -> str:
        """Determina el nivel de desempeño basado en MOIC"""
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
        """Determina el resultado de la inversión"""
        if moic > 1.0:
            return "gain"
        elif moic == 1.0:
            return "break_even"
        else:
            return "loss"