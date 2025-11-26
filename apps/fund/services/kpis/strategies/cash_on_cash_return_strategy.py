"""
Cash on Cash Return Calculation Strategy para Fund
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum

from ..core.base_strategy import BaseKPIStrategy
from apps.fund.models.core import Fund
from .free_cash_flow_strategy import FreeCashFlowCalculationStrategy
from ..repositories.operating_data_repository import OperatingDataRepository


class CashOnCashCalculationStrategy(BaseKPIStrategy):
    """
    Strategy para calcular Cash on Cash Return de un fondo.
    
    El retorno anual en efectivo sobre el capital inicial invertido (sin deuda).
    
    Formula:
    Cash on Cash = (Flujo de Caja Libre Anual / Capital Invertido) × 100
    
    Donde:
    - Flujo de Caja Libre Anual: FCF de los últimos 12 meses
    - Capital Invertido: initial_capex + CAPEX de períodos seleccionados
    
    Nota importante:
    - Este es el KPI del FONDO, no de la inversión individual
    - Incluye tanto la inversión inicial como las mejoras/expansiones
    
    Interpretación:
    - CoC > 8%: Excelente retorno en efectivo
    - CoC 5-8%: Buen retorno
    - CoC < 5%: Retorno bajo, revisar estructura
    """
    
    def __init__(self, fund: Fund):
        super().__init__(fund)
        self.fcf_strategy = FreeCashFlowCalculationStrategy(fund)
        self.repository = OperatingDataRepository()
    
    def validate_prerequisites(self) -> Dict[str, bool]:
        """Valida que el fondo tenga los datos necesarios"""
        validations = {
            'fund_exists': self.fund is not None,
            'fund_has_id': bool(self.fund.pk if self.fund else False),
            'fund_is_active': self.fund.status == 'active' if self.fund else False,
            'has_initial_capex': bool(self.fund.initial_capex) if self.fund else False
        }
        
        return {
            'is_valid': all(validations.values()),
            'validations': validations
        }
    
    def calculate(
        self,
        months_back: int = 12,
        include_breakdown: bool = False
    ) -> Dict[str, Any]:
        """
        Calcula Cash on Cash Return del fondo.
        
        Args:
            months_back: Meses hacia atrás para FCF (default: 12)
            include_breakdown: Incluir desglose mensual del FCF
            
        Returns:
            dict: Resultado del Cash on Cash con componentes
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
            # 2. Obtener FCF anual usando FreeCashFlowCalculationStrategy
            fcf_result = self.fcf_strategy.calculate(
                months_back=months_back,
                include_breakdown=include_breakdown
            )
            
            # Validar que el FCF se calculó correctamente
            if 'error' in fcf_result:
                return {
                    'error': f"Error calculando FCF: {fcf_result['error']}",
                    **self._get_fund_info()
                }
            
            fcf_anual = Decimal(str(fcf_result.get('total_fcf_12m', 0)))
            
            # 3. ✅ CAMBIO: Calcular capital invertido = initial_capex + CAPEX de períodos
            
            # 3.1 Obtener initial_capex del modelo Fund
            initial_capex = self.fund.initial_capex or Decimal('0.00')
            
            # 3.2 Obtener CAPEX de los períodos analizados
            # Calcular rango de fechas (misma lógica que FCF)
            from dateutil.relativedelta import relativedelta
            
            current_date = timezone.now()
            
            # Determinar último mes completo
            if current_date.day < 30:
                last_completed_date = current_date.replace(day=1) - timezone.timedelta(days=1)
            else:
                last_completed_date = current_date.replace(day=1)
            
            last_completed_year = last_completed_date.year
            last_completed_month = last_completed_date.month
            
            start_date = last_completed_date - relativedelta(months=months_back - 1)
            start_year = start_date.year
            start_month = start_date.month
            
            # 3.3 Obtener suma de CAPEX de los períodos
            expenses = self.repository.get_expense_range(
                fund=self.fund,
                period_type='monthly',
                start_year=start_year,
                start_month=start_month,
                end_year=last_completed_year,
                end_month=last_completed_month
            )
            
            capex_periodic = expenses.aggregate(total=Sum('capex'))['total'] or Decimal('0.00')
            
            # 3.4 Capital invertido total
            capital_invertido = initial_capex + capex_periodic
            
            # Validar que el capital invertido sea válido
            if capital_invertido <= 0:
                return {
                    'error': 'Capital invertido inválido o cero',
                    **self._get_fund_info(),
                    'initial_capex': float(initial_capex),
                    'capex_periodic': float(capex_periodic),
                    'capital_invertido': float(capital_invertido)
                }
            
            # 4. Calcular Cash on Cash
            # Cash on Cash = (FCF Anual / Capital Invertido) × 100
            cash_on_cash = (fcf_anual / capital_invertido) * 100
            
            # 5. Interpretación del Cash on Cash
            interpretation = self._interpret_cash_on_cash(float(cash_on_cash))
            
            # 6. Métricas adicionales
            # FCF yield (similar a dividend yield pero usando FCF)
            fcf_yield = cash_on_cash  # Es lo mismo en este contexto
            
            # Payback period simple (años para recuperar inversión)
            payback_period = (capital_invertido / fcf_anual) if fcf_anual > 0 else None
            
            result = {
                **self._get_fund_info(),
                
                # Cash on Cash principal
                'cash_on_cash_percentage': float(cash_on_cash),
                'fcf_anual': float(fcf_anual),
                'capital_invertido': float(capital_invertido),
                
                # ✅ NUEVO: Desglose del capital invertido
                'capital_breakdown': {
                    'initial_capex': float(initial_capex),
                    'capex_periodic': float(capex_periodic),
                    'total_capital_invested': float(capital_invertido),
                    'capex_as_percentage_of_initial': float((capex_periodic / initial_capex) * 100) if initial_capex > 0 else 0
                },
                
                # Interpretación
                'interpretation': interpretation,
                'performance_level': self._get_performance_level(float(cash_on_cash)),
                
                # Métricas adicionales
                'additional_metrics': {
                    'fcf_yield_percentage': float(fcf_yield),
                    'payback_period_years': float(payback_period) if payback_period else None,
                    'monthly_fcf_average': float(fcf_anual / 12),
                    'annual_cash_return': float(fcf_anual)
                },
                
                # Componentes del FCF (para contexto)
                'fcf_components': fcf_result.get('fcf_components', {}),
                
                # Metadata
                'calculation_date': timezone.now().isoformat(),
                'period_analyzed': f'{start_year}-{start_month:02d} a {last_completed_year}-{last_completed_month:02d}',
                'months_analyzed': months_back,
                'calculation_note': 'Capital invertido = initial_capex + CAPEX de períodos analizados'
            }
            
            # Agregar información por área si existe
            total_area = getattr(self.fund, 'total_area_m2', None)
            rentable_area = getattr(self.fund, 'rentable_area_m2', None)
            
            if total_area and total_area > 0:
                result['fund_metrics'] = {
                    'total_area_m2': float(total_area),
                    'rentable_area_m2': float(rentable_area) if rentable_area else None,
                    'cash_on_cash_per_m2': float(fcf_anual / total_area),
                    'capital_invested_per_m2': float(capital_invertido / total_area)
                }
            
            # Agregar información por unidad
            total_units = self.fund.amount_tokens or 0
            if total_units > 0:
                result['per_unit_metrics'] = {
                    'total_units_issued': total_units,
                    'fcf_per_unit': float(fcf_anual / Decimal(str(total_units))),
                    'capital_invested_per_unit': float(capital_invertido / Decimal(str(total_units)))
                }
            
            # Agregar desglose si se solicitó
            if include_breakdown and 'monthly_breakdown' in fcf_result:
                result['monthly_breakdown'] = fcf_result['monthly_breakdown']
            
            return result
            
        except Exception as e:
            return {
                'error': f'Error calculando Cash on Cash: {str(e)}',
                **self._get_fund_info()
            }
    
    def _interpret_cash_on_cash(self, coc: float) -> str:
        """
        Interpreta el Cash on Cash según rangos estándar.
        
        Args:
            coc: Valor del Cash on Cash en porcentaje
            
        Returns:
            str: Interpretación textual
        """
        if coc >= 10:
            return "Excelente retorno en efectivo: El fondo genera flujo de caja significativo sobre el capital invertido."
        elif coc >= 7:
            return "Muy buen retorno: El fondo produce flujo de caja sólido, típico de fondos bien gestionados."
        elif coc >= 5:
            return "Buen retorno: El fondo genera flujo de caja aceptable, en línea con mercado."
        elif coc >= 3:
            return "Retorno moderado: El fondo genera algo de efectivo, pero hay oportunidad de mejora."
        elif coc > 0:
            return "Retorno bajo: El fondo genera poco efectivo relativo al capital invertido. Revisar eficiencia operativa."
        else:
            return "Sin retorno o negativo: El fondo no genera efectivo o requiere inyección de capital."
    
    def _get_performance_level(self, coc: float) -> str:
        """
        Determina el nivel de desempeño basado en Cash on Cash.
        
        Args:
            coc: Valor del Cash on Cash en porcentaje
            
        Returns:
            str: 'excellent', 'very_good', 'good', 'moderate', 'poor', 'negative'
        """
        if coc >= 10:
            return "excellent"
        elif coc >= 7:
            return "very_good"
        elif coc >= 5:
            return "good"
        elif coc >= 3:
            return "moderate"
        elif coc > 0:
            return "poor"
        else:
            return "negative"