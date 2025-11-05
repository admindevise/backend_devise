from decimal import Decimal
from typing import Dict, List, Tuple
from django.utils import timezone
from django.db.models import Sum, Q
from collections import defaultdict


class DividendYieldCalculator:
    """
    Calculadora de Dividend Yield con funciones modulares para análisis histórico.
    """
    
    def __init__(self, fund, user=None):
        """
        Inicializa el calculador.
        
        Args:
            fund: Instancia del fondo
            user: Usuario opcional para cálculo personalizado
        """
        self.fund = fund
        self.user = user
    
    # ==========================================
    # FUNCIONES AUXILIARES
    # ==========================================
    
    def _get_investments(self):
        """
        Obtiene las inversiones del fondo o usuario.
        
        Returns:
            QuerySet: Inversiones ordenadas por fecha
        """
        from apps.fund.models.membership import FundInvestment
        
        query = FundInvestment.objects.select_related(
            'application__fund', 'application__user'
        ).filter(application__fund=self.fund)
        
        if self.user:
            query = query.filter(application__user=self.user)
        
        return query.order_by('created_at')
    
    def _get_distribution_periods(self):
        """
        Obtiene los períodos de distribución del fondo.
        
        Returns:
            QuerySet: Períodos ordenados cronológicamente
        """
        from apps.fund.models.distributions import DistributionPeriod
        
        return DistributionPeriod.objects.filter(
            fund=self.fund,
            #status__in=[
                #DistributionPeriod.DistributionStatus.COMPLETED,
                #DistributionPeriod.DistributionStatus.PROCESSING,
                #DistributionPeriod.DistributionStatus.APPROVED
            #]
        ).order_by('period_year', 'period_month')
    
    def _index_investments_by_date(self, investments):
        """
        Crea un índice de inversiones por fecha para búsqueda rápida.
        
        Args:
            investments: QuerySet de inversiones
            
        Returns:
            dict: Diccionario con fecha como clave y lista de inversiones como valor
        """
        investments_by_date = defaultdict(list)
        
        for inv in investments:
            inv_date = inv.created_at.date()
            investments_by_date[inv_date].append({
                'investment': inv,
                'amount': inv.final_invested_amount or Decimal('0.00'),
                'units': inv.units_owned,
                'counted': False  # Flag para evitar contar dos veces
            })
        
        return investments_by_date
    
    def _calculate_accumulated_investment_for_period(
        self, 
        period_date, 
        investments_index, 
        previous_accumulated
    ) -> Tuple[Decimal, Decimal, int]:
        """
        Calcula la inversión acumulada hasta un período específico.
        
        Args:
            period_date: Fecha del período
            investments_index: Índice de inversiones por fecha
            previous_accumulated: Inversión acumulada del período anterior
            
        Returns:
            tuple: (inversión_acumulada, nuevas_inversiones, cantidad_inversiones)
        """
        accumulated = previous_accumulated
        new_investments = Decimal('0.00')
        investments_count = 0
        
        # Recorrer todas las inversiones
        for inv_date, inv_list in investments_index.items():
            # Si la inversión fue hecha antes o en la fecha del período
            if inv_date <= period_date:
                for inv_data in inv_list:
                    # Solo contar si no ha sido contada previamente
                    if not inv_data['counted']:
                        accumulated += inv_data['amount']
                        new_investments += inv_data['amount']
                        investments_count += 1
                        inv_data['counted'] = True
        
        return accumulated, new_investments, investments_count
    
    def _get_period_distributions(self, period, investments):
        """
        Obtiene las distribuciones de un período específico.
        
        Args:
            period: Período de distribución
            investments: QuerySet de inversiones
            
        Returns:
            Decimal: Total de distribuciones del período
        """
        from apps.fund.models.distributions import InvestmentDistributionRecord
        
        query = InvestmentDistributionRecord.objects.filter(
            distribution_period=period,
            #payment_status__in=[
            #    InvestmentDistributionRecord.PaymentStatus.PAID,
            #    InvestmentDistributionRecord.PaymentStatus.VERIFIED,
            #    InvestmentDistributionRecord.PaymentStatus.PROCESSING
            #]
        )
        
        if self.user:
            query = query.filter(investment__in=investments)
        
        return query.aggregate(total=Sum('net_distribution_amount_cop'))['total'] or Decimal('0.00')
    
    def _calculate_dividend_yield_for_period(
        self, 
        period_distributions, 
        accumulated_investment
    ) -> float:
        """
        Calcula el Dividend Yield para un período específico.
        
        Args:
            period_distributions: Distribuciones del período
            accumulated_investment: Inversión acumulada hasta el período
            
        Returns:
            float: Dividend Yield del período en porcentaje
        """
        if accumulated_investment > 0:
            return float((period_distributions / accumulated_investment) * 100)
        return 0.0
    
    # ==========================================
    # FUNCIÓN PRINCIPAL
    # ==========================================
    
    def calculate_historical_dividend_yield(self) -> Dict[str, any]:
        """
        Calcula el historial completo de inversión acumulada y dividend yield.
        
        Returns:
            dict: Historial período a período con todas las métricas
        """
        try:
            # 1. Obtener datos necesarios
            investments = self._get_investments()
            if not investments.exists():
                return {
                    'error': f'No hay inversiones {"del usuario" if self.user else "en el fondo"}',
                    'fund_id': self.fund.id,
                    'user_id': self.user.id if self.user else None
                }
            
            distribution_periods = self._get_distribution_periods()
            if not distribution_periods.exists():
                return {
                    'error': f'El fondo {self.fund.name} no tiene períodos de distribución',
                    'fund_id': self.fund.id,
                    'user_id': self.user.id if self.user else None
                }
            
            # 2. Preparar estructuras de datos
            investments_index = self._index_investments_by_date(investments)
            period_history = []
            accumulated_investment = Decimal('0.00')
            accumulated_distributions = Decimal('0.00')
            
            # 3. Procesar cada período
            for period in distribution_periods:
                period_data = self._process_period(
                    period=period,
                    investments=investments,
                    investments_index=investments_index,
                    accumulated_investment=accumulated_investment,
                    accumulated_distributions=accumulated_distributions
                )
                
                # Actualizar acumulados
                accumulated_investment = Decimal(str(period_data['accumulated_investment']))
                accumulated_distributions = Decimal(str(period_data['accumulated_distributions']))
                
                period_history.append(period_data)
            
            # 4. Calcular estadísticas globales
            summary = self._calculate_summary_statistics(period_history)
            
            # 5. Construir respuesta final
            return self._build_response(period_history, summary)
            
        except Exception as e:
            return {
                'error': f'Error calculando historial de Dividend Yield: {str(e)}',
                'fund_id': self.fund.id,
                'user_id': self.user.id if self.user else None
            }
    
    def _process_period(
        self, 
        period, 
        investments, 
        investments_index, 
        accumulated_investment, 
        accumulated_distributions
    ) -> Dict[str, any]:
        """
        Procesa un período individual calculando todas sus métricas.
        
        Args:
            period: Período de distribución
            investments: QuerySet de inversiones
            investments_index: Índice de inversiones por fecha
            accumulated_investment: Inversión acumulada del período anterior
            accumulated_distributions: Distribuciones acumuladas del período anterior
            
        Returns:
            dict: Datos completos del período
        """
        # Fecha del período
        period_date = period.payment_date or timezone.now().date()
        
        # Calcular inversión acumulada
        new_accumulated, new_investments, investments_count = self._calculate_accumulated_investment_for_period(
            period_date=period_date,
            investments_index=investments_index,
            previous_accumulated=accumulated_investment
        )
        
        # Obtener distribuciones del período
        period_distributions = self._get_period_distributions(period, investments)
        new_accumulated_distributions = accumulated_distributions + period_distributions
        
        # Calcular Dividend Yields
        period_dividend_yield = self._calculate_dividend_yield_for_period(
            period_distributions=period_distributions,
            accumulated_investment=new_accumulated
        )
        
        cumulative_dividend_yield = self._calculate_dividend_yield_for_period(
            period_distributions=new_accumulated_distributions,
            accumulated_investment=new_accumulated
        )
        
        return {
            'period_id': period.id,
            'period_year': period.period_year,
            'period_month': period.period_month,
            'period_quarter': period.period_quarter,
            'period_display': period.period_display,
            'period_date': period_date.strftime("%Y-%m-%d"),
            'distribution_type': period.get_distribution_type_display(),
            
            # Inversión acumulada
            'accumulated_investment': float(new_accumulated),
            'new_investments_in_period': float(new_investments),
            'investments_count_in_period': investments_count,
            
            # Distribuciones
            'period_distributions': float(period_distributions),
            'accumulated_distributions': float(new_accumulated_distributions),
            
            # Dividend Yield
            'period_dividend_yield_percentage': period_dividend_yield,
            'cumulative_dividend_yield_percentage': cumulative_dividend_yield,
            
            # Métricas adicionales
            'distribution_per_invested_unit': float(period_distributions / new_accumulated) if new_accumulated > 0 else 0.0,
            'total_tokens_in_period': period.total_tokens_outstanding or 0,
            'distribution_per_token': float(period.distribution_per_token or 0)
        }
    
    def _calculate_summary_statistics(self, period_history: List[Dict]) -> Dict[str, any]:
        """
        Calcula estadísticas resumidas del historial completo.
        
        Args:
            period_history: Lista de datos por período
            
        Returns:
            dict: Estadísticas globales
        """
        if not period_history:
            return {}
        
        total_periods = len(period_history)
        
        # Última entrada del historial
        last_period = period_history[-1]
        
        # Calcular promedios
        avg_period_dividend_yield = sum(
            p['period_dividend_yield_percentage'] for p in period_history
        ) / total_periods
        
        # Contar períodos
        periods_with_distributions = len([
            p for p in period_history if p['period_distributions'] > 0
        ])
        periods_with_new_investments = len([
            p for p in period_history if p['new_investments_in_period'] > 0
        ])
        
        # Identificar mejor y peor período
        best_period = max(
            period_history, 
            key=lambda x: x['period_dividend_yield_percentage']
        )
        worst_period = min(
            period_history, 
            key=lambda x: x['period_dividend_yield_percentage']
        )
        
        return {
            'total_periods_analyzed': total_periods,
            'first_period': period_history[0]['period_display'],
            'last_period': last_period['period_display'],
            'total_accumulated_investment': last_period['accumulated_investment'],
            'total_accumulated_distributions': last_period['accumulated_distributions'],
            'overall_dividend_yield_percentage': last_period['cumulative_dividend_yield_percentage'],
            'average_period_dividend_yield_percentage': avg_period_dividend_yield,
            'periods_with_distributions': periods_with_distributions,
            'periods_with_new_investments': periods_with_new_investments,
            'best_period': {
                'period_display': best_period['period_display'],
                'dividend_yield_percentage': best_period['period_dividend_yield_percentage'],
                'distributions': best_period['period_distributions'],
                'date': best_period['period_date']
            },
            'worst_period': {
                'period_display': worst_period['period_display'],
                'dividend_yield_percentage': worst_period['period_dividend_yield_percentage'],
                'distributions': worst_period['period_distributions'],
                'date': worst_period['period_date']
            }
        }
    
    def _build_response(self, period_history: List[Dict], summary: Dict) -> Dict[str, any]:
        """
        Construye la respuesta final estructurada.
        
        Args:
            period_history: Lista de datos por período
            summary: Estadísticas resumidas
            
        Returns:
            dict: Respuesta completa formateada
        """
        return {
            'fund_id': self.fund.id,
            'fund_name': self.fund.name,
            'user_id': self.user.id if self.user else None,
            'user_email': self.user.email if self.user else None,
            'analysis_summary': summary,
            'period_history': period_history,
            'calculation_metadata': {
                'calculation_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                'calculation_type': 'user_specific' if self.user else 'fund_level',
                'formula_dividend_yield': '(Distribuciones del período / Inversión acumulada) × 100',
                'formula_accumulated_investment': 'Σ(Inversiones hasta la fecha del período)',
                'currency': 'COP'
            }
        }


# ==========================================
# FUNCIONES WRAPPER PARA INTEGRACIÓN
# ==========================================

def calculate_accumulated_investment(fund, user=None) -> Dict[str, any]:
    """
    Calcula la inversión acumulada total (simplificada).
    
    Args:
        fund: Instancia del fondo
        user: Usuario opcional
        
    Returns:
        dict: Inversión acumulada total
    """
    calculator = DividendYieldCalculator(fund, user)
    result = calculator.calculate_historical_dividend_yield()
    
    if 'error' in result:
        return result
    
    summary = result['analysis_summary']
    
    return {
        'fund_id': fund.id,
        'fund_name': fund.name,
        'user_id': user.id if user else None,
        'user_email': user.email if user else None,
        'accumulated_investment': summary['total_accumulated_investment'],
        'total_investments_count': summary['periods_with_new_investments'],
        'first_investment_period': summary['first_period'],
        'last_investment_period': summary['last_period'],
        'calculation_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def calculate_dividend_yield_percentage(fund, user=None) -> Dict[str, any]:
    """
    Calcula el Dividend Yield actual (simplificado).
    
    Args:
        fund: Instancia del fondo
        user: Usuario opcional
        
    Returns:
        dict: Dividend Yield actual
    """
    calculator = DividendYieldCalculator(fund, user)
    result = calculator.calculate_historical_dividend_yield()
    
    if 'error' in result:
        return result
    
    summary = result['analysis_summary']
    
    return {
        'fund_id': fund.id,
        'fund_name': fund.name,
        'user_id': user.id if user else None,
        'user_email': user.email if user else None,
        'dividend_yield_percentage': summary['overall_dividend_yield_percentage'],
        'total_distributions': summary['total_accumulated_distributions'],
        'accumulated_investment': summary['total_accumulated_investment'],
        'average_period_dividend_yield': summary['average_period_dividend_yield_percentage'],
        'best_period': summary['best_period'],
        'worst_period': summary['worst_period'],
        'calculation_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    }