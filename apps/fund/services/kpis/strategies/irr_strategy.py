"""
IRR (Internal Rate of Return) Calculation Strategy para Inversión de Usuario
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from django.utils import timezone
from django.db.models import Q
import numpy as np
from numpy_financial import irr

from ..core.base_strategy import BaseKPIStrategy
from apps.fund.models.core import Fund
from apps.fund.models.membership import FundInvestment
from apps.fund.models.distributions import InvestmentDistributionRecord


class IRRCalculationStrategy(BaseKPIStrategy):
    """
    Strategy para calcular TIR (Tasa Interna de Retorno / IRR) de una inversión específica.
    
    Calcula el retorno anualizado considerando:
    - Inversión inicial
    - Distribuciones reales recibidas (ajustadas por días de tenencia en el primer mes)
    - Valor de salida de los tokens
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
        exit_price_per_unit: Optional[Decimal] = None,
        exit_date: Optional[timezone.datetime] = None
    ) -> Dict[str, Any]:
        """Calcula TIR de una inversión específica del usuario."""
        # 1. Validaciones previas
        prereq = self.validate_prerequisites()
        if not prereq['is_valid']:
            return self._build_error_response('Fund prerequisites not met', prereq['validations'])
        
        # 2. Obtener inversión
        investment = self._get_investment(investment_id)
        if isinstance(investment, dict):
            return investment
        
        try:
            # 3. Preparar parámetros
            params = self._prepare_calculation_parameters(investment, exit_price_per_unit, exit_date)
            
            # 4. Obtener distribuciones filtradas
            distributions = self._get_filtered_distributions(investment, params['investment_date'])
            
            # 5. Construir flujos de caja
            cash_flows_result = self._build_cash_flows(
                investment,
                distributions,
                params
            )
            
            # 6. Calcular TIR
            irr_result = self._calculate_irr(
                cash_flows_result['annual_distributions'],
                params['initial_investment'],
                params['exit_value']
            )
            
            if 'error' in irr_result:
                return {**irr_result, **self._get_fund_info(), 'investment_id': investment.id}
            
            # 7. Construir respuesta completa
            return self._build_success_response(investment, params, cash_flows_result, irr_result)
            
        except Exception as e:
            return {
                'error': f'Error: {str(e)}',
                **self._get_fund_info(),
                'investment_id': investment.id
            }
    
    # ========================================
    # OBTENCIÓN DE DATOS
    # ========================================
    
    def _get_investment(self, investment_id: int):
        """Obtiene la inversión o retorna error"""
        try:
            return FundInvestment.objects.select_related(
                'application__fund',
                'application__user'
            ).get(id=investment_id, application__fund=self.fund)
        except FundInvestment.DoesNotExist:
            return {
                'error': f'Inversión con ID {investment_id} no encontrada',
                **self._get_fund_info(),
                'investment_id': investment_id
            }
    
    def _get_filtered_distributions(self, investment, investment_date):
        """Obtiene distribuciones posteriores a la fecha de inversión"""
        return InvestmentDistributionRecord.objects.filter(
            investment=investment
        ).filter(
            Q(distribution_period__period_year__gt=investment_date.year) |
            Q(distribution_period__period_year=investment_date.year, 
              distribution_period__period_month__gte=investment_date.month)
        ).select_related('distribution_period').order_by(
            'distribution_period__period_year',
            'distribution_period__period_month'
        )
    
    # ========================================
    # PREPARACIÓN DE PARÁMETROS
    # ========================================
    
    def _prepare_calculation_parameters(self, investment, exit_price_per_unit, exit_date):
        """Prepara parámetros de cálculo"""
        initial_investment = investment.final_invested_amount or Decimal('0.00')
        
        if initial_investment == 0:
            raise ValueError('Inversión inicial es cero o inválida')
        
        investment_date = investment.created_at or timezone.now()
        exit_date = exit_date or timezone.now()
        
        if exit_price_per_unit is None:
            exit_price_per_unit = self.fund.price_per_unit
        else:
            exit_price_per_unit = Decimal(str(exit_price_per_unit))
        
        exit_value = Decimal(str(investment.units_owned)) * exit_price_per_unit
        
        return {
            'initial_investment': initial_investment,
            'investment_date': investment_date,
            'exit_date': exit_date,
            'exit_price_per_unit': exit_price_per_unit,
            'exit_value': exit_value,
            'units_owned': investment.units_owned
        }
    
    # ========================================
    # CONSTRUCCIÓN DE FLUJOS DE CAJA
    # ========================================
    
    def _build_cash_flows(self, investment, distributions, params):
        """Construye flujos de caja con ajustes"""
        cash_flows_data = []
        
        # Inversión inicial
        cash_flows_data.append({
            'date': params['investment_date'],
            'cash_flow': -params['initial_investment'],
            'original_amount': -params['initial_investment'],
            'type': 'investment',
            'description': 'Inversión inicial',
            'days_held_in_period': 0,
            'days_in_month': None,
            'holding_fraction': 0
        })
        
        # Procesar distribuciones
        distributions_result = self._process_distributions(distributions, params)
        cash_flows_data.extend(distributions_result['cash_flows'])
        
        # Salida
        cash_flows_data.append({
            'date': params['exit_date'],
            'cash_flow': params['exit_value'],
            'original_amount': params['exit_value'],
            'type': 'exit',
            'description': f"Valor de salida ({params['units_owned']} tokens × ${float(params['exit_price_per_unit']):,.2f})",
            'days_held_in_period': None,
            'days_in_month': None,
            'holding_fraction': 1.0
        })
        
        # Añadir períodos de tiempo
        cash_flows_with_periods = self._add_time_periods(cash_flows_data, params['investment_date'])
        
        # Agrupar por año
        annual_distributions = self._group_by_year(
            distributions_result['distributions_with_adjustments'],
            params['investment_date'],
            params['exit_date']
        )
        
        return {
            'cash_flows_detailed': cash_flows_with_periods,
            'total_distributions': distributions_result['total_distributions'],
            'distributions_with_adjustments': distributions_result['distributions_with_adjustments'],
            'annual_distributions': annual_distributions
        }
    
    def _process_distributions(self, distributions, params):
        """Procesa distribuciones con ajuste solo en primer mes"""
        total_distributions = Decimal('0.00')
        distributions_with_adjustments = []
        cash_flows = []
        
        investment_date = params['investment_date']
        exit_date = params['exit_date']
        
        for dist in distributions:
            distribution_amount = dist.net_distribution_amount_cop or Decimal('0.00')
            
            if distribution_amount <= 0:
                continue
            
            dist_date = dist.created_at or timezone.now()
            
            if dist_date < investment_date:
                continue
            
            period_year = dist.distribution_period.period_year
            period_month = dist.distribution_period.period_month
            
            # ✅ Determinar si es primer mes
            is_first_month = (
                period_year == investment_date.year and 
                period_month == investment_date.month
            )
            
            if is_first_month:
                # ✅ Ajustar por días
                dist_data = self._create_adjusted_distribution(
                    dist_date,
                    distribution_amount,
                    investment_date,
                    period_year,
                    period_month,
                    exit_date
                )
            else:
                # ✅ Mes completo
                dist_data = self._create_full_distribution(
                    dist_date,
                    distribution_amount,
                    period_year,
                    period_month
                )
            
            if dist_data:
                distributions_with_adjustments.append(dist_data)
                cash_flows.append(dist_data)
                total_distributions += dist_data['cash_flow']
        
        return {
            'total_distributions': total_distributions,
            'distributions_with_adjustments': distributions_with_adjustments,
            'cash_flows': cash_flows
        }
    
    def _create_adjusted_distribution(self, dist_date, amount, investment_date, year, month, exit_date):
        """Crea distribución ajustada por días (primer mes)"""
        days_in_month = self._get_days_in_month(year, month)
        days_held = self._calculate_days_held(investment_date, year, month, exit_date)
        
        if days_held == 0:
            return None
        
        fraction = days_held / days_in_month if days_in_month > 0 else 1.0
        adjusted = amount * Decimal(str(fraction))
        
        return {
            'date': dist_date,
            'cash_flow': adjusted,
            'original_distribution': amount,
            'type': 'distribution',
            'description': f'Distribución {year}-{month:02d} (proporcional)',
            'period_year': year,
            'period_month': month,
            'days_in_month': days_in_month,
            'days_held': days_held,
            'holding_fraction': fraction,
            'is_first_month': True,
            'is_full_month': False,
            'adjustment_reason': f'Inversión realizada el día {investment_date.day}'
        }
    
    def _create_full_distribution(self, dist_date, amount, year, month):
        """Crea distribución de mes completo"""
        return {
            'date': dist_date,
            'cash_flow': amount,
            'original_distribution': amount,
            'type': 'distribution',
            'description': f'Distribución {year}-{month:02d}',
            'period_year': year,
            'period_month': month,
            'days_in_month': None,
            'days_held': None,
            'holding_fraction': 1.0,
            'is_first_month': False,
            'is_full_month': True,
            'adjustment_reason': None
        }
    
    def _add_time_periods(self, cash_flows, base_date):
        """Agrega años fraccionados desde la inversión"""
        return [
            {
                **cf,
                'years_from_start': (cf['date'] - base_date).days / 365.25
            }
            for cf in cash_flows
        ]
    
    def _group_by_year(self, distributions, investment_date, exit_date):
        """Agrupa distribuciones por año"""
        total_years = (exit_date - investment_date).days / 365.25
        holding_years = int(np.ceil(total_years))
        
        annual_distributions = [Decimal('0.00')] * holding_years
        
        for dist in distributions:
            year_index = int((dist['date'] - investment_date).days / 365.25)
            
            if 0 <= year_index < holding_years:
                annual_distributions[year_index] += dist['cash_flow']
        
        return annual_distributions
    
    # ========================================
    # CÁLCULO DE TIR
    # ========================================
    
    def _calculate_irr(self, annual_distributions, initial_investment, exit_value):
        """Calcula TIR usando numpy"""
        cash_flows = [-float(initial_investment)]
        
        for year_idx, annual_dist in enumerate(annual_distributions):
            if year_idx < len(annual_distributions) - 1:
                cash_flows.append(float(annual_dist))
            else:
                cash_flows.append(float(annual_dist + exit_value))
        
        try:
            irr_decimal = irr(cash_flows)
            irr_percentage = irr_decimal * 100
            
            if np.isnan(irr_percentage) or np.isinf(irr_percentage):
                return {'error': 'TIR no convergió'}
            
            return {
                'irr_decimal': float(irr_decimal),
                'irr_percentage': float(irr_percentage),
                'cash_flows_simple': cash_flows
            }
        except Exception as e:
            return {'error': f'Error calculando TIR: {str(e)}'}
    
    # ========================================
    # CONSTRUCCIÓN DE RESPUESTAS
    # ========================================
    
    def _build_success_response(self, investment, params, cash_flows_result, irr_result):
        """Construye respuesta exitosa"""
        total_years = (params['exit_date'] - params['investment_date']).days / 365.25
        capital_gain = params['exit_value'] - params['initial_investment']
        total_return = cash_flows_result['total_distributions'] + capital_gain
        moic = (cash_flows_result['total_distributions'] + params['exit_value']) / params['initial_investment']
        roi_percentage = (total_return / params['initial_investment']) * 100
        
        return {
            **self._get_fund_info(),
            'investment_info': {
                'investment_id': investment.id,
                'user_id': investment.application.user.id,
                'user_email': investment.application.user.email,
                'units_owned': params['units_owned'],
                'investment_date': params['investment_date'].isoformat(),
                'exit_date': params['exit_date'].isoformat(),
                'holding_period_days': (params['exit_date'] - params['investment_date']).days,
                'holding_period_years': round(total_years, 2)
            },
            'irr_percentage': irr_result['irr_percentage'],
            'irr_decimal': irr_result['irr_decimal'],
            'investment_parameters': {
                'initial_investment': float(params['initial_investment']),
                'total_distributions_received': float(cash_flows_result['total_distributions']),
                'total_distributions_original': float(sum(
                    d['original_distribution'] for d in cash_flows_result['distributions_with_adjustments']
                )),
                'exit_price_per_unit': float(params['exit_price_per_unit']),
                'exit_value_total': float(params['exit_value'])
            },
            'cash_flows_detailed': [
                {
                    'date': cf['date'].isoformat(),
                    'years_from_start': round(cf['years_from_start'], 2),
                    'cash_flow': float(cf['cash_flow']),
                    'original_amount': float(cf.get('original_distribution', cf.get('original_amount', cf['cash_flow']))),
                    'type': cf['type'],
                    'description': cf['description'],
                    'days_held_in_period': cf.get('days_held'),
                    'days_in_month': cf.get('days_in_month'),
                    'holding_fraction': round(cf.get('holding_fraction', 1.0), 4) if cf.get('holding_fraction') is not None else None
                }
                for cf in cash_flows_result['cash_flows_detailed']
            ],
            'cash_flows_simple': {
                'period_0_investment': irr_result['cash_flows_simple'][0],
                'annual_cash_flows': irr_result['cash_flows_simple'][1:],
                'all_cash_flows': irr_result['cash_flows_simple']
            },
            'return_metrics': {
                'total_distributions_received': float(cash_flows_result['total_distributions']),
                'capital_gain_loss': float(capital_gain),
                'total_return': float(total_return),
                'moic': float(moic),
                'roi_percentage': float(roi_percentage),
                'distributions_count': len(cash_flows_result['distributions_with_adjustments'])
            },
            'annual_breakdown': self._build_annual_breakdown(
                cash_flows_result['annual_distributions'],
                params['exit_value'],
                irr_result['irr_decimal']
            ),
            'interpretation': self._interpret_irr(irr_result['irr_percentage']),
            'performance_level': self._get_performance_level(irr_result['irr_percentage']),
            'calculation_date': timezone.now().isoformat(),
            'calculation_method': 'numpy_financial.irr con ajuste por días (solo primer mes)',
            'data_source': 'historical_real_distributions_adjusted'
        }
    
    def _build_error_response(self, error_message, validations=None):
        """Construye respuesta de error"""
        response = {'error': error_message, **self._get_fund_info()}
        if validations:
            response['validations'] = validations
        return response
    
    def _build_annual_breakdown(self, annual_distributions, exit_value, irr_decimal):
        """Desglose anual"""
        breakdown = []
        cumulative = Decimal('0.00')
        
        for year_idx, annual_dist in enumerate(annual_distributions):
            year_number = year_idx + 1
            is_last = (year_idx == len(annual_distributions) - 1)
            
            cash_flow = annual_dist + exit_value if is_last else annual_dist
            exit_component = exit_value if is_last else Decimal('0.00')
            cumulative += annual_dist
            
            breakdown.append({
                'year': year_number,
                'cash_flow': float(cash_flow),
                'cash_flow_type': 'distributions_and_exit' if is_last else 'distributions',
                'distributions_component': float(annual_dist),
                'exit_value_component': float(exit_component),
                'cumulative_distributions': float(cumulative),
                'present_value': float(cash_flow) / ((1 + irr_decimal) ** year_number)
            })
        
        return breakdown
    
    # ========================================
    # UTILIDADES
    # ========================================
    
    def _get_days_in_month(self, year: int, month: int) -> int:
        """Días en un mes"""
        import calendar
        return calendar.monthrange(year, month)[1]
    
    def _calculate_days_held(self, investment_date, year, month, exit_date) -> int:
        """Calcula días de tenencia en un mes"""
        period_start = timezone.datetime(year, month, 1, tzinfo=investment_date.tzinfo)
        days_in_month = self._get_days_in_month(year, month)
        period_end = timezone.datetime(year, month, days_in_month, 23, 59, 59, tzinfo=investment_date.tzinfo)
        
        effective_start = max(investment_date, period_start)
        effective_end = min(exit_date, period_end)
        
        if effective_start > period_end or effective_end < period_start:
            return 0
        
        return max(0, (effective_end.date() - effective_start.date()).days + 1)
    
    def _interpret_irr(self, irr: float) -> str:
        """Interpretación del TIR"""
        if irr >= 15:
            return f"Excelente: TIR de {irr:.2f}%"
        elif irr >= 10:
            return f"Muy bueno: TIR de {irr:.2f}%"
        elif irr >= 7:
            return f"Bueno: TIR de {irr:.2f}%"
        elif irr >= 5:
            return f"Moderado: TIR de {irr:.2f}%"
        elif irr > 0:
            return f"Bajo: TIR de {irr:.2f}%"
        else:
            return f"Negativo: TIR de {irr:.2f}%"
    
    def _get_performance_level(self, irr: float) -> str:
        """Nivel de desempeño"""
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