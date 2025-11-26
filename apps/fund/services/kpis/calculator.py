"""
FundKPICalculator - Orquestador que usa Strategies
"""

from typing import Dict, Any, Optional
from django.utils import timezone
from decimal import Decimal
from apps.fund.models.core import Fund
from apps.fund.services.kpis.core.exceptions import FundKPIError

from apps.fund.services.kpis.strategies.noi_strategy import NOICalculationStrategy
from apps.fund.services.kpis.strategies.cap_rate_strategy import CapRateCalculationStrategy
from apps.fund.services.kpis.strategies.output_value_strategy import OutputValueCalculationStrategy
from apps.fund.services.kpis.strategies.free_cash_flow_strategy import FreeCashFlowCalculationStrategy
from apps.fund.services.kpis.strategies.cash_on_cash_return_strategy import CashOnCashCalculationStrategy
from apps.fund.services.kpis.strategies.dividend_yield_strategy import DividendYieldCalculationStrategy
from apps.fund.services.kpis.strategies.dividend_yield_moving_strategy import DividendYieldMovingAverageStrategy
from apps.fund.services.kpis.strategies.irr_strategy import IRRCalculationStrategy
from apps.fund.services.kpis.strategies.moic_strategy import MOICCalculationStrategy
from apps.fund.services.kpis.strategies.fund_valuation_strategy import FundValuationCalculationStrategy


class FundKPICalculator:
    """
    Calculador principal que orquesta Strategies de KPIs.
    
    Delega los cálculos a strategies especializadas.
    """
    
    def __init__(self, fund: Fund):
        if not fund:
            raise FundKPIError("Fund is required")
        
        if not fund.pk:
            raise FundKPIError("Fund must be saved")
        
        self.fund = fund
        
        # Instanciar strategies
        self.noi_strategy = NOICalculationStrategy(fund)
        self.cap_rate_strategy = CapRateCalculationStrategy(fund)
        self.output_value_strategy = OutputValueCalculationStrategy(fund)
        self.fcf_strategy = FreeCashFlowCalculationStrategy(fund)
        self.coc_strategy = CashOnCashCalculationStrategy(fund)
        self.dividend_yield_strategy = DividendYieldCalculationStrategy(fund)
        self.dividend_yield_ma_strategy = DividendYieldMovingAverageStrategy(fund)
        self.irr_strategy = IRRCalculationStrategy(fund)
        self.moic_strategy = MOICCalculationStrategy(fund)
        self.fund_valuation_strategy = FundValuationCalculationStrategy(fund)
    
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
    # FUND VALUATION
    # ========================================        
        
    def calculate_fund_valuation(
        self,
        target_cap_rate: Decimal,
        months_back: int = 12,
        noi_override: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Calcula el Valor del Fondo basado en NOI y Cap Rate.
        
        Valor del Fondo = (NOI Anual / Cap Rate) × 100
        
        Args:
            target_cap_rate: Cap Rate objetivo en porcentaje
            months_back: Meses hacia atrás para NOI (default: 12)
            noi_override: NOI manual (opcional)
            
        Returns:
            dict: Resultado de la valoración del fondo
        """
        return self.fund_valuation_strategy.calculate(
            target_cap_rate=target_cap_rate,
            months_back=months_back,
            noi_override=noi_override
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
        exit_cap_rate: Decimal, 
        current_cap_rate: Decimal,
        projected_noi: Optional[Decimal] = None,
        use_projection: bool = False,
        projection_start_year: Optional[int] = None,
        projection_years: int = 5,
        annual_noi_growth_rate: Optional[Decimal] = None,
        growth_rates_by_year: Optional[Dict[int, Decimal]] = None
    ) -> Dict[str, Any]:
        """
        Calcula el Valor de Salida del fondo.
        
        Output Value = (NOI Proyectado / Cap Rate de Salida) × 100
        
        Args:
            exit_cap_rate: Cap Rate de salida esperado (REQUERIDO)
            projected_noi: NOI proyectado manual (opcional)
            use_projection: Si usar proyección con crecimiento (default: False)
            projection_start_year: Año base para proyección (opcional)
            projection_years: Años a proyectar (default: 5)
            annual_noi_growth_rate: Tasa de crecimiento uniforme %
            growth_rates_by_year: Dict con tasas por año específico
            
        Returns:
            dict: Resultado del Output Value con métricas de retorno
        """
        return self.output_value_strategy.calculate(
            exit_cap_rate=exit_cap_rate,
            current_cap_rate=current_cap_rate,
            projected_noi=projected_noi,
            use_projection=use_projection,
            projection_start_year=projection_start_year,
            projection_years=projection_years,
            annual_noi_growth_rate=annual_noi_growth_rate,
            growth_rates_by_year=growth_rates_by_year
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
        investment_id: int,
        period_type: str = 'monthly',
        period_year: Optional[int] = None,
        period_month: Optional[int] = None,
        period_quarter: Optional[int] = None,
        months_back: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Calcula Dividend Yield del activo.
        
        Dividend Yield = (Dividendo por Token / Valor Compra Token) × 100
        
        Returns:
            dict: Resultado del Dividend Yield
        """
        return self.dividend_yield_strategy.calculate(
            investment_id=investment_id,
            period_type=period_type,
            period_year=period_year,
            period_month=period_month,
            period_quarter=period_quarter,
            months_back=months_back,
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
        investment_id: int,
        exit_price_per_unit: Optional[Decimal] = None,
        exit_date: Optional[timezone.datetime] = None
    ) -> Dict[str, Any]:
        """
        Calcula TIR (Tasa Interna de Retorno / IRR) de una inversión específica.
        
        Args:
            investment_id: ID de FundInvestment
            exit_price_per_unit: Precio de salida por unidad (opcional)
            exit_date: Fecha de salida (opcional)
        
        Returns:
            dict: Resultado del TIR con flujos de caja
        """
        return self.irr_strategy.calculate(
            investment_id=investment_id,
            exit_price_per_unit=exit_price_per_unit,
            exit_date=exit_date
        )
            
    # ========================================
    # MOIC (MÚLTIPLO DE INVERSIÓN)
    # ========================================
    
    def calculate_moic(
        self,
        investment_id: int,
        exit_price_per_unit: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Calcula MOIC (Múltiplo de Inversión) de una inversión específica.
        
        Args:
            investment_id: ID de FundInvestment
            include_unrealized_value: Incluir valor actual no realizado de tokens
            use_current_price: Usar precio actual vs precio de compra para valoración
        
        Returns:
            dict: Resultado del MOIC con desglose
        """
        return self.moic_strategy.calculate(
            investment_id=investment_id,
            exit_price_per_unit=exit_price_per_unit
        )