from datetime import timedelta
from decimal import Decimal
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone

from apps.fund.models.membership import FundInvestment


class InvestmentTrendService:
    """Servicio para calcular tendencias de inversiones"""
    
    PERIOD_DAYS = {
        '1M': 30,
        '3M': 90,
        '6M': 180,
        '1Y': 365,
    }
    
    @staticmethod
    def get_investment_trend(fund_id=None, time_period='1M'):
        """
        Calcula las tendencias de inversión para un período dado
        
        Args:
            fund_id: ID del fondo (opcional)
            time_period: Período de tiempo ('1M', '3M', '6M', '1Y')
            
        Returns:
            dict: Datos de tendencia formateados
        """
        days = InvestmentTrendService.PERIOD_DAYS.get(time_period, 30)
        start_date = timezone.now() - timedelta(days=days)
        
        # Filtrar inversiones usando application__fund
        queryset = FundInvestment.objects.filter(created_at__gte=start_date)
        if fund_id:
            queryset = queryset.filter(application__fund_id=fund_id)  # ✅ CORRECCIÓN
        
        # Calcular métricas
        stats = queryset.aggregate(
            total_investments=Count('id'),
            total_amount=Sum('final_invested_amount'),
        )
        
        average_investment = (
            stats['total_amount'] / stats['total_investments']
            if stats['total_investments'] and stats['total_amount']
            else Decimal('0')
        )
        
        # Calcular crecimiento
        growth_percentage = InvestmentTrendService._calculate_growth(
            queryset, start_date, days, fund_id
        )
        
        # Agrupar datos por período
        period_data = InvestmentTrendService._group_by_period(
            queryset, time_period
        )
        
        return {
            'fund_id': fund_id,
            'time_period': time_period,
            'total_investments': stats['total_investments'] or 0,
            'total_amount': str(stats['total_amount'] or 0),
            'average_investment': str(average_investment),
            'growth_percentage': round(float(growth_percentage), 2),
            'period_data': period_data,
        }
    
    @staticmethod
    def _calculate_growth(queryset, start_date, days, fund_id):
        """Calcula el porcentaje de crecimiento comparado con período anterior"""
        previous_start = start_date - timedelta(days=days)
        previous_queryset = FundInvestment.objects.filter(
            created_at__gte=previous_start,
            created_at__lt=start_date
        )
        
        # Usar application__fund_id
        if fund_id:
            previous_queryset = previous_queryset.filter(application__fund_id=fund_id)
        
        previous_total = previous_queryset.aggregate(
            total=Sum('final_invested_amount')
        )['total'] or Decimal('0')
        
        current_total = queryset.aggregate(
            total=Sum('final_invested_amount')
        )['total'] or Decimal('0')
        
        if previous_total > 0:
            return ((current_total - previous_total) / previous_total) * 100
        return Decimal('0')
    
    @staticmethod
    def _group_by_period(queryset, time_period):
        """Agrupa las inversiones por período (semanal o mensual)"""
        if time_period == '1M':
            # Agrupar por semana
            grouped = queryset.annotate(
                period=TruncWeek('created_at')
            )
        else:
            # Agrupar por mes
            grouped = queryset.annotate(
                period=TruncMonth('created_at')
            )
        
        period_data = grouped.values('period').annotate(
            investments_count=Count('id'),
            total_amount=Sum('final_invested_amount')
        ).order_by('period')
        
        return [
            {
                'period': item['period'].strftime('%Y-%m-%d'),
                'month': item['period'].strftime('%B') if time_period != '1M' else None,
                'investments_count': item['investments_count'],
                'total_amount': str(item['total_amount']),
            }
            for item in period_data
        ]