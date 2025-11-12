"""
Facade Pattern - Interfaz simplificada para el sistema de KPIs

Esta clase proporciona una API sencilla para acceder a todos los cálculos de KPIs
sin necesidad de conocer la complejidad interna del sistema.
"""

from typing import Dict, Any, Optional, List
from decimal import Decimal
from apps.asset.models.core import Asset
from .calculator import FundKPICalculator


class FundKPIFacade:
    """
    Facade para simplificar el acceso a cálculos de KPIs
    
    Proporciona métodos de alto nivel para obtener KPIs y reportes
    sin necesidad de instanciar strategies individuales.
    """
    
    def __init__(self, asset: Asset):
        self.asset = asset
        self.calculator = FundKPICalculator(asset)
    
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
        projected_noi: Optional[Decimal] = None,
        exit_cap_rate: Optional[Decimal] = None,
        projection_years: int = 5,
        annual_noi_growth_rate: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Calcula el Valor de Salida (Output Value) del activo.
        
        Precio estimado al que se podrá vender el activo en el futuro.
        
        Args:
            projected_noi: NOI proyectado al momento de salida
            exit_cap_rate: Cap Rate de salida esperado
            projection_years: Años hacia adelante para proyección
            annual_noi_growth_rate: Tasa de crecimiento anual del NOI
            
        Returns:
            dict: Resultado del Output Value
        """
        return self.calculator.calculate_output_value(
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
        period_type: str = 'monthly',
        period_year: Optional[int] = None,
        period_month: Optional[int] = None,
        period_quarter: Optional[int] = None,
        calculate_annualized: bool = True
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
        annual_dividends_per_token: Optional[Decimal] = None,
        exit_price_per_token: Optional[Decimal] = None,
        holding_period_years: int = 5,
        use_historical_dividends: bool = False
    ) -> Dict[str, Any]:
        """
        Calcula TIR (Tasa Interna de Retorno).
        
        Example:
            >>> facade = AssetKPIFacade(asset)
            >>> # Con parámetros manuales
            >>> irr = facade.calculate_irr(
            ...     annual_dividends_per_token=Decimal('400'),
            ...     exit_price_per_token=Decimal('4600'),
            ...     holding_period_years=5
            ... )
            >>> print(f"TIR: {irr['irr_percentage']:.2f}%")
            >>> 
            >>> # Con datos históricos
            >>> irr_hist = facade.calculate_irr(
            ...     use_historical_dividends=True,
            ...     holding_period_years=5
            ... )
        """
        return self.calculator.calculate_irr(
            annual_dividends_per_token=annual_dividends_per_token,
            exit_price_per_token=exit_price_per_token,
            holding_period_years=holding_period_years,
            use_historical_dividends=use_historical_dividends
        )        
        
    # ========================================
    # MOIC
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
        
        Example:
            >>> facade = AssetKPIFacade(asset)
            >>> # Con parámetros manuales
            >>> moic = facade.calculate_moic(
            ...     total_dividends_received=Decimal('2000'),
            ...     exit_price_per_token=Decimal('4600'),
            ...     holding_period_years=5
            ... )
            >>> print(f"MOIC: {moic['moic']:.2f}x")
            >>> 
            >>> # Con datos históricos
            >>> moic_hist = facade.calculate_moic(
            ...     use_historical_dividends=True,
            ...     holding_period_years=5
            ... )
        """
        return self.calculator.calculate_moic(
            total_dividends_received=total_dividends_received,
            exit_price_per_token=exit_price_per_token,
            holding_period_years=holding_period_years,
            use_historical_dividends=use_historical_dividends
        )        