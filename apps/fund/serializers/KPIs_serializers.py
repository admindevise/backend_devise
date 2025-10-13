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

# ================================================
# AVERAGE PRICE CHANGE PER UNIT
# ================================================
class UserPriceChangeSerializer(serializers.Serializer):
    """
    Serializer para calcular el cambio de precio por unidad para un usuario específico
    usando promedio ponderado por unidades.
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
    )
    
    user_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID del usuario específico (opcional, si no se proporciona usa el usuario autenticado)"
    )
    
    include_portfolio_details = serializers.BooleanField(
        default=True,
        help_text="Incluir detalles de cada inversión en el portfolio"
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
        
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=value)
            return user
        except User.DoesNotExist:
            raise serializers.ValidationError(f"El usuario con ID {value} no existe")
    
    def validate(self, attrs):
        """Validaciones a nivel de objeto"""
        fund = attrs.get('fund_id')
        target_user = attrs.get('user_id')
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
                "No tienes permisos para consultar cambios de precio de otros usuarios"
            )
        
        return attrs
    
    def create(self, validated_data):
        """Calcular cambio de precio del usuario usando el servicio"""
        fund = validated_data['fund_id']
        target_user = validated_data['user_id']
        include_details = validated_data.get('include_portfolio_details', True)
        request = self.context.get('request')
        
        try:
            # Crear servicio de cálculos
            calc_service = FundCalculationService(fund)
            
            # Calcular cambio de precio del usuario
            result = calc_service.calculate_user_price_change(target_user)
            
            # Si hay error en el resultado, devolverlo
            if 'error' in result:
                return result
            
            # Filtrar detalles si no se solicitan
            if not include_details:
                result.pop('investment_details', None)
                result.pop('portfolio_statistics', None)
            
            # Agregar metadata adicional
            result['calculated_by'] = request.user.email if request else None
            
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
                'fund_id': instance.get('fund_id')
            }
        
        response_data = {
            'success': True,
            'data': {
                'user_info': {
                    'user_id': instance['user_id'],
                    'user_email': instance['user_email'],
                    'fund_id': instance['fund_id'],
                    'fund_name': instance['fund_name']
                },
                'price_change_summary': {
                    'current_price_per_unit': instance['current_price_per_unit'],
                    'user_weighted_average_price_change': instance['user_weighted_average_price_change'],
                    'total_user_units': instance['total_user_units'],
                    'total_user_investments': instance['total_user_investments'],
                    'calculation_method': instance['calculation_method']
                }
            },
            'message': f'Cambio de precio calculado exitosamente: {instance["user_weighted_average_price_change"]:.2f}%'
        }
        
        # Agregar detalles si están disponibles
        if 'investment_details' in instance:
            response_data['data']['portfolio_details'] = {
                'investment_breakdown': instance['investment_details'],
                'portfolio_statistics': instance.get('portfolio_statistics', {})
            }
        
        # Agregar metadata
        response_data['data']['calculation_metadata'] = {
            'calculation_date': instance['calculation_date'],
            'calculated_by': instance.get('calculated_by')
        }
        
        return response_data

# ================================================
# USER RENT 12M PER UNIT
# ================================================
class UserRent12mPerUnitSerializer(serializers.Serializer):
    """
    Serializer para calcular las rentas por unidad de los últimos 12 meses para un usuario específico.
    
    Calcula las distribuciones recibidas por unidad en los últimos 12 meses usando lógica de día 30 
    como corte: si estamos antes del día 30 del mes actual, usa el mes anterior como último finalizado.
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
    )
    
    user_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID del usuario específico (opcional, si no se proporciona usa el usuario autenticado)"
    )
    
    include_distribution_details = serializers.BooleanField(
        default=True,
        help_text="Incluir detalles de distribuciones por inversión"
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
        
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=value)
            return user
        except User.DoesNotExist:
            raise serializers.ValidationError(f"El usuario con ID {value} no existe")
    
    def validate(self, attrs):
        """Validaciones a nivel de objeto"""
        fund = attrs.get('fund_id')
        target_user = attrs.get('user_id')
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
                "No tienes permisos para consultar rentas de otros usuarios"
            )
        
        return attrs
    
    def create(self, validated_data):
        """Calcular rentas 12m por unidad usando el servicio"""
        fund = validated_data['fund_id']
        target_user = validated_data['user_id']
        include_details = validated_data.get('include_distribution_details', True)
        request = self.context.get('request')
        
        try:
            # Crear servicio de cálculos
            calc_service = FundCalculationService(fund)
            
            # Calcular rentas 12m por unidad del usuario
            result = calc_service.calculate_user_rent_12m_per_unit(target_user)
            
            # Si hay error en el resultado, devolverlo
            if 'error' in result:
                return result
            
            # Filtrar detalles si no se solicitan
            if not include_details:
                result.pop('distribution_details', None)
            
            # Agregar metadata adicional
            result['calculated_by'] = request.user.email if request else None
            
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
                'fund_id': instance.get('fund_id')
            }
        
        response_data = {
            'success': True,
            'data': {
                'user_info': {
                    'user_id': instance['user_id'],
                    'user_email': instance['user_email'],
                    'fund_id': instance['fund_id'],
                    'fund_name': instance['fund_name']
                },
                'rent_summary': {
                    'user_rent_per_unit_12m': instance['user_rent_per_unit_12m'],
                    'total_user_rent_12m': instance['total_user_rent_12m'],
                    'total_user_units': instance['total_user_units'],
                    'average_monthly_rent_per_unit': instance['user_rent_per_unit_12m'] / 12 if instance['user_rent_per_unit_12m'] > 0 else 0
                },
                'period_info': {
                    'period_analyzed': instance['period_analyzed'],
                    'current_date': instance['current_date'],
                    'cutoff_logic_applied': instance['cutoff_logic'],
                    'methodology': 'Uses day 30 as cutoff: if current day < 30, uses previous month as last completed'
                }
            },
            'message': f'Rentas 12m calculadas exitosamente: ${instance["user_rent_per_unit_12m"]:.2f} por unidad'
        }
        
        # Agregar detalles si están disponibles
        if 'distribution_details' in instance:
            response_data['data']['distribution_breakdown'] = {
                'investment_details': instance['distribution_details'],
                'total_investments_analyzed': len(instance['distribution_details'])
            }
        
        # Agregar metadata
        response_data['data']['calculation_metadata'] = {
            'calculation_date': instance['calculation_date'],
            'calculated_by': instance.get('calculated_by')
        }
        
        return response_data

# ================================================
# USER CASH ON CASH
# ================================================
class UserCashOnCashSerializer(serializers.Serializer):
    """
    Serializer para calcular Cash on Cash de un usuario específico.
    
    Cash on Cash = (Distribuciones anuales del usuario / Costo inicial del usuario) × 100
    
    Utiliza la misma lógica de "día 30 como corte" para determinar meses completados.
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
    )
    
    user_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID del usuario específico (opcional, si no se proporciona usa el usuario autenticado)"
    )
    
    include_investment_details = serializers.BooleanField(
        default=True,
        help_text="Incluir detalles de Cash on Cash por inversión"
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
        
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=value)
            return user
        except User.DoesNotExist:
            raise serializers.ValidationError(f"El usuario con ID {value} no existe")
    
    def validate(self, attrs):
        """Validaciones a nivel de objeto"""
        fund = attrs.get('fund_id')
        target_user = attrs.get('user_id')
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
                "No tienes permisos para consultar Cash on Cash de otros usuarios"
            )
        
        return attrs
    
    def create(self, validated_data):
        """Calcular Cash on Cash del usuario usando el servicio"""
        fund = validated_data['fund_id']
        target_user = validated_data['user_id']
        include_details = validated_data.get('include_investment_details', True)
        request = self.context.get('request')
        
        try:
            # Crear servicio de cálculos
            calc_service = FundCalculationService(fund)
            
            # Calcular Cash on Cash del usuario
            result = calc_service.calculate_user_cash_on_cash(target_user)
            
            # Si hay error en el resultado, devolverlo
            if 'error' in result:
                return result
            
            # Filtrar detalles si no se solicitan
            if not include_details:
                result.pop('investment_details', None)
            
            # Agregar metadata adicional
            result['calculated_by'] = request.user.email if request else None
            
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
                'fund_id': instance.get('fund_id')
            }
        
        response_data = {
            'success': True,
            'data': {
                'user_info': {
                    'user_id': instance['user_id'],
                    'user_email': instance['user_email'],
                    'fund_id': instance['fund_id'],
                    'fund_name': instance['fund_name']
                },
                'cash_on_cash_summary': {
                    'user_cash_on_cash_percentage': instance['user_cash_on_cash_percentage'],
                    'total_user_initial_investment': instance['total_user_initial_investment'],
                    'total_user_distributions_12m': instance['total_user_distributions_12m'],
                    'annualized_return': f"{instance['user_cash_on_cash_percentage']:.2f}%"
                },
                'period_info': {
                    'period_analyzed': instance['period_analyzed'],
                    'current_date': instance['current_date'],
                    'cutoff_logic_applied': instance['cutoff_logic'],
                    'calculation_period': instance['calculation_period'],
                    'methodology': 'Uses day 30 as cutoff: if current day < 30, uses previous month as last completed'
                }
            },
            'message': f'Cash on Cash calculado exitosamente: {instance["user_cash_on_cash_percentage"]:.2f}%'
        }
        
        # Agregar detalles por inversión si están disponibles
        if 'investment_details' in instance:
            response_data['data']['investment_breakdown'] = {
                'individual_investments': instance['investment_details'],
                'total_investments_analyzed': len(instance['investment_details']),
                'investment_summary': {
                    'highest_coc': max([inv['investment_cash_on_cash'] for inv in instance['investment_details']]) if instance['investment_details'] else 0,
                    'lowest_coc': min([inv['investment_cash_on_cash'] for inv in instance['investment_details']]) if instance['investment_details'] else 0,
                    'average_coc': sum([inv['investment_cash_on_cash'] for inv in instance['investment_details']]) / len(instance['investment_details']) if instance['investment_details'] else 0
                }
            }
        
        # Agregar metadata
        response_data['data']['calculation_metadata'] = {
            'calculation_date': instance['calculation_date'],
            'calculated_by': instance.get('calculated_by'),
            'formula_applied': 'Cash on Cash = (Distribuciones anuales / Costo inicial) × 100'
        }
        
        return response_data
    
# ================================================
# USER CURRENT VALUE
# ================================================
class UserCurrentValueSerializer(serializers.Serializer):
    """
    Serializer para calcular el valor actual de inversión de un usuario
    
    4.5) Valor actual del usuario = unidades del usuario × precio actual
    """
    
    fund_id = serializers.IntegerField(required=True)
    
    def validate_fund_id(self, value):
        """Validar que el fondo existe"""
        try:
            return Fund.objects.get(id=value)
        except Fund.DoesNotExist:
            raise serializers.ValidationError(f"El fondo con ID {value} no existe")
    
    def validate(self, attrs):
        """Validaciones a nivel de serializer"""
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Usuario no autenticado")
        
        # Siempre usar el usuario autenticado
        attrs['_user'] = request.user
        attrs['_fund'] = attrs['fund_id']
        
        return attrs
    
    def create(self, validated_data):
        """Calcular valor actual usando el servicio"""
        fund = validated_data['_fund']
        user = validated_data['_user']
        
        try:
            calculation_service = FundCalculationService(fund)
            result = calculation_service.calculate_user_current_value(user)
            
            if 'error' in result:
                raise serializers.ValidationError(result['error'])
            
            return result
            
        except Exception as e:
            raise serializers.ValidationError(f"Error calculando valor actual: {str(e)}")
    
    def to_representation(self, instance):
        """Formatear la respuesta de salida"""
        if isinstance(instance, dict) and 'error' not in instance:
            return {
                'success': True,
                'data': {
                    'user_info': {
                        'user_id': instance.get('user_id'),
                        'user_email': instance.get('user_email'),
                    },
                    'fund_info': {
                        'fund_id': instance.get('fund_id'),
                        'fund_name': instance.get('fund_name'),
                        'current_price_per_unit': instance.get('current_price_per_unit'),
                    },
                    'value_metrics': {
                        'total_user_units': instance.get('total_user_units'),
                        'total_user_invested_amount': instance.get('total_user_invested_amount'),
                        'user_current_value': instance.get('user_current_value'),
                        'user_unrealized_gain_loss': instance.get('user_unrealized_gain_loss'),
                        'user_return_percentage': instance.get('user_return_percentage'),
                    },
                    'investment_details': instance.get('investment_details', []),
                    'calculation_date': instance.get('calculation_date')
                }
            }
        return instance
    
# ================================================
# USER SIMPLE TOTAL RETURN
# ================================================    
    
class UserSimpleTotalReturnSerializer(serializers.Serializer):
    """
    Serializer para calcular el rendimiento total simple de un usuario
    
    4.6) Rendimiento total simple del usuario = ((valor actual + efectivo recibido) - Costo) / Costo
    """
    
    fund_id = serializers.IntegerField(required=True)
    user_id = serializers.IntegerField(required=False)
    
    def validate_fund_id(self, value):
        """Validar que el fondo existe"""
        try:
            return Fund.objects.get(id=value)
        except Fund.DoesNotExist:
            raise serializers.ValidationError(f"El fondo con ID {value} no existe")
    
    def validate(self, attrs):
        """Validaciones a nivel de serializer"""
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Usuario no autenticado")
        
        # Siempre usar el usuario autenticado
        attrs['_user'] = request.user
        attrs['_fund'] = attrs['fund_id']
        
        return attrs
    
    def create(self, validated_data):
        """Calcular rendimiento total simple usando el servicio"""
        fund = validated_data['_fund']
        user = validated_data['_user']
        
        try:
            calculation_service = FundCalculationService(fund)
            result = calculation_service.calculate_user_simple_total_return(user)
            
            if 'error' in result:
                raise serializers.ValidationError(result['error'])
            
            return result
            
        except Exception as e:
            raise serializers.ValidationError(f"Error calculando rendimiento total simple: {str(e)}")
    
    def to_representation(self, instance):
        """Formatear la respuesta de salida"""
        if isinstance(instance, dict) and 'error' not in instance:
            return {
                'success': True,
                'data': {
                    'user_info': {
                        'user_id': instance.get('user_id'),
                        'user_email': instance.get('user_email'),
                    },
                    'fund_info': {
                        'fund_id': instance.get('fund_id'),
                        'fund_name': instance.get('fund_name'),
                    },
                    'return_metrics': {
                        'user_simple_total_return_percentage': instance.get('user_simple_total_return_percentage'),
                        'total_user_initial_cost': instance.get('total_user_initial_cost'),
                        'total_user_current_value': instance.get('total_user_current_value'),
                        'total_user_cash_received': instance.get('total_user_cash_received'),
                        'user_total_value': instance.get('user_total_value'),
                        'user_absolute_gain_loss': instance.get('user_absolute_gain_loss'),
                    },
                    'portfolio_summary': {
                        'total_investments': instance.get('total_investments'),
                        'investment_breakdown': instance.get('investment_breakdown', []),
                    },
                    'calculation_date': instance.get('calculation_date')
                }
            }
        return instance    
    
    
    