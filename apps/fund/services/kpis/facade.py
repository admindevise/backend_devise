"""
Facade Pattern - Interfaz simplificada para el sistema de KPIs

Esta clase proporciona una API sencilla para acceder a todos los cálculos de KPIs
sin necesidad de conocer la complejidad interna del sistema.
"""

from typing import Dict, Any, Optional, List
from django.utils import timezone
from decimal import Decimal
from apps.fund.models.core import Fund
from .calculator import FundKPICalculator


class FundKPIFacade:
    """
    Facade para simplificar el acceso a cálculos de KPIs
    
    Proporciona métodos de alto nivel para obtener KPIs y reportes
    sin necesidad de instanciar strategies individuales.
    """
    
    def __init__(self, fund:Fund):
        self.fund = fund
        self.calculator = FundKPICalculator(fund)
    
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
        Calcula NOI.
        
        Uso:
        - calculate_noi() → últimos 12 meses
        - calculate_noi(period_year=2024, period_month=6) → junio 2024
        - calculate_noi(months_back=6) → últimos 6 meses
        """
        return self.calculator.calculate_noi(
            period_type=period_type,
            period_year=period_year,
            period_month=period_month,
            period_quarter=period_quarter,
            months_back=months_back,
            include_breakdown=include_breakdown
        )
    
    def get_noi_summary(self, months: int = 12) -> Dict[str, Any]:
        """NOI con análisis de tendencias"""
        return self.calculator.get_noi_summary(months=months)     
    
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
        Calcula el Valor del Fondo basado en Cap Rate objetivo.
        
        Example:
            >>> facade = FundKPIFacade(fund)
            >>> 
            >>> # Valoración con cap rate de mercado (7%)
            >>> valuation = facade.calculate_fund_valuation(target_cap_rate=7.0)
            >>> print(f"Valor del Fondo: ${valuation['fund_value']:,.2f}")
            >>> 
            >>> # Valoración con NOI manual
            >>> valuation = facade.calculate_fund_valuation(
            ...     target_cap_rate=6.5,
            ...     noi_override=5000000
            ... )
        """
        return self.calculator.calculate_fund_valuation(
            target_cap_rate=target_cap_rate,
            months_back=months_back,
            noi_override=noi_override
        )    
    
    # ========================================
    # CAP RATE
    # ========================================
    
    def calculate_cap_rate(self) -> Dict[str, Any]:
        """
        Calcula Capitalization Rate.
        
        Cap Rate = (NOI Anual / Valor del Activo) * 100
        
        Example:
            >>> facade = AssetKPIFacade(asset)
            >>> cap_rate = facade.calculate_cap_rate()
            >>> print(f"Cap Rate: {cap_rate['cap_rate']}%")
            >>> print(f"Interpretación: {cap_rate['interpretation']}")
        
        Returns:
            dict: Resultado del Cap Rate
        """
        return self.calculator.calculate_cap_rate()
    
    # ========================================
    # OUTPUT VALUE
    # ========================================
    
    def calculate_output_value(
        self,
        exit_cap_rate: Decimal,
        current_cap_rate: calculate_cap_rate,
        projected_noi: Optional[Decimal] = None,
        use_projection: bool = False,
        projection_start_year: Optional[int] = None,
        projection_years: int = 5,
        annual_noi_growth_rate: Optional[Decimal] = None,
        growth_rates_by_year: Optional[Dict[int, Decimal]] = None  
    ) -> Dict[str, Any]:
        """
        Calcula el Valor de Salida (Output Value) del fondo.
        
        Output Value = (NOI Proyectado / Cap Rate de Salida) × 100
        """
        return self.calculator.calculate_output_value(
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
        Calcula Flujo de Caja Libre.
        
        Example:
            >>> facade = AssetKPIFacade(asset)
            >>> fcf = facade.calculate_free_cash_flow()
            >>> print(f"FCF: ${fcf['total_fcf_12m']:,.2f}")
            >>> print(f"FCF por Token: ${fcf['fcf_per_token']:,.2f}")
        """
        return self.calculator.calculate_free_cash_flow(
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
        
        Retorno anual en efectivo sobre el capital inicial invertido.
        
        Example:
            >>> facade = AssetKPIFacade(asset)
            >>> coc = facade.calculate_cash_on_cash()
            >>> print(f"Cash on Cash: {coc['cash_on_cash_percentage']:.2f}%")
            >>> print(f"Interpretación: {coc['interpretation']}")
        
        Args:
            months_back: Meses hacia atrás (default: 12)
            include_breakdown: Incluir desglose mensual
            
        Returns:
            dict: Resultado del Cash on Cash
        """
        return self.calculator.calculate_cash_on_cash(
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
        
        Example:
            >>> facade = AssetKPIFacade(asset)
            >>> # Anualizado
            >>> dy = facade.calculate_dividend_yield()
            >>> print(f"Dividend Yield anualizado: {dy['dividend_yield_annualized_percentage']:.2f}%")
            >>> 
            >>> # Período específico
            >>> dy_monthly = facade.calculate_dividend_yield(
            ...     period_year=2024, period_month=12
            ... )
            >>> print(f"Dividend Yield mensual: {dy_monthly['dividend_yield_period_percentage']:.2f}%")
        """
        return self.calculator.calculate_dividend_yield(
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
        
        Example:
            >>> facade = AssetKPIFacade(asset)
            >>> dy_ma = facade.calculate_dividend_yield_moving_average(months_back=12)
            >>> print(f"Promedio: {dy_ma['average_dividend_yield_percentage']:.2f}%")
            >>> print(f"Anualizado: {dy_ma['average_dividend_yield_annualized_percentage']:.2f}%")
            >>> print(f"Desviación estándar: {dy_ma['statistical_metrics']['standard_deviation_percentage']:.2f}%")
            >>> print(f"Tendencia: {dy_ma['trend_analysis']['trend_direction']}")
        """
        return self.calculator.calculate_dividend_yield_moving_average(
            months_back=months_back,
            include_monthly_breakdown=include_monthly_breakdown
        )        
        
    def calculate_irr(
        self,
        investment_id: int,
        exit_price_per_unit: Optional[Decimal] = None,
        exit_date: Optional[timezone.datetime] = None
    ) -> Dict[str, Any]:
        """
        Calcula TIR de una inversión específica del usuario.
        
        Example:
            >>> from apps.fund.models.membership import FundInvestment
            >>> investment = FundInvestment.objects.get(id=123)
            >>> facade = FundKPIFacade(investment.application.fund)
            >>> 
            >>> # TIR con precio actual
            >>> tir = facade.calculate_irr(investment_id=investment.id)
            >>> 
            >>> # TIR con precio de salida proyectado
            >>> tir = facade.calculate_irr(
            ...     investment_id=investment.id,
            ...     exit_price_per_unit=Decimal('1100000')
            ... )
        """
        return self.calculator.calculate_irr(
            investment_id=investment_id,
            exit_price_per_unit=exit_price_per_unit,
            exit_date=exit_date
        )    
        
    # ========================================
    # MOIC
    # ========================================
    
    def calculate_moic(
        self,
        investment_id: int,
        exit_price_per_unit: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Calcula MOIC (Múltiplo de Inversión) de una inversión específica.
        
        Example:
            >>> from apps.fund.models.membership import FundInvestment
            >>> investment = FundInvestment.objects.get(id=5)
            >>> facade = FundKPIFacade(investment.application.fund)
            >>> 
            >>> # MOIC total (distribuciones + valor actual)
            >>> moic = facade.calculate_moic(investment_id=investment.id)
            >>> print(f"MOIC: {moic['moic_metrics']['moic']:.2f}x")
            >>> 
            >>> # MOIC solo distribuciones realizadas
            >>> moic_realized = facade.calculate_moic(
            ...     investment_id=investment.id,
            ...     include_unrealized_value=False
            ... )
        """
        return self.calculator.calculate_moic(
            investment_id=investment_id,
            exit_price_per_unit=exit_price_per_unit
        )