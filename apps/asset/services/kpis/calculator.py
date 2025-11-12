"""
AssetKPICalculator - Orquestador que usa Strategies
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from apps.asset.models.core import Asset
from apps.asset.services.kpis.core.exceptions import AssetKPIError

from apps.asset.services.kpis.strategies.noi_strategy import NOICalculationStrategy
from apps.asset.services.kpis.strategies.cap_rate_strategy import CapRateCalculationStrategy
from apps.asset.services.kpis.strategies.output_value_strategy import OutputValueCalculationStrategy
from apps.asset.services.kpis.strategies.free_cash_flow_strategy import FreeCashFlowCalculationStrategy
from apps.asset.services.kpis.strategies.cash_on_cash_return_strategy import CashOnCashCalculationStrategy
from apps.asset.services.kpis.strategies.dividend_yield_strategy import DividendYieldCalculationStrategy
from apps.asset.services.kpis.strategies.dividend_yield_moving_strategy import DividendYieldMovingAverageStrategy
from apps.asset.services.kpis.strategies.irr_strategy import IRRCalculationStrategy
from apps.asset.services.kpis.strategies.moic_strategy import MOICCalculationStrategy


class AssetKPICalculator:
    """
    Calculador principal que orquesta Strategies de KPIs.
    
    Delega los cálculos a strategies especializadas.
    """
    
    def __init__(self, asset: Asset):
        if not asset:
            raise AssetKPIError("Asset is required")
        
        if not asset.pk:
            raise AssetKPIError("Asset must be saved")
        
        self.asset = asset
        
        # Instanciar strategies
        self.noi_strategy = NOICalculationStrategy(asset)
        self.cap_rate_strategy = CapRateCalculationStrategy(asset)
        self.output_value_strategy = OutputValueCalculationStrategy(asset)
        self.fcf_strategy = FreeCashFlowCalculationStrategy(asset)
        self.coc_strategy = CashOnCashCalculationStrategy(asset)
        self.dividend_yield_strategy = DividendYieldCalculationStrategy(asset)
        self.dividend_yield_ma_strategy = DividendYieldMovingAverageStrategy(asset)
        self.irr_strategy = IRRCalculationStrategy(asset)
        self.moic_strategy = MOICCalculationStrategy(asset)
                                
    
    # ========================================
    # NOI
    # ========================================    
    
    def calculate_noi(
        self,
        period_type: str = 'monthly',
        period_year: Optional[int] = None,
        period_month: Optional[int] = None,
        period_quarter: Optional[int] = None,
        months_back: int = 12,
        include_breakdown: bool = True
    ) -> Dict[str, Any]:
        """
        Calcula NOI delegando a NOICalculationStrategy.
        """
        return self.noi_strategy.calculate(
            period_type=period_type,
            period_year=period_year,
            period_month=period_month,
            period_quarter=period_quarter,
            months_back=months_back,
            include_breakdown=include_breakdown
        )
    
    def get_noi_summary(self, months: int = 12) -> Dict[str, Any]:
        """NOI con análisis"""
        return self.noi_strategy.calculate(
            months_back=months,
            include_breakdown=True
        )
        
    # ========================================
    # CAP RATE
    # ========================================
    
    def calculate_cap_rate(self) -> Dict[str, Any]:
        """
        Calcula Cap Rate (Capitalization Rate).
        
        Cap Rate = (NOI Anual / Valor del Activo) * 100
        
        Returns:
            dict: Resultado del Cap Rate con interpretación
        """
        return self.cap_rate_strategy.calculate()
    
    
    # ========================================
    # OUTPUT VALUE (VALOR DE SALIDA)
    # ========================================
    
    def calculate_output_value(
        self,
        projected_noi: Optional[Decimal] = None,
        exit_cap_rate: Optional[Decimal] = None,
        projection_years: int = 5,
        annual_noi_growth_rate: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Calcula el Valor de Salida del activo.
        
        Output Value = NOI Proyectado / Cap Rate de Salida
        
        Args:
            projected_noi: NOI proyectado al momento de salida (opcional)
            exit_cap_rate: Cap Rate de salida esperado (opcional)
            projection_years: Años hacia adelante (default: 5)
            annual_noi_growth_rate: Tasa de crecimiento anual del NOI (opcional)
            
        Returns:
            dict: Resultado del Output Value con métricas de retorno
        """
        return self.output_value_strategy.calculate(
            projected_noi=projected_noi,
            exit_cap_rate=exit_cap_rate,
            projection_years=projection_years,
            annual_noi_growth_rate=annual_noi_growth_rate
        )    
        
    # ========================================
    # FREE CASH FLOW
    # ========================================
    
    def calculate_free_cash_flow(
        self,
        period_type: str = 'monthly',
        period_year: Optional[int] = None,
        period_month: Optional[int] = None,
        period_quarter: Optional[int] = None,
        months_back: int = 12,
        include_breakdown: bool = True
    ) -> Dict[str, Any]:
        """
        Calcula Free Cash Flow (Flujo de Caja Libre).
        
        FCF = NOI + Ingresos no operativos - Gastos no operativos - CAPEX - Deuda
        
        Returns:
            dict: Resultado del FCF con componentes
        """
        return self.fcf_strategy.calculate(
            period_type=period_type,
            period_year=period_year,
            period_month=period_month,
            period_quarter=period_quarter,
            months_back=months_back,
            include_breakdown=include_breakdown
        )        
        
    # ========================================
    # CASH ON CASH
    # ========================================
    
    def calculate_cash_on_cash(
        self,
        months_back: int = 12,
        include_breakdown: bool = False
    ) -> Dict[str, Any]:
        """
        Calcula Cash on Cash Return del activo.
        
        Cash on Cash = (FCF Anual / Capital Invertido) × 100
        
        Args:
            months_back: Meses hacia atrás para FCF (default: 12)
            include_breakdown: Incluir desglose mensual
            
        Returns:
            dict: Resultado del Cash on Cash con interpretación
        """
        return self.coc_strategy.calculate(
            months_back=months_back,
            include_breakdown=include_breakdown
        )        
        
    # ========================================
    # DIVIDEND YIELD
    # ========================================
    
    def calculate_dividend_yield(
        self,
        period_type: str = 'monthly',
        period_year: Optional[int] = None,
        period_month: Optional[int] = None,
        period_quarter: Optional[int] = None,
        calculate_annualized: bool = True
    ) -> Dict[str, Any]:
        """
        Calcula Dividend Yield del activo.
        
        Dividend Yield = (Dividendo por Token / Valor Compra Token) × 100
        
        Returns:
            dict: Resultado del Dividend Yield
        """
        return self.dividend_yield_strategy.calculate(
            period_type=period_type,
            period_year=period_year,
            period_month=period_month,
            period_quarter=period_quarter,
            calculate_annualized=calculate_annualized
        )        
        
        
    # ========================================
    # DIVIDEND YIELD MOVING AVERAGE
    # ========================================
    
    def calculate_dividend_yield_moving_average(
        self,
        months_back: int = 12,
        include_monthly_breakdown: bool = True
    ) -> Dict[str, Any]:
        """
        Calcula Dividend Yield Promedio Móvil.
        
        Dividend Yield Promedio = Σ(Dividend Yields) / Número de Períodos
        
        Returns:
            dict: Resultado con métricas estadísticas y análisis de tendencia
        """
        return self.dividend_yield_ma_strategy.calculate(
            months_back=months_back,
            include_monthly_breakdown=include_monthly_breakdown
        )        
        
        
    # ========================================
    # IRR (TASA INTERNA DE RETORNO)
    # ========================================
    
    def calculate_irr(
        self,
        annual_dividends_per_token: Optional[Decimal] = None,
        exit_price_per_token: Optional[Decimal] = None,
        holding_period_years: int = 5,
        use_historical_dividends: bool = False
    ) -> Dict[str, Any]:
        """
        Calcula TIR (Tasa Interna de Retorno / IRR).
        
        0 = Σ [Flujos de Caja / (1 + TIR)^t] - Inversión Inicial
        
        Returns:
            dict: Resultado del TIR con flujos de caja y métricas
        """
        return self.irr_strategy.calculate(
            annual_dividends_per_token=annual_dividends_per_token,
            exit_price_per_token=exit_price_per_token,
            holding_period_years=holding_period_years,
            use_historical_dividends=use_historical_dividends
        )        
        
    # ========================================
    # MOIC (MÚLTIPLO DE INVERSIÓN)
    # ========================================
    
    def calculate_moic(
        self,
        total_dividends_received: Optional[Decimal] = None,
        exit_price_per_token: Optional[Decimal] = None,
        holding_period_years: int = 5,
        use_historical_dividends: bool = False
    ) -> Dict[str, Any]:
        """
        Calcula MOIC (Múltiplo de Inversión).
        
        MOIC = Total Recibido / Inversión Inicial
        
        Returns:
            dict: Resultado del MOIC con desglose
        """
        return self.moic_strategy.calculate(
            total_dividends_received=total_dividends_received,
            exit_price_per_token=exit_price_per_token,
            holding_period_years=holding_period_years,
            use_historical_dividends=use_historical_dividends
        )        