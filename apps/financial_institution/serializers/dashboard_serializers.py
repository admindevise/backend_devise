from rest_framework import serializers
from apps.financial_institution.services.dashboard_stats_service import DashboardStatsService

class DashboardStatsSerializer(serializers.Serializer):
    """Serializer para estadísticas del dashboard financiero"""
    
    total_funds = serializers.IntegerField(read_only=True)
    active_funds = serializers.IntegerField(read_only=True)
    aum_by_fund = serializers.ListField(child=serializers.DictField(), read_only=True)
    total_aum = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    total_transactions = serializers.IntegerField(read_only=True)
    total_volume = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    active_investors = serializers.IntegerField(read_only=True)
    investors_with_investments = serializers.IntegerField(read_only=True)
    investors_without_investments = serializers.IntegerField(read_only=True)
    pending_investor_approvals = serializers.IntegerField(read_only=True)
    members_financial_institution = serializers.IntegerField(read_only=True)
    onboarding_users_financial_institution = serializers.IntegerField(read_only=True)
    
    
    