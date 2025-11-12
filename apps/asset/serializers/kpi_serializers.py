from rest_framework import serializers
from apps.asset.models.core import Asset
from apps.asset.services.kpis import AssetKPIFacade


class AssetNOICalculationSerializer(serializers.Serializer):
    """
    Serializer para calcular NOI de un asset.
    
    Uso:
    - Sin parámetros adicionales: Últimos 12 meses
    - Con period_year y period_month: Período específico
    - Con months_back: Rango personalizado
    
    Example:
        >>> # NOI últimos 12 meses
        >>> data = {'asset_id': 1}
        >>> serializer = AssetNOICalculationSerializer(data=data, context={'request': request})
        >>> 
        >>> # NOI de junio 2024
        >>> data = {'asset_id': 1, 'period_year': 2024, 'period_month': 6}
        >>> serializer = AssetNOICalculationSerializer(data=data, context={'request': request})
    """
    
    asset_id = serializers.IntegerField(
        required=True,
        help_text="ID del asset"
    )
    
    period_type = serializers.ChoiceField(
        choices=['monthly', 'quarterly', 'semi_annual', 'annual'],
        default='monthly',
        required=False,
        help_text="Tipo de período"
    )
    
    period_year = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Año específico (opcional)"
    )
    
    period_month = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        max_value=12,
        help_text="Mes específico 1-12 (opcional)"
    )
    
    period_quarter = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        max_value=4,
        help_text="Trimestre específico 1-4 (opcional)"
    )
    
    months_back = serializers.IntegerField(
        default=12,
        required=False,
        min_value=1,
        max_value=60,
        help_text="Meses hacia atrás (default: 12)"
    )
    
    include_breakdown = serializers.BooleanField(
        default=True,
        required=False,
        help_text="Incluir desglose detallado"
    )
    
    # ========================================
    # VALIDACIONES
    # ========================================
    
    def validate_asset_id(self, value):
        """Validar que el asset existe"""
        try:
            asset = Asset.objects.get(id=value)
            
            # Validar que el asset esté activo
            if asset.status != 'active':
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no está activo"
                )
            
            return value
            
        except Asset.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un asset con el ID {value}"
            )
    
    def validate_period_year(self, value):
        """Validar año si se proporciona"""
        if value:
            from django.utils import timezone
            current_year = timezone.now().year
            
            if value < 2000 or value > current_year + 1:
                raise serializers.ValidationError(
                    f"El año debe estar entre 2000 y {current_year + 1}"
                )
        
        return value
    
    def validate(self, attrs):
        """Validaciones a nivel de objeto"""
        period_year = attrs.get('period_year')
        period_month = attrs.get('period_month')
        period_quarter = attrs.get('period_quarter')
        period_type = attrs.get('period_type', 'monthly')
        
        # Si especifica año, debe especificar mes o trimestre según tipo
        if period_year:
            if period_type == 'monthly' and not period_month:
                raise serializers.ValidationError({
                    'period_month': 'Debe especificar el mes para período mensual'
                })
            
            if period_type == 'quarterly' and not period_quarter:
                raise serializers.ValidationError({
                    'period_quarter': 'Debe especificar el trimestre para período trimestral'
                })
        
        return attrs
    
    # ========================================
    # CÁLCULO
    # ========================================
    
    def create(self, validated_data):
        """Calcular NOI usando el facade"""
        asset_id = validated_data.pop('asset_id')
        
        try:
            asset = Asset.objects.get(id=asset_id)
            facade = AssetKPIFacade(asset)
            
            # Calcular NOI
            result = facade.calculate_noi(**validated_data)
            
            return result
            
        except Exception as e:
            raise serializers.ValidationError(
                f"Error calculando NOI: {str(e)}"
            )
    
    # ========================================
    # REPRESENTACIÓN
    # ========================================
    
    def to_representation(self, instance):
        """
        Formatear la respuesta de salida
        
        Args:
            instance: Resultado del cálculo de NOI
            
        Returns:
            dict: Respuesta formateada
        """
        # Si hay error, retornar formato de error
        if isinstance(instance, dict) and 'error' in instance:
            return {
                'success': False,
                'error': instance['error'],
                'asset_id': instance.get('asset_id'),
                'asset_code': instance.get('asset_code')
            }
        
        # Respuesta exitosa
        return {
            'success': True,
            'data': {
                'asset_info': {
                    'asset_id': instance.get('asset_id'),
                    'asset_code': instance.get('asset_code'),
                    'asset_name': instance.get('asset_name'),
                    'fund_id': instance.get('fund_id'),
                    'fund_name': instance.get('fund_name')
                },
                'period_info': {
                    'period_type': instance.get('period_type'),
                    'period_year': instance.get('period_year'),
                    'period_month': instance.get('period_month'),
                    'period_quarter': instance.get('period_quarter'),
                    'period_display': instance.get('period_display'),
                    'period_analyzed': instance.get('period_analyzed'),
                    'start_period': instance.get('start_period'),
                    'end_period': instance.get('end_period')
                },
                'noi_metrics': {
                    'total_operating_income': instance.get('total_operating_income_12m') or instance.get('total_operating_income'),
                    'total_operating_expenses': instance.get('total_operating_expenses_12m') or instance.get('total_operating_expenses'),
                    'net_operating_income': instance.get('total_noi_12m') or instance.get('net_operating_income'),
                    'noi_margin_percentage': instance.get('noi_margin_percentage'),
                    'average_monthly_noi': instance.get('average_monthly_noi')
                },
                'asset_metrics': instance.get('asset_metrics', {}),
                'calculation_date': instance.get('calculation_date')
            },
            'message': f"NOI calculado exitosamente: ${instance.get('total_noi_12m') or instance.get('net_operating_income', 0):,.2f} COP"
        }


class AssetNOISummarySerializer(serializers.Serializer):
    """
    Serializer para obtener resumen de NOI con análisis de tendencias.
    
    Example:
        >>> data = {'asset_id': 1, 'months': 12}
        >>> serializer = AssetNOISummarySerializer(data=data, context={'request': request})
    """
    
    asset_id = serializers.IntegerField(
        required=True,
        help_text="ID del asset"
    )
    
    months = serializers.IntegerField(
        default=12,
        required=False,
        min_value=1,
        max_value=60,
        help_text="Número de meses a analizar (default: 12)"
    )
    
    def validate_asset_id(self, value):
        """Validar que el asset existe"""
        try:
            asset = Asset.objects.get(id=value)
            
            if asset.status != 'active':
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no está activo"
                )
            
            return value
            
        except Asset.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un asset con el ID {value}"
            )
    
    def create(self, validated_data):
        """Obtener resumen de NOI"""
        asset_id = validated_data.pop('asset_id')
        months = validated_data.get('months', 12)
        
        try:
            asset = Asset.objects.get(id=asset_id)
            facade = AssetKPIFacade(asset)
            
            result = facade.get_noi_summary(months=months)
            
            return result
            
        except Exception as e:
            raise serializers.ValidationError(
                f"Error obteniendo resumen de NOI: {str(e)}"
            )
    
    def to_representation(self, instance):
        """Formatear respuesta"""
        if isinstance(instance, dict) and 'error' in instance:
            return {
                'success': False,
                'error': instance['error'],
                'asset_id': instance.get('asset_id')
            }
        
        return {
            'success': True,
            'data': {
                'asset_info': {
                    'asset_id': instance.get('asset_id'),
                    'asset_code': instance.get('asset_code'),
                    'asset_name': instance.get('asset_name'),
                    'fund_name': instance.get('fund_name')
                },
                'noi_summary': {
                    'total_noi_12m': instance.get('total_noi_12m'),
                    'average_monthly_noi': instance.get('average_monthly_noi'),
                    'noi_margin_percentage': instance.get('noi_margin_percentage'),
                    'months_with_data': instance.get('months_with_data')
                },
                'performance_metrics': instance.get('performance_metrics', {}),
                'trend_analysis': instance.get('trend_analysis', {}),
                'monthly_breakdown': instance.get('monthly_breakdown', []),
                'asset_metrics': instance.get('asset_metrics', {})
            }
        }
        
        
class AssetCapRateCalculationSerializer(serializers.Serializer):
    """
    Serializer para calcular Cap Rate de un asset.
    
    Cap Rate = (NOI Anual / Valor del Activo) * 100
    
    Example:
        >>> data = {'asset_id': 1}
        >>> serializer = AssetCapRateCalculationSerializer(data=data)
        >>> serializer.is_valid()
        >>> result = serializer.save()
        >>> print(f"Cap Rate: {result['cap_rate']}%")
    """
    
    asset_id = serializers.IntegerField(
        required=True,
        help_text="ID del asset"
    )
    
    def validate_asset_id(self, value):
        """Validar que el asset existe y tiene datos necesarios"""
        try:
            asset = Asset.objects.get(id=value)
            
            # Validar que el asset esté activo
            if asset.status != 'active':
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no está activo"
                )
            
            # Validar que tenga acquisition_value
            if not asset.acquisition_value or asset.acquisition_value <= 0:
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no tiene un valor de adquisición válido"
                )
            
            return value
            
        except Asset.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un asset con el ID {value}"
            )
    
    def create(self, validated_data):
        """Calcular Cap Rate usando el facade"""
        asset_id = validated_data.pop('asset_id')
        
        try:
            asset = Asset.objects.get(id=asset_id)
            facade = AssetKPIFacade(asset)
            
            # Calcular Cap Rate
            result = facade.calculate_cap_rate()
            
            return result
            
        except Exception as e:
            raise serializers.ValidationError(
                f"Error calculando Cap Rate: {str(e)}"
            )
    
    def to_representation(self, instance):
        """Formatear la respuesta"""
        
        # Si hay error
        if isinstance(instance, dict) and 'error' in instance:
            return {
                'success': False,
                'error': instance['error'],
                'asset_id': instance.get('asset_id'),
                'asset_code': instance.get('asset_code')
            }
        
        # Respuesta exitosa
        return {
            'success': True,
            'data': {
                'asset_info': {
                    'asset_id': instance.get('asset_id'),
                    'asset_code': instance.get('asset_code'),
                    'asset_name': instance.get('asset_name'),
                    'fund_id': instance.get('fund_id'),
                    'fund_name': instance.get('fund_name')
                },
                'cap_rate_metrics': {
                    'cap_rate': instance.get('cap_rate'),
                    'noi_anual': instance.get('noi_anual'),
                    'valor_activo': instance.get('valor_activo'),
                    'interpretation': instance.get('interpretation'),
                    'risk_level': instance.get('risk_level')
                },
                'noi_metrics': {
                    'noi_margin_percentage': instance.get('noi_margin_percentage'),
                    'average_monthly_noi': instance.get('average_monthly_noi')
                },
                'asset_metrics': instance.get('asset_metrics', {}),
                'calculation_date': instance.get('calculation_date'),
                'noi_period': instance.get('noi_period')
            },
            'message': f"Cap Rate calculado: {instance.get('cap_rate', 0):.2f}% - {instance.get('risk_level', 'N/A').title()} Risk"
        }
        
        
class AssetOutputValueCalculationSerializer(serializers.Serializer):
    """
    Serializer para calcular Output Value (Valor de Salida) de un asset.
    
    Output Value = NOI Proyectado / Cap Rate de Salida
    
    Example:
        >>> # Cálculo automático
        >>> data = {'asset_id': 1, 'projection_years': 5}
        >>> 
        >>> # Cálculo con valores específicos
        >>> data = {
        ...     'asset_id': 1,
        ...     'projected_noi': 100000,
        ...     'exit_cap_rate': 6.5
        ... }
    """
    
    asset_id = serializers.IntegerField(
        required=True,
        help_text="ID del asset"
    )
    
    projected_noi = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="NOI proyectado al momento de salida (opcional)"
    )
    
    exit_cap_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Cap Rate de salida esperado en % (opcional)"
    )
    
    projection_years = serializers.IntegerField(
        default=5,
        required=False,
        min_value=1,
        max_value=30,
        help_text="Años hacia adelante para proyección (default: 5)"
    )
    
    annual_noi_growth_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Tasa de crecimiento anual del NOI en % (default: 3%)"
    )
    
    def validate_asset_id(self, value):
        """Validar que el asset existe"""
        try:
            asset = Asset.objects.get(id=value)
            
            if asset.status != 'active':
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no está activo"
                )
            
            return value
            
        except Asset.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un asset con el ID {value}"
            )
    
    def validate_projected_noi(self, value):
        """Validar NOI proyectado"""
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "NOI proyectado debe ser mayor a cero"
            )
        return value
    
    def validate_exit_cap_rate(self, value):
        """Validar cap rate de salida"""
        if value is not None:
            if value <= 0:
                raise serializers.ValidationError(
                    "Cap Rate debe ser mayor a cero"
                )
            if value > 50:
                raise serializers.ValidationError(
                    "Cap Rate parece demasiado alto (>50%)"
                )
        return value
    
    def validate_annual_noi_growth_rate(self, value):
        """Validar tasa de crecimiento"""
        if value is not None:
            if value < -50 or value > 50:
                raise serializers.ValidationError(
                    "Tasa de crecimiento debe estar entre -50% y 50%"
                )
        return value
    
    def validate(self, attrs):
        """Validaciones a nivel de objeto"""
        projected_noi = attrs.get('projected_noi')
        exit_cap_rate = attrs.get('exit_cap_rate')
        
        # Si proporciona uno, debe proporcionar ambos
        if (projected_noi is not None) != (exit_cap_rate is not None):
            raise serializers.ValidationError({
                'detail': 'Si proporciona projected_noi, también debe proporcionar exit_cap_rate y viceversa'
            })
        
        return attrs
    
    def create(self, validated_data):
        """Calcular Output Value usando el facade"""
        asset_id = validated_data.pop('asset_id')
        
        try:
            asset = Asset.objects.get(id=asset_id)
            facade = AssetKPIFacade(asset)
            
            # Calcular Output Value
            result = facade.calculate_output_value(**validated_data)
            
            return result
            
        except Exception as e:
            raise serializers.ValidationError(
                f"Error calculando Output Value: {str(e)}"
            )
    
    def to_representation(self, instance):
        """Formatear la respuesta"""
        
        if isinstance(instance, dict) and 'error' in instance:
            return {
                'success': False,
                'error': instance['error'],
                'asset_id': instance.get('asset_id'),
                'asset_code': instance.get('asset_code')
            }
        
        return {
            'success': True,
            'data': {
                'asset_info': {
                    'asset_id': instance.get('asset_id'),
                    'asset_code': instance.get('asset_code'),
                    'asset_name': instance.get('asset_name'),
                    'fund_id': instance.get('fund_id'),
                    'fund_name': instance.get('fund_name')
                },
                'output_value_metrics': {
                    'output_value': instance.get('output_value'),
                    'projected_noi': instance.get('projected_noi'),
                    'exit_cap_rate': instance.get('exit_cap_rate')
                },
                'projection_context': instance.get('projection_context', {}),
                'return_metrics': instance.get('return_metrics', {}),
                'asset_metrics': instance.get('asset_metrics', {}),
                'calculation_date': instance.get('calculation_date'),
                'calculation_method': instance.get('calculation_method')
            },
            'message': f"Valor de Salida calculado: ${instance.get('output_value', 0):,.2f} COP (MOIC: {instance.get('return_metrics', {}).get('moic', 0):.2f}x)"
        }
        
# ========================================
# FREE CASH FLOW SERIALIZER
# ========================================

class AssetFreeCashFlowCalculationSerializer(serializers.Serializer):
    """
    Serializer para calcular Free Cash Flow (Flujo de Caja Libre) de un asset.
    
    FCF = NOI + Ingresos no operativos - Gastos no operativos - CAPEX - Deuda
    
    Example:
        >>> # Cálculo de últimos 12 meses (default)
        >>> data = {'asset_id': 1}
        >>> 
        >>> # Cálculo de período específico
        >>> data = {
        ...     'asset_id': 1,
        ...     'period_year': 2024,
        ...     'period_month': 6
        ... }
    """
    
    asset_id = serializers.IntegerField(
        required=True,
        help_text="ID del asset"
    )
    
    period_type = serializers.ChoiceField(
        choices=['monthly', 'quarterly', 'annual'],
        default='monthly',
        required=False,
        help_text="Tipo de período"
    )
    
    period_year = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=2000,
        help_text="Año específico (opcional)"
    )
    
    period_month = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        max_value=12,
        help_text="Mes específico (1-12, opcional)"
    )
    
    period_quarter = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        max_value=4,
        help_text="Trimestre específico (1-4, opcional)"
    )
    
    months_back = serializers.IntegerField(
        default=12,
        required=False,
        min_value=1,
        max_value=60,
        help_text="Meses hacia atrás para análisis (default: 12)"
    )
    
    include_breakdown = serializers.BooleanField(
        default=True,
        required=False,
        help_text="Incluir desglose mensual"
    )
    
    def validate_asset_id(self, value):
        """Validar que el asset existe y está activo"""
        try:
            asset = Asset.objects.get(id=value)
            
            if asset.status != 'active':
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no está activo"
                )
            
            return value
            
        except Asset.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un asset con el ID {value}"
            )
    
    def validate_period_year(self, value):
        """Validar año si se proporciona"""
        if value is not None:
            from django.utils import timezone
            current_year = timezone.now().year
            if value > current_year + 1:
                raise serializers.ValidationError(
                    f"El año no puede ser mayor a {current_year + 1}"
                )
        return value
    
    def validate(self, attrs):
        """Validaciones cruzadas"""
        period_type = attrs.get('period_type')
        period_year = attrs.get('period_year')
        period_month = attrs.get('period_month')
        period_quarter = attrs.get('period_quarter')
        
        # Si se especifica año, validar coherencia con period_type
        if period_year:
            if period_type == 'monthly' and not period_month:
                raise serializers.ValidationError({
                    'period_month': 'Se requiere period_month para tipo monthly'
                })
            
            if period_type == 'quarterly' and not period_quarter:
                raise serializers.ValidationError({
                    'period_quarter': 'Se requiere period_quarter para tipo quarterly'
                })
            
            # No permitir month y quarter simultáneamente
            if period_month and period_quarter:
                raise serializers.ValidationError(
                    'No se puede especificar period_month y period_quarter simultáneamente'
                )
        
        return attrs
    
    def create(self, validated_data):
        """Calcular FCF usando el facade"""
        asset_id = validated_data.pop('asset_id')
        
        try:
            asset = Asset.objects.get(id=asset_id)
            facade = AssetKPIFacade(asset)
            
            # Calcular Free Cash Flow
            result = facade.calculate_free_cash_flow(**validated_data)
            
            return result
            
        except Exception as e:
            raise serializers.ValidationError(
                f"Error calculando Free Cash Flow: {str(e)}"
            )
    
    def to_representation(self, instance):
        """Formatear la respuesta"""
        
        # Si hay error
        if isinstance(instance, dict) and 'error' in instance:
            return {
                'success': False,
                'error': instance['error'],
                'asset_id': instance.get('asset_id'),
                'asset_code': instance.get('asset_code')
            }
        
        # Respuesta exitosa
        return {
            'success': True,
            'data': {
                'asset_info': {
                    'asset_id': instance.get('asset_id'),
                    'asset_code': instance.get('asset_code'),
                    'asset_name': instance.get('asset_name'),
                    'fund_id': instance.get('fund_id'),
                    'fund_name': instance.get('fund_name')
                },
                'fcf_metrics': {
                    'free_cash_flow': instance.get('free_cash_flow') or instance.get('total_fcf_12m'),
                    'fcf_per_token': instance.get('fcf_per_token'),
                    'fcf_margin_percentage': instance.get('fcf_margin_percentage'),
                    'average_monthly_fcf': instance.get('average_monthly_fcf')
                },
                'fcf_components': instance.get('fcf_components') or instance.get('fcf_components_12m', {}),
                'period_info': {
                    'period_type': instance.get('period_type'),
                    'period_year': instance.get('period_year'),
                    'period_month': instance.get('period_month'),
                    'period_quarter': instance.get('period_quarter'),
                    'period_display': instance.get('period_display') or instance.get('period_analyzed'),
                    'months_with_data': instance.get('months_with_data')
                },
                'token_info': {
                    'total_tokens': instance.get('total_tokens')
                },
                'monthly_breakdown': instance.get('monthly_breakdown', []) if instance.get('monthly_breakdown') else None,
                'calculation_date': instance.get('calculation_date')
            },
            'message': self._build_message(instance)
        }
    
    def _build_message(self, instance: dict) -> str:
        """Construye mensaje descriptivo del resultado"""
        fcf = instance.get('free_cash_flow') or instance.get('total_fcf_12m', 0)
        fcf_per_token = instance.get('fcf_per_token', 0)
        
        if fcf > 0:
            return f"FCF positivo: ${fcf:,.2f} COP (${fcf_per_token:,.2f} por token). El activo genera efectivo disponible para distribución."
        elif fcf < 0:
            return f"FCF negativo: ${fcf:,.2f} COP. El activo requiere inyección de capital."
        else:
            return "FCF neutro: El activo está en punto de equilibrio."        
   
        
class AssetCashOnCashCalculationSerializer(serializers.Serializer):
    """
    Serializer para calcular Cash on Cash Return de un asset.
    
    Cash on Cash = (FCF Anual / Capital Invertido) × 100
    
    Example:
        >>> data = {'asset_id': 1}
        >>> serializer = AssetCashOnCashCalculationSerializer(data=data)
        >>> serializer.is_valid()
        >>> result = serializer.save()
        >>> print(f"Cash on Cash: {result['cash_on_cash_percentage']}%")
    """
    
    asset_id = serializers.IntegerField(
        required=True,
        help_text="ID del asset"
    )
    
    months_back = serializers.IntegerField(
        default=12,
        required=False,
        min_value=1,
        max_value=60,
        help_text="Meses hacia atrás para FCF (default: 12)"
    )
    
    include_breakdown = serializers.BooleanField(
        default=False,
        required=False,
        help_text="Incluir desglose mensual del FCF"
    )
    
    def validate_asset_id(self, value):
        """Validar que el asset existe y tiene datos necesarios"""
        try:
            asset = Asset.objects.get(id=value)
            
            # Validar que el asset esté activo
            if asset.status != 'active':
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no está activo"
                )
            
            # Validar que tenga acquisition_value
            if not asset.acquisition_value or asset.acquisition_value <= 0:
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no tiene un valor de adquisición válido (capital invertido)"
                )
            
            return value
            
        except Asset.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un asset con el ID {value}"
            )
    
    def create(self, validated_data):
        """Calcular Cash on Cash usando el facade"""
        asset_id = validated_data.pop('asset_id')
        
        try:
            asset = Asset.objects.get(id=asset_id)
            facade = AssetKPIFacade(asset)
            
            # Calcular Cash on Cash
            result = facade.calculate_cash_on_cash(**validated_data)
            
            return result
            
        except Exception as e:
            raise serializers.ValidationError(
                f"Error calculando Cash on Cash: {str(e)}"
            )
    
    def to_representation(self, instance):
        """Formatear la respuesta"""
        
        # Si hay error
        if isinstance(instance, dict) and 'error' in instance:
            return {
                'success': False,
                'error': instance['error'],
                'asset_id': instance.get('asset_id'),
                'asset_code': instance.get('asset_code')
            }
        
        # Respuesta exitosa
        return {
            'success': True,
            'data': {
                'asset_info': {
                    'asset_id': instance.get('asset_id'),
                    'asset_code': instance.get('asset_code'),
                    'asset_name': instance.get('asset_name'),
                    'fund_id': instance.get('fund_id'),
                    'fund_name': instance.get('fund_name')
                },
                'cash_on_cash_metrics': {
                    'cash_on_cash_percentage': instance.get('cash_on_cash_percentage'),
                    'fcf_anual': instance.get('fcf_anual'),
                    'capital_invertido': instance.get('capital_invertido'),
                    'interpretation': instance.get('interpretation'),
                    'performance_level': instance.get('performance_level')
                },
                'additional_metrics': instance.get('additional_metrics', {}),
                'fcf_components': instance.get('fcf_components', {}),
                'asset_metrics': instance.get('asset_metrics', {}),
                'monthly_breakdown': instance.get('monthly_breakdown'),
                'calculation_date': instance.get('calculation_date'),
                'period_analyzed': instance.get('period_analyzed'),
                'calculation_note': instance.get('calculation_note')
            },
            'message': f"Cash on Cash calculado: {instance.get('cash_on_cash_percentage', 0):.2f}% - {instance.get('performance_level', 'N/A').replace('_', ' ').title()}"
        }       
       
       
class AssetDividendYieldCalculationSerializer(serializers.Serializer):
    """
    Serializer para calcular Dividend Yield de un asset.
    
    Dividend Yield = (Dividendo por Token / Valor Compra Token) × 100
    
    Example:
        >>> # Anualizado
        >>> data = {'asset_id': 1}
        >>> 
        >>> # Período específico
        >>> data = {
        ...     'asset_id': 1,
        ...     'period_year': 2024,
        ...     'period_month': 12
        ... }
    """
    
    asset_id = serializers.IntegerField(
        required=True,
        help_text="ID del asset"
    )
    
    period_type = serializers.ChoiceField(
        choices=['monthly', 'quarterly'],
        default='monthly',
        required=False,
        help_text="Tipo de período"
    )
    
    period_year = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=2000,
        help_text="Año específico (opcional, si no se proporciona calcula anualizado)"
    )
    
    period_month = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        max_value=12,
        help_text="Mes específico (1-12, opcional)"
    )
    
    period_quarter = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        max_value=4,
        help_text="Trimestre específico (1-4, opcional)"
    )
    
    calculate_annualized = serializers.BooleanField(
        default=True,
        required=False,
        help_text="Calcular yield anualizado además del período"
    )
    
    def validate_asset_id(self, value):
        """Validar que el asset existe y tiene tokens"""
        try:
            asset = Asset.objects.get(id=value)
            
            if asset.status != 'active':
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no está activo"
                )
            
            if not hasattr(asset, 'total_tokens_issued') or asset.total_tokens_issued <= 0:
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no tiene tokens emitidos"
                )
            
            if not asset.acquisition_value or asset.acquisition_value <= 0:
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no tiene un valor de adquisición válido"
                )
            
            return value
            
        except Asset.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un asset con el ID {value}"
            )
    
    def validate(self, attrs):
        """Validaciones cruzadas"""
        period_type = attrs.get('period_type')
        period_year = attrs.get('period_year')
        period_month = attrs.get('period_month')
        period_quarter = attrs.get('period_quarter')
        
        if period_year:
            if period_type == 'monthly' and not period_month:
                raise serializers.ValidationError({
                    'period_month': 'Se requiere period_month para tipo monthly'
                })
            
            if period_type == 'quarterly' and not period_quarter:
                raise serializers.ValidationError({
                    'period_quarter': 'Se requiere period_quarter para tipo quarterly'
                })
        
        return attrs
    
    def create(self, validated_data):
        """Calcular Dividend Yield usando el facade"""
        asset_id = validated_data.pop('asset_id')
        
        try:
            asset = Asset.objects.get(id=asset_id)
            facade = AssetKPIFacade(asset)
            
            result = facade.calculate_dividend_yield(**validated_data)
            
            return result
            
        except Exception as e:
            raise serializers.ValidationError(
                f"Error calculando Dividend Yield: {str(e)}"
            )
    
    def to_representation(self, instance):
        """Formatear la respuesta"""
        
        if isinstance(instance, dict) and 'error' in instance:
            return {
                'success': False,
                'error': instance['error'],
                'asset_id': instance.get('asset_id'),
                'asset_code': instance.get('asset_code')
            }
        
        # Determinar si es período específico o anualizado
        is_period_specific = 'dividend_yield_period_percentage' in instance
        
        return {
            'success': True,
            'data': {
                'asset_info': {
                    'asset_id': instance.get('asset_id'),
                    'asset_code': instance.get('asset_code'),
                    'asset_name': instance.get('asset_name'),
                    'fund_id': instance.get('fund_id'),
                    'fund_name': instance.get('fund_name')
                },
                'dividend_yield_metrics': {
                    'dividend_yield_period_percentage': instance.get('dividend_yield_period_percentage'),
                    'dividend_yield_annualized_percentage': instance.get('dividend_yield_annualized_percentage') or instance.get('dividend_yield_annualized_percentage'),
                    'dividend_yield_monthly_avg_percentage': instance.get('dividend_yield_monthly_avg_percentage'),
                    'dividendo_por_token': instance.get('dividendo_por_token') or instance.get('dividendo_anual_por_token'),
                    'valor_compra_token': instance.get('valor_compra_token'),
                    'interpretation': instance.get('interpretation'),
                    'performance_level': instance.get('performance_level')
                },
                'period_info': {
                    'period_type': instance.get('period_type'),
                    'period_year': instance.get('period_year'),
                    'period_month': instance.get('period_month'),
                    'period_quarter': instance.get('period_quarter'),
                    'period_display': instance.get('period_display') or instance.get('period_analyzed')
                },
                'period_metrics': instance.get('period_metrics') or instance.get('annual_metrics', {}),
                'asset_metrics': instance.get('asset_metrics', {}),
                'calculation_date': instance.get('calculation_date')
            },
            'message': self._build_message(instance, is_period_specific)
        }
    
    def _build_message(self, instance: dict, is_period_specific: bool) -> str:
        """Construye mensaje descriptivo del resultado"""
        if is_period_specific:
            dy = instance.get('dividend_yield_period_percentage', 0)
            dy_ann = instance.get('dividend_yield_annualized_percentage', 0)
            if dy_ann:
                return f"Dividend Yield: {dy:.2f}% (período) | {dy_ann:.2f}% (anualizado) - {instance.get('performance_level', 'N/A').replace('_', ' ').title()}"
            return f"Dividend Yield: {dy:.2f}% - {instance.get('performance_level', 'N/A').replace('_', ' ').title()}"
        else:
            dy_ann = instance.get('dividend_yield_annualized_percentage', 0)
            return f"Dividend Yield anualizado: {dy_ann:.2f}% - {instance.get('performance_level', 'N/A').replace('_', ' ').title()}"        
                
        
class AssetDividendYieldMovingAverageSerializer(serializers.Serializer):
    """
    Serializer para calcular Dividend Yield Promedio Móvil de un asset.
    
    Dividend Yield Promedio = Σ(Dividend Yields) / Número de Períodos
    
    Example:
        >>> data = {'asset_id': 1, 'months_back': 12}
    """
    
    asset_id = serializers.IntegerField(
        required=True,
        help_text="ID del asset"
    )
    
    months_back = serializers.IntegerField(
        default=12,
        required=False,
        min_value=1,
        max_value=60,
        help_text="Meses hacia atrás para análisis (default: 12)"
    )
    
    include_monthly_breakdown = serializers.BooleanField(
        default=True,
        required=False,
        help_text="Incluir desglose mensual"
    )
    
    def validate_asset_id(self, value):
        """Validar que el asset existe y tiene tokens"""
        try:
            asset = Asset.objects.get(id=value)
            
            if asset.status != 'active':
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no está activo"
                )
            
            if not hasattr(asset, 'total_tokens_issued') or asset.total_tokens_issued <= 0:
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no tiene tokens emitidos"
                )
            
            if not asset.acquisition_value or asset.acquisition_value <= 0:
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no tiene un valor de adquisición válido"
                )
            
            return value
            
        except Asset.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un asset con el ID {value}"
            )
    
    def create(self, validated_data):
        """Calcular Dividend Yield Promedio Móvil usando el facade"""
        asset_id = validated_data.pop('asset_id')
        
        try:
            asset = Asset.objects.get(id=asset_id)
            facade = AssetKPIFacade(asset)
            
            result = facade.calculate_dividend_yield_moving_average(**validated_data)
            
            return result
            
        except Exception as e:
            raise serializers.ValidationError(
                f"Error calculando Dividend Yield Promedio Móvil: {str(e)}"
            )
    
    def to_representation(self, instance):
        """Formatear la respuesta"""
        
        if isinstance(instance, dict) and 'error' in instance:
            return {
                'success': False,
                'error': instance['error'],
                'asset_id': instance.get('asset_id'),
                'asset_code': instance.get('asset_code')
            }
        
        return {
            'success': True,
            'data': {
                'asset_info': {
                    'asset_id': instance.get('asset_id'),
                    'asset_code': instance.get('asset_code'),
                    'asset_name': instance.get('asset_name'),
                    'fund_id': instance.get('fund_id'),
                    'fund_name': instance.get('fund_name')
                },
                'dividend_yield_average': {
                    'average_dividend_yield_percentage': instance.get('average_dividend_yield_percentage'),
                    'average_dividend_yield_annualized_percentage': instance.get('average_dividend_yield_annualized_percentage'),
                    'valor_compra_token': instance.get('valor_compra_token'),
                    'interpretation': instance.get('interpretation'),
                    'consistency_rating': instance.get('consistency_rating')
                },
                'statistical_metrics': instance.get('statistical_metrics', {}),
                'trend_analysis': instance.get('trend_analysis', {}),
                'period_info': {
                    'period_analyzed': instance.get('period_analyzed'),
                    'months_analyzed': instance.get('months_analyzed')
                },
                'asset_metrics': instance.get('asset_metrics', {}),
                'monthly_breakdown': instance.get('monthly_breakdown'),
                'calculation_date': instance.get('calculation_date')
            },
            'message': self._build_message(instance)
        }
    
    def _build_message(self, instance: dict) -> str:
        """Construye mensaje descriptivo del resultado"""
        avg = instance.get('average_dividend_yield_annualized_percentage', 0)
        consistency = instance.get('consistency_rating', 'N/A').title()
        trend = instance.get('trend_analysis', {}).get('trend_direction', 'stable').title()
        
        return f"Dividend Yield Promedio: {avg:.2f}% anualizado | Consistencia: {consistency} | Tendencia: {trend}"        
        
        
class AssetIRRCalculationSerializer(serializers.Serializer):
    """
    Serializer para calcular TIR (Tasa Interna de Retorno / IRR) de un asset.
    
    TIR = Retorno anualizado que iguala el valor presente de flujos de caja a la inversión
    
    Example:
        >>> # Con parámetros manuales
        >>> data = {
        ...     'asset_id': 1,
        ...     'annual_dividends_per_token': 400,
        ...     'exit_price_per_token': 4600,
        ...     'holding_period_years': 5
        ... }
        >>> 
        >>> # Con datos históricos
        >>> data = {
        ...     'asset_id': 1,
        ...     'use_historical_dividends': True,
        ...     'holding_period_years': 5
        ... }
    """
    
    asset_id = serializers.IntegerField(
        required=True,
        help_text="ID del asset"
    )
    
    annual_dividends_per_token = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Dividendos anuales por token (opcional, se calcula automáticamente)"
    )
    
    exit_price_per_token = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Precio de venta final del token (opcional, se calcula usando Output Value)"
    )
    
    holding_period_years = serializers.IntegerField(
        default=5,
        required=False,
        min_value=1,
        max_value=30,
        help_text="Años de tenencia (default: 5)"
    )
    
    use_historical_dividends = serializers.BooleanField(
        default=False,
        required=False,
        help_text="Usar dividendos históricos en lugar de proyectados"
    )
    
    def validate_asset_id(self, value):
        """Validar que el asset existe y tiene datos necesarios"""
        try:
            asset = Asset.objects.get(id=value)
            
            if asset.status != 'active':
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no está activo"
                )
            
            if not hasattr(asset, 'total_tokens_issued') or asset.total_tokens_issued <= 0:
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no tiene tokens emitidos"
                )
            
            if not asset.acquisition_value or asset.acquisition_value <= 0:
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no tiene un valor de adquisición válido"
                )
            
            return value
            
        except Asset.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un asset con el ID {value}"
            )
    
    def create(self, validated_data):
        """Calcular TIR usando el facade"""
        asset_id = validated_data.pop('asset_id')
        
        try:
            asset = Asset.objects.get(id=asset_id)
            facade = AssetKPIFacade(asset)
            
            result = facade.calculate_irr(**validated_data)
            
            return result
            
        except Exception as e:
            raise serializers.ValidationError(
                f"Error calculando TIR: {str(e)}"
            )
    
    def to_representation(self, instance):
        """Formatear la respuesta"""
        
        if isinstance(instance, dict) and 'error' in instance:
            return {
                'success': False,
                'error': instance['error'],
                'asset_id': instance.get('asset_id'),
                'asset_code': instance.get('asset_code'),
                'cash_flows': instance.get('cash_flows')
            }
        
        return {
            'success': True,
            'data': {
                'asset_info': {
                    'asset_id': instance.get('asset_id'),
                    'asset_code': instance.get('asset_code'),
                    'asset_name': instance.get('asset_name'),
                    'fund_id': instance.get('fund_id'),
                    'fund_name': instance.get('fund_name')
                },
                'irr_metrics': {
                    'irr_percentage': instance.get('irr_percentage'),
                    'irr_decimal': instance.get('irr_decimal'),
                    'interpretation': instance.get('interpretation'),
                    'performance_level': instance.get('performance_level')
                },
                'investment_parameters': instance.get('investment_parameters', {}),
                'cash_flows': instance.get('cash_flows', {}),
                'return_metrics': instance.get('return_metrics', {}),
                'annual_breakdown': instance.get('annual_breakdown', []),
                'asset_metrics': instance.get('asset_metrics', {}),
                'calculation_date': instance.get('calculation_date'),
                'calculation_method': instance.get('calculation_method'),
                'data_source': instance.get('data_source')
            },
            'message': f"TIR calculado: {instance.get('irr_percentage', 0):.2f}% anualizado - {instance.get('performance_level', 'N/A').replace('_', ' ').title()}"
        }        
     
        
class AssetMOICCalculationSerializer(serializers.Serializer):
    """
    Serializer para calcular MOIC (Múltiplo de Inversión) de un asset.
    
    MOIC = Total Recibido / Inversión Inicial
    
    Example:
        >>> # Con parámetros manuales
        >>> data = {
        ...     'asset_id': 1,
        ...     'total_dividends_received': 2000,
        ...     'exit_price_per_token': 4600,
        ...     'holding_period_years': 5
        ... }
        >>> 
        >>> # Con datos históricos
        >>> data = {
        ...     'asset_id': 1,
        ...     'use_historical_dividends': True,
        ...     'holding_period_years': 5
        ... }
    """
    
    asset_id = serializers.IntegerField(
        required=True,
        help_text="ID del asset"
    )
    
    total_dividends_received = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Suma total de dividendos recibidos (opcional, se calcula automáticamente)"
    )
    
    exit_price_per_token = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Precio de venta final del token (opcional, se calcula usando Output Value)"
    )
    
    holding_period_years = serializers.IntegerField(
        default=5,
        required=False,
        min_value=1,
        max_value=30,
        help_text="Años de tenencia (default: 5)"
    )
    
    use_historical_dividends = serializers.BooleanField(
        default=False,
        required=False,
        help_text="Usar dividendos históricos en lugar de proyectados"
    )
    
    def validate_asset_id(self, value):
        """Validar que el asset existe y tiene datos necesarios"""
        try:
            asset = Asset.objects.get(id=value)
            
            if asset.status != 'active':
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no está activo"
                )
            
            if not hasattr(asset, 'total_tokens_issued') or asset.total_tokens_issued <= 0:
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no tiene tokens emitidos"
                )
            
            if not asset.acquisition_value or asset.acquisition_value <= 0:
                raise serializers.ValidationError(
                    f"El asset '{asset.name}' no tiene un valor de adquisición válido"
                )
            
            return value
            
        except Asset.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un asset con el ID {value}"
            )
    
    def create(self, validated_data):
        """Calcular MOIC usando el facade"""
        asset_id = validated_data.pop('asset_id')
        
        try:
            asset = Asset.objects.get(id=asset_id)
            facade = AssetKPIFacade(asset)
            
            result = facade.calculate_moic(**validated_data)
            
            return result
            
        except Exception as e:
            raise serializers.ValidationError(
                f"Error calculando MOIC: {str(e)}"
            )
    
    def to_representation(self, instance):
        """Formatear la respuesta"""
        
        if isinstance(instance, dict) and 'error' in instance:
            return {
                'success': False,
                'error': instance['error'],
                'asset_id': instance.get('asset_id'),
                'asset_code': instance.get('asset_code')
            }
        
        return {
            'success': True,
            'data': {
                'asset_info': {
                    'asset_id': instance.get('asset_id'),
                    'asset_code': instance.get('asset_code'),
                    'asset_name': instance.get('asset_name'),
                    'fund_id': instance.get('fund_id'),
                    'fund_name': instance.get('fund_name')
                },
                'moic_metrics': {
                    'moic': instance.get('moic'),
                    'moic_display': instance.get('moic_display'),
                    'interpretation': instance.get('interpretation'),
                    'performance_level': instance.get('performance_level'),
                    'outcome': instance.get('outcome')
                },
                'investment_components': instance.get('investment_components', {}),
                'return_metrics': instance.get('return_metrics', {}),
                'asset_metrics': instance.get('asset_metrics', {}),
                'calculation_date': instance.get('calculation_date'),
                'data_source': instance.get('data_source')
            },
            'message': f"MOIC calculado: {instance.get('moic_display', '0.00x')} - {instance.get('outcome', 'N/A').replace('_', ' ').title()}"
        }        
        
        