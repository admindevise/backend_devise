"""
IRR (Internal Rate of Return) Calculation Strategy
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from django.utils import timezone
import numpy as np
from numpy_financial import irr

from ..core.base_strategy import BaseKPIStrategy
from apps.asset.models.core import Asset


class IRRCalculationStrategy(BaseKPIStrategy):
    """
    Strategy para calcular TIR (Tasa Interna de Retorno / IRR).
    
    El retorno anualizado total considerando TODAS las entradas y salidas de efectivo
    durante la vida de la inversión, incluyendo el valor de salida.
    
    Formula:
    0 = Σ [Flujos de Caja / (1 + TIR)^t] - Inversión Inicial
    
    Donde:
    - Inversión Inicial: Capital invertido por token (negativo)
    - Flujos de Caja: Dividendos recibidos por período
    - Valor de Salida: Precio de venta final del token
    - t: Período de tiempo
    
    Nota:
    - TIR se calcula usando método iterativo (Newton-Raphson)
    - Considera todos los dividendos recibidos + ganancia/pérdida de capital al vender
    - Es una métrica anualizada que refleja el retorno real del inversionista
    
    Interpretación:
    - TIR > 15%: Excelente inversión
    - TIR 10-15%: Muy buena inversión
    - TIR 7-10%: Buena inversión
    - TIR < 7%: Inversión moderada/baja
    
    Example:
        >>> strategy = IRRCalculationStrategy(asset)
        >>> result = strategy.calculate(
        ...     exit_price_per_token=4600,
        ...     holding_period_years=5
        ... )
        >>> print(f"TIR: {result['irr_percentage']:.2f}%")
    """
    
    def __init__(self, asset: Asset):
        super().__init__(asset)
    
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
        annual_dividends_per_token: Optional[Decimal] = None,
        exit_price_per_token: Optional[Decimal] = None,
        holding_period_years: int = 5,
        use_historical_dividends: bool = False
    ) -> Dict[str, Any]:
        """
        Calcula TIR del activo.
        
        Args:
            annual_dividends_per_token: Dividendos anuales por token (opcional)
            exit_price_per_token: Precio de venta final del token (opcional)
            holding_period_years: Años de tenencia (default: 5)
            use_historical_dividends: Usar dividendos históricos si están disponibles
            
        Returns:
            dict: Resultado del TIR con flujos de caja y métricas
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
            # 2. Obtener inversión inicial por token
            total_tokens = self.asset.total_tokens_issued
            acquisition_value = self.asset.acquisition_value
            initial_investment_per_token = acquisition_value / Decimal(str(total_tokens))
            
            # 3. Determinar dividendos anuales por token
            if use_historical_dividends:
                # Calcular dividendos promedio usando Dividend Yield histórico
                annual_dividends = self._calculate_historical_annual_dividends()
            elif annual_dividends_per_token:
                annual_dividends = annual_dividends_per_token
            else:
                # Usar Dividend Yield actual proyectado
                annual_dividends = self._estimate_annual_dividends_from_fcf()
            
            # 4. Determinar precio de salida
            if exit_price_per_token:
                exit_price = exit_price_per_token
            else:
                # Usar Output Value proyectado
                exit_price = self._estimate_exit_price(holding_period_years)
            
            # 5. Construir flujo de caja
            # Período 0: Inversión inicial (negativo)
            # Períodos 1-N: Dividendos anuales
            # Período N: Dividendos + Precio de venta
            
            cash_flows = []
            cash_flows.append(-float(initial_investment_per_token))  # Período 0: Inversión
            
            for year in range(1, holding_period_years + 1):
                if year < holding_period_years:
                    # Años intermedios: solo dividendos
                    cash_flows.append(float(annual_dividends))
                else:
                    # Último año: dividendos + precio de venta
                    final_cash_flow = float(annual_dividends) + float(exit_price)
                    cash_flows.append(final_cash_flow)
            
            # 6. Calcular TIR usando numpy_financial
            try:
                irr_decimal = irr(cash_flows)
                irr_percentage = irr_decimal * 100
                
                # Validar que TIR sea un número válido
                if np.isnan(irr_percentage) or np.isinf(irr_percentage):
                    return {
                        'error': 'No se pudo calcular TIR (flujos de caja no convergen)',
                        'asset_id': self.asset.id,
                        'cash_flows': cash_flows
                    }
                
            except Exception as e:
                return {
                    'error': f'Error calculando TIR: {str(e)}',
                    'asset_id': self.asset.id,
                    'cash_flows': cash_flows
                }
            
            # 7. Calcular métricas adicionales
            total_dividends_received = annual_dividends * holding_period_years
            capital_gain = exit_price - initial_investment_per_token
            total_return = total_dividends_received + capital_gain
            
            # Multiple on Invested Capital (MOIC)
            moic = (exit_price + total_dividends_received) / initial_investment_per_token
            
            # 8. Interpretación
            interpretation = self._interpret_irr(float(irr_percentage))
            
            return {
                'asset_id': self.asset.id,
                'asset_code': self.asset.asset_code,
                'asset_name': self.asset.name,
                'fund_id': self.asset.fund.id,
                'fund_name': self.asset.fund.name,
                
                # TIR principal
                'irr_percentage': float(irr_percentage),
                'irr_decimal': float(irr_decimal),
                
                # Componentes de entrada
                'investment_parameters': {
                    'initial_investment_per_token': float(initial_investment_per_token),
                    'annual_dividends_per_token': float(annual_dividends),
                    'exit_price_per_token': float(exit_price),
                    'holding_period_years': holding_period_years
                },
                
                # Flujo de caja
                'cash_flows': {
                    'period_0_investment': cash_flows[0],
                    'annual_cash_flows': cash_flows[1:],
                    'all_cash_flows': cash_flows
                },
                
                # Métricas de retorno
                'return_metrics': {
                    'total_dividends_received': float(total_dividends_received),
                    'capital_gain_loss': float(capital_gain),
                    'total_return': float(total_return),
                    'moic': float(moic),
                    'total_return_percentage': float((total_return / initial_investment_per_token) * 100)
                },
                
                # Desglose anual
                'annual_breakdown': self._build_annual_breakdown(
                    initial_investment_per_token,
                    annual_dividends,
                    exit_price,
                    holding_period_years,
                    irr_decimal
                ),
                
                # Interpretación
                'interpretation': interpretation,
                'performance_level': self._get_performance_level(float(irr_percentage)),
                
                # Información del activo
                'asset_metrics': {
                    'total_tokens_issued': total_tokens,
                    'acquisition_value': float(acquisition_value),
                    'current_price_per_unit': float(self.asset.price_per_unit) if hasattr(self.asset, 'price_per_unit') else None
                },
                
                # Metadata
                'calculation_date': timezone.now().isoformat(),
                'calculation_method': 'numpy_financial.irr (Newton-Raphson)',
                'data_source': 'historical' if use_historical_dividends else 'projected'
            }
            
        except Exception as e:
            return {
                'error': f'Error: {str(e)}',
                'asset_id': self.asset.id,
                'asset_code': self.asset.asset_code
            }
    
    def _calculate_historical_annual_dividends(self) -> Decimal:
        """Calcula dividendos anuales promedio usando datos históricos"""
        from .dividend_yield_moving_strategy import DividendYieldMovingAverageStrategy
        
        dy_ma_strategy = DividendYieldMovingAverageStrategy(self.asset)
        dy_ma_result = dy_ma_strategy.calculate(months_back=12, include_monthly_breakdown=False)
        
        if 'error' in dy_ma_result:
            # Fallback: usar FCF promedio
            return self._estimate_annual_dividends_from_fcf()
        
        # Usar dividendo anual promedio
        avg_annual_dividend = Decimal(str(dy_ma_result.get('annual_metrics', {}).get('fcf_per_token', 0)))
        return avg_annual_dividend
    
    def _estimate_annual_dividends_from_fcf(self) -> Decimal:
        """Estima dividendos anuales desde FCF"""
        from .free_cash_flow_strategy import FreeCashFlowCalculationStrategy
        
        fcf_strategy = FreeCashFlowCalculationStrategy(self.asset)
        fcf_result = fcf_strategy.calculate(months_back=12, include_breakdown=False)
        
        if 'error' in fcf_result:
            return Decimal('0.00')
        
        fcf_per_token = Decimal(str(fcf_result.get('fcf_per_token', 0)))
        return fcf_per_token
    
    def _estimate_exit_price(self, years: int) -> Decimal:
        """Estima precio de salida usando Output Value"""
        from .output_value_strategy import OutputValueCalculationStrategy
        
        output_value_strategy = OutputValueCalculationStrategy(self.asset)
        output_result = output_value_strategy.calculate(projection_years=years)
        
        if 'error' in output_result:
            # Fallback: usar precio actual
            return self.asset.price_per_unit if hasattr(self.asset, 'price_per_unit') else self.asset.acquisition_value / Decimal(str(self.asset.total_tokens_issued))
        
        output_value = Decimal(str(output_result.get('output_value', 0)))
        total_tokens = self.asset.total_tokens_issued
        exit_price_per_token = output_value / Decimal(str(total_tokens))
        
        return exit_price_per_token
    
    def _build_annual_breakdown(
        self,
        initial_investment: Decimal,
        annual_dividend: Decimal,
        exit_price: Decimal,
        years: int,
        irr_decimal: float
    ) -> List[Dict[str, Any]]:
        """Construye desglose anual de flujos de caja"""
        breakdown = []
        
        # Año 0: Inversión
        breakdown.append({
            'year': 0,
            'cash_flow': float(-initial_investment),
            'cash_flow_type': 'investment',
            'cumulative_dividends': 0.0,
            'present_value': float(-initial_investment)
        })
        
        cumulative_dividends = Decimal('0.00')
        
        for year in range(1, years + 1):
            if year < years:
                cash_flow = annual_dividend
                cash_flow_type = 'dividends'
            else:
                cash_flow = annual_dividend + exit_price
                cash_flow_type = 'dividends_and_exit'
            
            cumulative_dividends += annual_dividend
            
            # Calcular valor presente
            present_value = float(cash_flow) / ((1 + irr_decimal) ** year)
            
            breakdown.append({
                'year': year,
                'cash_flow': float(cash_flow),
                'cash_flow_type': cash_flow_type,
                'dividends_component': float(annual_dividend),
                'exit_price_component': float(exit_price) if year == years else 0.0,
                'cumulative_dividends': float(cumulative_dividends),
                'present_value': present_value
            })
        
        return breakdown
    
    def _interpret_irr(self, irr: float) -> str:
        """
        Interpreta el TIR según rangos estándar.
        
        Args:
            irr: Valor del TIR en porcentaje
            
        Returns:
            str: Interpretación textual
        """
        if irr >= 15:
            return f"Excelente inversión: TIR de {irr:.2f}% supera ampliamente el retorno esperado del mercado. La inversión genera valor significativo considerando todos los flujos de caja."
        elif irr >= 10:
            return f"Muy buena inversión: TIR de {irr:.2f}% está por encima del retorno promedio del mercado inmobiliario. Inversión sólida con buenos retornos totales."
        elif irr >= 7:
            return f"Buena inversión: TIR de {irr:.2f}% está en línea con el mercado. Retorno aceptable considerando dividendos y apreciación."
        elif irr >= 5:
            return f"Inversión moderada: TIR de {irr:.2f}% es conservador. Retorno bajo pero estable."
        elif irr > 0:
            return f"Inversión con retorno bajo: TIR de {irr:.2f}% está por debajo de expectativas. Requiere revisión de estrategia."
        elif irr == 0:
            return "Inversión en punto de equilibrio: TIR de 0% indica que no hay ganancia ni pérdida."
        else:
            return f"Inversión con pérdida: TIR negativo de {irr:.2f}% indica que se pierde valor. La inversión destruye capital."
    
    def _get_performance_level(self, irr: float) -> str:
        """
        Determina el nivel de desempeño basado en TIR.
        
        Args:
            irr: Valor del TIR en porcentaje
            
        Returns:
            str: 'excellent', 'very_good', 'good', 'moderate', 'poor', 'negative'
        """
        if irr >= 15:
            return "excellent"
        elif irr >= 10:
            return "very_good"
        elif irr >= 7:
            return "good"
        elif irr >= 5:
            return "moderate"
        elif irr > 0:
            return "poor"
        else:
            return "negative"