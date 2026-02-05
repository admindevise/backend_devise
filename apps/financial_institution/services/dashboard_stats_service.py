from django.core.cache import cache
from django.db.models import Count, Q, Sum

from apps.fund.models.core import Fund
from apps.user.models import User
from apps.fund.models.membership import FundInvestment, InvestorContract
from apps.trading.models.core_models import PurchaseOrder, SalesOrder

class DashboardStatsService:
    """Servicio para obtener estadísticas del dashboard de instituciones financieras"""
    
    CACHE_KEY = "dashboard_stats"
    CACHE_TIMEOUT = 300  # 5 minutos
    
    @classmethod
    def get_dashboard_stats(cls, use_cache=True):
        """
        Obtiene estadísticas del dashboard financiero, usando caché si es necesario.
        """

        if use_cache:
            cached = cache.get(cls.CACHE_KEY)
            if cached:
                print("Dashboard stats from cache")
                return cached
        
        try: 
        # Calcular estadísticas
            stats = {
                'total_funds': cls._get_total_funds(),
                'active_funds': cls._get_active_funds(),
                'total_transactions': cls._get_total_transactions(),
                'total_volume': cls._get_total_volume(),
                'pending_approvals': cls._get_pending_approvals(),
                'active_investors': cls._get_active_investors(),
                'active_investments': cls._get_active_investments(),
                'investors_without_investments': cls._get_investors_without_investments(),
                'pending_investor_approvals': cls._get_pending_investor_approvals(),
            }
            # Guardar en caché
            if use_cache:
                cache.set(cls.CACHE_KEY, stats, cls.CACHE_TIMEOUT)
                print("Dashboard stats cached")
            return stats
        except Exception as e:
            print(f"Error calculating dashboard stats: {type(e).__name__}: {e}")
            raise
    
    @classmethod
    def _get_total_funds(cls):
        return Fund.objects.count()
    
    @classmethod
    def _get_active_funds(cls):
        return Fund.objects.filter(status='active').count()
    
    @classmethod
    def _get_total_transactions(cls):
        return PurchaseOrder.objects.count() + SalesOrder.objects.count()
    
    @classmethod
    def _get_total_volume(cls):
        po_volume = PurchaseOrder.objects.aggregate(
            total=Sum('total_amount')
            )['total'] or 0
        
        so_volume = SalesOrder.objects.aggregate(
            total=Sum('total_amount')
            )['total'] or 0
        
        return float(po_volume + so_volume)
    
    @classmethod
    def _get_pending_approvals(cls):
        return InvestorContract.objects.filter(status='pending').count()
    
    @classmethod
    def _get_active_investors(cls):
        signed_status = getattr(
            InvestorContract.InvestorContractStatus,
            "CONTRACT_SIGNED",
            "contract_signed"
        )
        return InvestorContract.objects.filter(
            status=signed_status
        ).values('user').distinct().count()
    
    @classmethod
    def _get_active_investments(cls):
        return FundInvestment.objects.filter(
            investment_status=FundInvestment.InvestmentStatus.ACTIVE
        ).count()
    
    @classmethod
    def _get_investors_without_investments(cls):
        return User.objects.filter(
            investor_contracts=True
        ).exclude(
            investor_contracts__status=InvestorContract.InvestorContractStatus.CONTRACT_SIGNED
        ).count()
    
    @classmethod
    def _get_pending_investor_approvals(cls):
        pending_status = getattr(
            InvestorContract.InvestorContractStatus,
            "PENDING",
            "pending"
        )
        return InvestorContract.objects.filter(
            status=pending_status
        ).count()