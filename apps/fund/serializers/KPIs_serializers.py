from rest_framework import serializers
from django.utils import timezone

from apps.fund.models.core import Fund
from apps.fund.models.membership import FundInvestment
from apps.fund.services.fund_calculations import FundCalculationService, FundCalculationError

# ================================================
# TOKEN VALUE CHANGE
# ================================================
class TokenValueChangeSerializer(serializers.Serializer):
    """
    Serializer para calcular el cambio de valor de tokens de un usuario en un fondo.
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
    )
    
    investment_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID de la inversión específica (opcional)"
    )
    
    def validate_fund_id(self, value):
        """Validar que el fondo existe"""
        try:
            fund = Fund.objects.get(id=value)
            return fund
        except Fund.DoesNotExist:
            raise serializers.ValidationError(f"El fondo con ID {value} no existe")
    
    def validate_investment_id(self, value):
        """Validar que la inversión existe si se proporciona"""
        if value is None:
            return None
        
        try:
            investment = FundInvestment.objects.get(id=value)
            return investment
        except FundInvestment.DoesNotExist:
            raise serializers.ValidationError(f"La inversión con ID {value} no existe")
    
    def validate(self, attrs):
        """Validaciones a nivel de objeto"""
        fund = attrs.get('fund_id')
        investment = attrs.get('investment_id')
        request = self.context.get('request')
        
        # Validar que el usuario esté autenticado
        if not request or not request.user:
            raise serializers.ValidationError("Usuario no autenticado")
        
        # Si se especifica una inversión, validar que pertenezca al usuario y al fondo
        if investment:
            if investment.application.user != request.user:
                raise serializers.ValidationError(
                    "La inversión no pertenece al usuario actual"
                )
            if investment.application.fund != fund:
                raise serializers.ValidationError(
                    "La inversión no pertenece al fondo especificado"
                )
        
        return attrs
    
    def create(self, validated_data):
        """Calcular cambio de valor usando el servicio"""
        request = self.context.get('request')
        fund = validated_data['fund_id']
        investment = validated_data.get('investment_id')
        
        try:
            # Crear servicio de cálculos
            calc_service = FundCalculationService(fund)
            
            # Calcular cambio de valor
            result = calc_service.calculate_tkn_value_change(
                user=request.user,
                investment_id=investment.id if investment else None
            )
            
            return result
            
        except FundCalculationError as e:
            raise serializers.ValidationError(str(e))
        except Exception as e:
            raise serializers.ValidationError(f"Error interno: {str(e)}")
    
    def to_representation(self, instance):
        """Representación de respuesta"""
        if 'error' in instance:
            return {
                'success': False,
                'error': instance['error'],
                'user_id': instance.get('user_id'),
                'fund_id': instance.get('fund_id'),
                'investment_id': instance.get('investment_id')
            }
        
        return {
            'success': True,
            'data': {
                'user_info': {
                    'user_id': instance['user_id'],
                    'user_email': instance['user_email'],
                    'fund_id': instance['fund_id'],
                    'fund_name': instance['fund_name']
                },
                'token_value_info': {
                    'current_tkn_value': instance['current_tkn_value'],
                    'weighted_average_change': instance['weighted_average_change'],
                    'weighted_average_change_percentage': instance['weighted_average_change_percentage']
                },
                'portfolio_summary': {
                    'total_investments': instance['total_investments'],
                    'total_cost_basis': instance['total_cost_basis'],
                    'investment_filter': instance.get('investment_filter')
                },
                'investment_details': instance['investment_details'],
                'calculation_metadata': {
                    'calculation_date': instance['calculation_date']
                }
            },
            'message': f'Cambio de valor calculado exitosamente para {instance["total_investments"]} inversión(es)'
        }
        
# ================================================
# TOTAL DISTRIBUTIONS LAST 12M        
# ================================================    
class FundDistributionsSummary12MSerializer(serializers.Serializer):
    """
    Serializer para obtener el resumen de distribuciones de los últimos 12 meses de un fondo.
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo para calcular distribuciones"
    )
    
    user_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID del usuario específico (opcional, si no se proporciona usa el usuario autenticado)"
    )
    
    investment_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID de la inversión específica (opcional)"
    )
    
    include_details = serializers.BooleanField(
        default=False,
        help_text="Incluir detalles de distribuciones individuales"
    )
    
    def validate_fund_id(self, value):
        """Validar que el fondo existe"""
        try:
            fund = Fund.objects.get(id=value)
            return fund
        except Fund.DoesNotExist:
            raise serializers.ValidationError(f"El fondo con ID {value} no existe")
    
    def validate_user_id(self, value):
        """Validar que el usuario existe si se proporciona"""
        if value is None:
            return None
        
        from apps.user.models import User
        try:
            user = User.objects.get(id=value)
            return user
        except User.DoesNotExist:
            raise serializers.ValidationError(f"El usuario con ID {value} no existe")
    
    def validate_investment_id(self, value):
        """Validar que la inversión existe si se proporciona"""
        if value is None:
            return None
        
        try:
            investment = FundInvestment.objects.get(id=value)
            return investment
        except FundInvestment.DoesNotExist:
            raise serializers.ValidationError(f"La inversión con ID {value} no existe")
    
    def validate(self, attrs):
        """Validaciones a nivel de objeto"""
        fund = attrs.get('fund_id')
        target_user = attrs.get('user_id')
        investment = attrs.get('investment_id')
        request = self.context.get('request')
        
        # Validar que el usuario esté autenticado
        if not request or not request.user:
            raise serializers.ValidationError("Usuario no autenticado")
        
        # Si no se especifica user_id, usar el usuario autenticado
        if target_user is None:
            target_user = request.user
            attrs['user_id'] = target_user
        
        # Validar permisos: solo staff puede consultar otros usuarios
        if target_user != request.user and not request.user.is_staff:
            raise serializers.ValidationError(
                "No tienes permisos para consultar distribuciones de otros usuarios"
            )
        
        # Si se especifica una inversión, validar que pertenezca al usuario y al fondo
        if investment:
            if investment.application.user != target_user:
                raise serializers.ValidationError(
                    "La inversión no pertenece al usuario especificado"
                )
            if investment.application.fund != fund:
                raise serializers.ValidationError(
                    "La inversión no pertenece al fondo especificado"
                )
        
        return attrs
    
    def create(self, validated_data):
        """Calcular suma de distribuciones usando el servicio"""
        fund = validated_data['fund_id']
        target_user = validated_data['user_id']
        investment = validated_data.get('investment_id')
        include_details = validated_data.get('include_details', False)
        request = self.context.get('request')
        
        try:
            # Crear servicio de cálculos
            calc_service = FundCalculationService(fund)
            
            # Obtener suma de distribuciones de los últimos 12 meses
            total_distributions_12m = calc_service.sum_distributions_last_12_months(
                user=target_user,
                investment_id=investment.id if investment else None
            )
            
            # Construir respuesta base
            result = {
                'fund_id': fund.id,
                'fund_name': fund.name,
                'target_user_id': target_user.id,
                'target_user_email': target_user.email,
                'investment_id': investment.id if investment else None,
                'total_distributions_12m': total_distributions_12m,
                'period': '12 months',
                'calculation_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Si se solicitan detalles, agregar información adicional
            if include_details:
                result.update(self._get_detailed_distribution_info(fund, target_user, investment))
            
            return result
            
        except FundCalculationError as e:
            raise serializers.ValidationError(str(e))
        except Exception as e:
            raise serializers.ValidationError(f"Error interno: {str(e)}")
    
    def _get_detailed_distribution_info(self, fund, target_user, investment=None):
        """Obtener información detallada de distribuciones del usuario"""
        from apps.fund.models.distributions import InvestmentDistributionRecord
        from django.db.models import Count, Avg, Sum
        from django.utils import timezone
        from datetime import timedelta
        
        # Fecha límite (hace 12 meses)
        twelve_months_ago = timezone.now() - timedelta(days=365)
        current_date = timezone.now()
        
        # Calcular período límite
        limit_year = twelve_months_ago.year
        limit_month = twelve_months_ago.month
        current_year = current_date.year
        current_month = current_date.month
        
        # Obtener registros de distribución del usuario
        user_distributions = InvestmentDistributionRecord.objects.select_related(
            'distribution_period', 'investment__application__user'
        ).filter(
            distribution_period__fund=fund,
            investment__application__user=target_user,
            payment_status__in=[
                InvestmentDistributionRecord.PaymentStatus.PAID,
                InvestmentDistributionRecord.PaymentStatus.VERIFIED,
                InvestmentDistributionRecord.PaymentStatus.PROCESSING
            ]
        )
        
        # Filtrar por período usando period_year y period_month
        from django.db import models
        period_filter = models.Q(
            models.Q(distribution_period__period_year__gt=limit_year) |
            models.Q(distribution_period__period_year=limit_year, distribution_period__period_month__gte=limit_month)
        ) & models.Q(
            models.Q(distribution_period__period_year__lt=current_year) |
            models.Q(distribution_period__period_year=current_year, distribution_period__period_month__lte=current_month)
        )
        
        user_distributions = user_distributions.filter(period_filter)
        
        # Filtrar por inversión específica si se proporciona
        if investment:
            user_distributions = user_distributions.filter(investment=investment)
        
        user_distributions = user_distributions.order_by(
            '-distribution_period__period_year', 
            '-distribution_period__period_month'
        )
        
        # Estadísticas del usuario
        stats = user_distributions.aggregate(
            total_count=Count('id'),
            average_amount=Avg('net_distribution_amount_cop'),
            total_distributed=Sum('net_distribution_amount_cop')
        )
        
        # Lista de distribuciones del usuario
        individual_distributions = []
        for record in user_distributions:
            individual_distributions.append({
                'record_id': record.id,
                'investment_id': record.investment.id,
                'amount': float(record.net_distribution_amount_cop or 0),
                'distribution_date': record.distribution_period.payment_date.strftime("%Y-%m-%d") if record.distribution_period.payment_date else None,
                'period_display': record.distribution_period.period_display,
                'period_year': record.distribution_period.period_year,
                'period_month': record.distribution_period.period_month,
                'payment_status': record.get_payment_status_display(),
                'tokens_held': record.tokens_held_on_record_date,
                'participation_percentage': float(record.participation_percentage or 0)
            })
        
        return {
            'detailed_stats': {
                'total_distributions_count': stats['total_count'] or 0,
                'average_distribution_amount': float(stats['average_amount'] or 0),
                'total_amount_verified': float(stats['total_distributed'] or 0),
                'period_start_date': twelve_months_ago.strftime("%Y-%m-%d"),
                'period_end_date': timezone.now().strftime("%Y-%m-%d"),
                'user_specific': True,
                'investment_specific': investment.id if investment else None
            },
            'individual_distributions': individual_distributions
        }
    
    def to_representation(self, instance):
        """Representación de respuesta"""
        base_response = {
            'success': True,
            'data': {
                'fund_info': {
                    'fund_id': instance['fund_id'],
                    'fund_name': instance['fund_name']
                },
                'user_info': {
                    'target_user_id': instance['target_user_id'],
                    'target_user_email': instance['target_user_email'],
                    'investment_filter': instance.get('investment_id')
                },
                'distribution_summary': {
                    'total_distributions_12m': float(instance['total_distributions_12m']),
                    'period_analyzed': instance['period'],
                    'calculation_date': instance['calculation_date']
                }
            },
            'message': f'Distribuciones del usuario calculadas exitosamente: ${float(instance["total_distributions_12m"]):,.2f}'
        }
        
        # Agregar detalles si están disponibles
        if 'detailed_stats' in instance:
            base_response['data']['detailed_stats'] = instance['detailed_stats']
            base_response['data']['individual_distributions'] = instance['individual_distributions']
        
        return base_response
    
# ================================================
# YIELD FROM DISTRIBUTIONS
# ================================================
class YieldFromDistributionsSerializer(serializers.Serializer):
    """
    Serializer para calcular el rendimiento basado en distribuciones de los últimos 12 meses.
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
    )
    
    investment_id = serializers.IntegerField(
        required=True,
        help_text="ID de la inversión específica (requerido)"
    )
    
    def validate_fund_id(self, value):
        """Validar que el fondo existe"""
        try:
            fund = Fund.objects.get(id=value)
            return fund
        except Fund.DoesNotExist:
            raise serializers.ValidationError(f"El fondo con ID {value} no existe")
    
    def validate_investment_id(self, value):
        """Validar que la inversión existe"""
        try:
            investment = FundInvestment.objects.get(id=value)
            return investment
        except FundInvestment.DoesNotExist:
            raise serializers.ValidationError(f"La inversión con ID {value} no existe")
    
    def validate(self, attrs):
        """Validaciones a nivel de objeto"""
        fund = attrs.get('fund_id')
        investment = attrs.get('investment_id')
        request = self.context.get('request')
        
        # Validar que el usuario esté autenticado
        if not request or not request.user:
            raise serializers.ValidationError("Usuario no autenticado")
        
        # Validar que la inversión pertenezca al usuario y al fondo
        if investment.application.user != request.user:
            raise serializers.ValidationError(
                "La inversión no pertenece al usuario actual"
            )
        if investment.application.fund != fund:
            raise serializers.ValidationError(
                "La inversión no pertenece al fondo especificado"
            )
        
        # Validar que la inversión esté activa
        if investment.investment_status != FundInvestment.InvestmentStatus.ACTIVE:
            raise serializers.ValidationError(
                "La inversión debe estar activa para calcular rendimientos"
            )
        
        return attrs
    
    def create(self, validated_data):
        """Calcular rendimiento por distribuciones usando el servicio"""
        request = self.context.get('request')
        fund = validated_data['fund_id']
        investment = validated_data['investment_id']
        
        try:
            # Crear servicio de cálculos
            calc_service = FundCalculationService(fund)
            
            # Calcular rendimiento por distribuciones
            result = calc_service.calculate_yield_from_distributions(
                user=request.user,
                investment_id=investment.id
            )
            
            return result
            
        except FundCalculationError as e:
            raise serializers.ValidationError(str(e))
        except Exception as e:
            raise serializers.ValidationError(f"Error interno: {str(e)}")
    
    def to_representation(self, instance):
        """Representación de respuesta"""
        if 'error' in instance:
            return {
                'success': False,
                'error': instance['error'],
                'user_id': instance.get('user_id'),
                'investment_id': instance.get('investment_id'),
                'token_cash_on_cash': instance.get('token_cash_on_cash', 0.0)
            }
        
        return {
            'success': True,
            'data': {
                'user_info': {
                    'user_id': instance['user_id'],
                    'user_email': instance['user_email']
                },
                'fund_info': {
                    'fund_id': instance['fund_id'],
                    'fund_name': instance['fund_name']
                },
                'investment_info': {
                    'investment_id': instance['investment_id'],
                    'units_owned': instance['units_owned'],
                    'tkn_cost': instance['tkn_cost']
                },
                'yield_calculation': {
                    'total_distributions_12m': instance['total_distributions_12m'],
                    'token_cash_on_cash': instance['token_cash_on_cash'],
                    'period_analyzed': instance['period_analyzed']
                },
                'calculation_metadata': {
                    'calculation_date': instance['calculation_date']
                }
            },
            'message': f'Rendimiento calculado exitosamente: {instance["token_cash_on_cash"]:.4f} (Cash on Cash por token)'
        }    

