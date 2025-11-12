from rest_framework import serializers
from apps.fund.models.core import Fund
from apps.fund.services.kpis.facade import FundKPIFacade


class FundNOICalculationSerializer(serializers.Serializer):
    """
    Serializer para calcular NOI de un fondo.
    
    Uso:
    - Sin parámetros adicionales: Últimos 12 meses
    - Con period_year y period_month: Período específico
    - Con months_back: Rango personalizado
    
    Example:
        >>> # NOI últimos 12 meses
        >>> data = {'fund_id': 1}
        >>> serializer = FundNOICalculationSerializer(data=data, context={'request': request})
        >>> 
        >>> # NOI de junio 2024
        >>> data = {'fund_id': 1, 'period_year': 2024, 'period_month': 6}
        >>> serializer = FundNOICalculationSerializer(data=data, context={'request': request})
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
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
    
    def validate_fund_id(self, value):
        """Validar que el fondo existe"""
        try:
            fund = Fund.objects.get(id=value)
            
            # Validar que el fondo esté activo
            if fund.status != 'active':
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no está activo"
                )
            
            return value
            
        except Fund.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un fondo con el ID {value}"
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
        fund_id = validated_data.pop('fund_id')
        
        try:
            fund = Fund.objects.get(id=fund_id)
            facade = FundKPIFacade(fund)
            
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
                'fund_id': instance.get('fund_id'),
                'fund_code': instance.get('fund_code')
            }
        
        # ✅ CORRECCIÓN: Usar los nombres exactos que devuelve la strategy
        total_income = instance.get('total_operating_income')
        total_expenses = instance.get('total_operating_expenses')  # ✅ Con 's'
        noi = instance.get('net_operating_income')  # ✅ Nombre exacto
        
        # Respuesta exitosa
        return {
            'success': True,
            'data': {
                'fund_info': {
                    'fund_id': instance.get('fund_id'),
                    'fund_code': instance.get('fund_code'),
                    'fund_name': instance.get('fund_name'),
                    'status': instance.get('status')
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
                    'total_operating_income': total_income,
                    'total_operating_expenses': total_expenses,  # ✅ Corregido
                    'net_operating_income': noi,  # ✅ Corregido
                    'noi_margin_percentage': instance.get('noi_margin_percentage'),
                    'average_monthly_noi': instance.get('average_monthly_noi')
                },
                'fund_metrics': instance.get('fund_metrics') or instance.get('per_area_metrics', {}),
                'calculation_date': instance.get('calculation_date')
            },
            'message': f"NOI calculado exitosamente: ${noi or 0:,.2f} COP"  # ✅ Usar la variable noi
        }


class FundNOISummarySerializer(serializers.Serializer):
    """
    Serializer para obtener resumen de NOI con análisis de tendencias.
    
    Example:
        >>> data = {'fund_id': 1, 'months': 12}
        >>> serializer = FundNOISummarySerializer(data=data, context={'request': request})
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
    )
    
    months = serializers.IntegerField(
        default=12,
        required=False,
        min_value=1,
        max_value=60,
        help_text="Número de meses a analizar (default: 12)"
    )
    
    def validate_fund_id(self, value):
        """Validar que el fondo existe"""
        try:
            fund = Fund.objects.get(id=value)
            
            if fund.status != 'active':
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no está activo"
                )
            
            return value
            
        except Fund.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un fondo con el ID {value}"
            )
    
    def create(self, validated_data):
        """Obtener resumen de NOI"""
        fund_id = validated_data.pop('fund_id')
        months = validated_data.get('months', 12)
        
        try:
            fund = Fund.objects.get(id=fund_id)
            facade = FundKPIFacade(fund)
            
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
                'fund_id': instance.get('fund_id')
            }
        
        return {
            'success': True,
            'data': {
                'fund_info': {
                    'fund_id': instance.get('fund_id'),
                    'fund_code': instance.get('fund_code'),
                    'fund_name': instance.get('fund_name')
                },
                'noi_summary': {
                    'total_noi': instance.get('total_noi') or instance.get('annual_noi'),
                    'average_monthly_noi': instance.get('average_monthly_noi'),
                    'noi_margin_percentage': instance.get('noi_margin_percentage'),
                    'months_with_data': instance.get('months_with_data')
                },
                'performance_metrics': instance.get('performance_metrics', {}),
                'trend_analysis': instance.get('trend_analysis', {}),
                'monthly_breakdown': instance.get('monthly_breakdown', []),
                'fund_metrics': instance.get('fund_metrics', {})
            }
        }
        
        
class FundCapRateCalculationSerializer(serializers.Serializer):
    """
    Serializer para calcular Cap Rate de un fondo.
    
    Cap Rate = (NOI Anual / Valor del Fondo) * 100
    
    Example:
        >>> data = {'fund_id': 1}
        >>> serializer = FundCapRateCalculationSerializer(data=data)
        >>> serializer.is_valid()
        >>> result = serializer.save()
        >>> print(f"Cap Rate: {result['cap_rate']}%")
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
    )
    
    def validate_fund_id(self, value):
        """Validar que el fondo existe y tiene datos necesarios"""
        try:
            fund = Fund.objects.get(id=value)
            
            # Validar que el fondo esté activo
            if fund.status != 'active':
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no está activo"
                )
            
            # Validar que tenga acquisition_value
            if not hasattr(fund, 'acquisition_value') or not fund.acquisition_value or fund.acquisition_value <= 0:
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no tiene un valor de adquisición válido"
                )
            
            return value
            
        except Fund.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un fondo con el ID {value}"
            )
    
    def create(self, validated_data):
        """Calcular Cap Rate usando el facade"""
        fund_id = validated_data.pop('fund_id')
        
        try:
            fund = Fund.objects.get(id=fund_id)
            facade = FundKPIFacade(fund)
            
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
                'fund_id': instance.get('fund_id'),
                'fund_code': instance.get('fund_code')
            }
        
        # ✅ Extraer datos de las estructuras anidadas
        calculation_components = instance.get('calculation_components', {})
        analysis = instance.get('analysis', {})
        noi_metrics = instance.get('noi_metrics', {})
        market_comparison = instance.get('market_comparison', {})
        per_unit_metrics = instance.get('per_unit_metrics', {})
        per_area_metrics = instance.get('per_area_metrics', {})
        
        # Respuesta exitosa
        return {
            'success': True,
            'data': {
                'fund_info': {
                    'fund_id': instance.get('fund_id'),
                    'fund_code': instance.get('fund_code'),
                    'fund_name': instance.get('fund_name'),
                    'status': instance.get('status')
                },
                'cap_rate_metrics': {
                    'cap_rate': instance.get('cap_rate'),
                    'cap_rate_display': instance.get('cap_rate_display'),
                    'noi_anual': calculation_components.get('noi_anual'),  # ✅ Desde calculation_components
                    'fund_value': calculation_components.get('fund_value'),  # ✅ Desde calculation_components
                    'value_source': calculation_components.get('value_source'),
                    'interpretation': analysis.get('interpretation'),  # ✅ Desde analysis
                    'risk_level': analysis.get('risk_level'),  # ✅ Desde analysis
                    'performance_rating': analysis.get('performance_rating')  # ✅ Desde analysis
                },
                'noi_metrics': {
                    'noi_margin_percentage': noi_metrics.get('noi_margin_percentage'),
                    'total_operating_income': noi_metrics.get('total_operating_income'),
                    'total_operating_expense': noi_metrics.get('total_operating_expense')
                },
                'market_comparison': {
                    'market_cap_rate': market_comparison.get('market_cap_rate'),
                    'spread_to_market': market_comparison.get('spread_to_market'),
                    'relative_performance': market_comparison.get('relative_performance')
                },
                'per_unit_metrics': {
                    'total_units_issued': per_unit_metrics.get('total_units_issued'),
                    'noi_per_unit': per_unit_metrics.get('noi_per_unit'),
                    'fund_value_per_unit': per_unit_metrics.get('fund_value_per_unit')
                },
                'per_area_metrics': per_area_metrics if per_area_metrics else None,
                'calculation_date': instance.get('calculation_date'),
                'noi_period': instance.get('noi_period')
            },
            'message': f"Cap Rate calculado: {instance.get('cap_rate', 0):.2f}% - {analysis.get('risk_level', 'N/A').title()} Risk"
        }
        
        
class FundOutputValueCalculationSerializer(serializers.Serializer):
    """
    Serializer para calcular Output Value (Valor de Salida) de un fondo.
    
    Output Value = NOI Proyectado / Cap Rate de Salida
    
    Example:
        >>> # Cálculo automático
        >>> data = {'fund_id': 1, 'projection_years': 5}
        >>> 
        >>> # Cálculo con valores específicos
        >>> data = {
        ...     'fund_id': 1,
        ...     'projected_noi': 100000000,
        ...     'exit_cap_rate': 6.5
        ... }
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
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
    
    def validate_fund_id(self, value):
        """Validar que el fondo existe"""
        try:
            fund = Fund.objects.get(id=value)
            
            if fund.status != 'active':
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no está activo"
                )
            
            return value
            
        except Fund.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un fondo con el ID {value}"
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
        fund_id = validated_data.pop('fund_id')
        
        try:
            fund = Fund.objects.get(id=fund_id)
            facade = FundKPIFacade(fund)
            
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
                'fund_id': instance.get('fund_id'),
                'fund_code': instance.get('fund_code')
            }
        
        return {
            'success': True,
            'data': {
                'fund_info': {
                    'fund_id': instance.get('fund_id'),
                    'fund_code': instance.get('fund_code'),
                    'fund_name': instance.get('fund_name'),
                    'status': instance.get('status')
                },
                'output_value_metrics': {
                    'output_value': instance.get('output_value'),
                    'projected_noi': instance.get('projected_noi'),
                    'exit_cap_rate': instance.get('exit_cap_rate')
                },
                'projection_context': instance.get('projection_context', {}),
                'return_metrics': instance.get('return_metrics', {}),
                'fund_metrics': instance.get('fund_metrics', {}),
                'calculation_date': instance.get('calculation_date'),
                'calculation_method': instance.get('calculation_method')
            },
            'message': f"Valor de Salida calculado: ${instance.get('output_value', 0):,.2f} COP (MOIC: {instance.get('return_metrics', {}).get('moic', 0):.2f}x)"
        }
        
# ========================================
# FREE CASH FLOW SERIALIZER
# ========================================

class FundFreeCashFlowCalculationSerializer(serializers.Serializer):
    """
    Serializer para calcular Free Cash Flow (Flujo de Caja Libre) de un fondo.
    
    FCF = NOI + Ingresos no operativos - Gastos no operativos - CAPEX - Deuda
    
    Example:
        >>> # Cálculo de últimos 12 meses (default)
        >>> data = {'fund_id': 1}
        >>> 
        >>> # Cálculo de período específico
        >>> data = {
        ...     'fund_id': 1,
        ...     'period_year': 2024,
        ...     'period_month': 6
        ... }
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
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
    
    def validate_fund_id(self, value):
        """Validar que el fondo existe y está activo"""
        try:
            fund = Fund.objects.get(id=value)
            
            if fund.status != 'active':
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no está activo"
                )
            
            return value
            
        except Fund.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un fondo con el ID {value}"
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
        fund_id = validated_data.pop('fund_id')
        
        try:
            fund = Fund.objects.get(id=fund_id)
            facade = FundKPIFacade(fund)
            
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
                'fund_id': instance.get('fund_id'),
                'fund_code': instance.get('fund_code')
            }
        
        # Respuesta exitosa
        return {
            'success': True,
            'data': {
                'fund_info': {
                    'fund_id': instance.get('fund_id'),
                    'fund_code': instance.get('fund_code'),
                    'fund_name': instance.get('fund_name'),
                    'status': instance.get('status')
                },
                'fcf_metrics': {
                    'free_cash_flow': instance.get('free_cash_flow') or instance.get('total_fcf'),
                    'fcf_per_unit': instance.get('fcf_per_unit'),
                    'fcf_margin_percentage': instance.get('fcf_margin_percentage'),
                    'average_monthly_fcf': instance.get('average_monthly_fcf')
                },
                'fcf_components': instance.get('fcf_components', {}),
                'period_info': {
                    'period_type': instance.get('period_type'),
                    'period_year': instance.get('period_year'),
                    'period_month': instance.get('period_month'),
                    'period_quarter': instance.get('period_quarter'),
                    'period_display': instance.get('period_display') or instance.get('period_analyzed'),
                    'months_with_data': instance.get('months_with_data')
                },
                'unit_info': {
                    'total_units': instance.get('amount_tokens')
                },
                'monthly_breakdown': instance.get('monthly_breakdown', []) if instance.get('monthly_breakdown') else None,
                'calculation_date': instance.get('calculation_date')
            },
            'message': self._build_message(instance)
        }
    
    def _build_message(self, instance: dict) -> str:
        """Construye mensaje descriptivo del resultado"""
        fcf = instance.get('free_cash_flow') or instance.get('total_fcf', 0)
        fcf_per_unit = instance.get('fcf_per_unit', 0)
        
        if fcf > 0:
            return f"FCF positivo: ${fcf:,.2f} COP (${fcf_per_unit:,.2f} por unidad). El fondo genera efectivo disponible para distribución."
        elif fcf < 0:
            return f"FCF negativo: ${fcf:,.2f} COP. El fondo requiere inyección de capital."
        else:
            return "FCF neutro: El fondo está en punto de equilibrio."        
   
        
class FundCashOnCashCalculationSerializer(serializers.Serializer):
    """
    Serializer para calcular Cash on Cash Return de un fondo.
    
    Cash on Cash = (FCF Anual / Capital Invertido) × 100
    
    Example:
        >>> data = {'fund_id': 1}
        >>> serializer = FundCashOnCashCalculationSerializer(data=data)
        >>> serializer.is_valid()
        >>> result = serializer.save()
        >>> print(f"Cash on Cash: {result['cash_on_cash_percentage']}%")
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
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
    
    def validate_fund_id(self, value):
        """Validar que el fondo existe y tiene datos necesarios"""
        try:
            fund = Fund.objects.get(id=value)
            
            # Validar que el fondo esté activo
            if fund.status != 'active':
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no está activo"
                )
            
            # Validar que tenga acquisition_value
            if not hasattr(fund, 'acquisition_value') or not fund.acquisition_value or fund.acquisition_value <= 0:
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no tiene un valor de adquisición válido (capital invertido)"
                )
            
            return value
            
        except Fund.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un fondo con el ID {value}"
            )
    
    def create(self, validated_data):
        """Calcular Cash on Cash usando el facade"""
        fund_id = validated_data.pop('fund_id')
        
        try:
            fund = Fund.objects.get(id=fund_id)
            facade = FundKPIFacade(fund)
            
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
                'fund_id': instance.get('fund_id'),
                'fund_code': instance.get('fund_code')
            }
        
        # Respuesta exitosa
        return {
            'success': True,
            'data': {
                'fund_info': {
                    'fund_id': instance.get('fund_id'),
                    'fund_code': instance.get('fund_code'),
                    'fund_name': instance.get('fund_name'),
                    'status': instance.get('status')
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
                'fund_metrics': instance.get('fund_metrics', {}),
                'monthly_breakdown': instance.get('monthly_breakdown'),
                'calculation_date': instance.get('calculation_date'),
                'period_analyzed': instance.get('period_analyzed'),
                'calculation_note': instance.get('calculation_note')
            },
            'message': f"Cash on Cash calculado: {instance.get('cash_on_cash_percentage', 0):.2f}% - {instance.get('performance_level', 'N/A').replace('_', ' ').title()}"
        }       
       
       
class FundDividendYieldCalculationSerializer(serializers.Serializer):
    """
    Serializer para calcular Dividend Yield de un fondo.
    
    Dividend Yield = (Dividendo por Unidad / Valor Compra Unidad) × 100
    
    Example:
        >>> # Anualizado
        >>> data = {'fund_id': 1}
        >>> 
        >>> # Período específico
        >>> data = {
        ...     'fund_id': 1,
        ...     'period_year': 2024,
        ...     'period_month': 12
        ... }
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
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
    
    def validate_fund_id(self, value):
        """Validar que el fondo existe y tiene unidades"""
        try:
            fund = Fund.objects.get(id=value)
            
            if fund.status != 'active':
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no está activo"
                )
            
            if not hasattr(fund, 'amount_tokens') or fund.amount_tokens <= 0:
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no tiene unidades emitidas"
                )
            
            if not hasattr(fund, 'acquisition_value') or not fund.acquisition_value or fund.acquisition_value <= 0:
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no tiene un valor de adquisición válido"
                )
            
            return value
            
        except Fund.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un fondo con el ID {value}"
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
        fund_id = validated_data.pop('fund_id')
        
        try:
            fund = Fund.objects.get(id=fund_id)
            facade = FundKPIFacade(fund)
            
            result = facade.calculate_dividend_yield(**validated_data)
            
            return result
            
        except Exception as e:
            raise serializers.ValidationError(
                f"Error calculando Dividend Yield: {str(e)}"
            )
        
    def to_representation(self, instance):
        """Formatear la respuesta de salida"""
        
        # Si hay error
        if isinstance(instance, dict) and 'error' in instance:
            return {
                'success': False,
                'error': instance['error'],
                'fund_id': instance.get('fund_id'),
                'fund_code': instance.get('fund_code')
            }
        
        # ✅ Extraer estructuras anidadas
        period_info = instance.get('period_info', {})
        dividend_yield_metrics = instance.get('dividend_yield_metrics', {})
        period_metrics = instance.get('period_metrics', {})
        distribution_metrics = instance.get('distribution_metrics', {})
        fund_metrics = instance.get('fund_metrics', {})
        
        # Respuesta exitosa
        return {
            'success': True,
            'data': {
                'fund_info': {
                    'fund_id': instance.get('fund_id'),
                    'fund_code': instance.get('fund_code'),
                    'fund_name': instance.get('fund_name'),
                    'status': instance.get('status')
                },
                'dividend_yield_metrics': {
                    'dividend_yield_period_percentage': dividend_yield_metrics.get('dividend_yield_period_percentage'),
                    'dividend_yield_annualized_percentage': dividend_yield_metrics.get('dividend_yield_annualized_percentage'),
                    'dividend_yield_monthly_avg_percentage': dividend_yield_metrics.get('dividend_yield_monthly_avg_percentage'),
                    'dividendo_por_unidad': dividend_yield_metrics.get('dividendo_por_unidad'),
                    'valor_actual_token': dividend_yield_metrics.get('valor_actual_token'),  # ✅ Nombre correcto
                    'interpretation': dividend_yield_metrics.get('interpretation'),
                    'performance_level': dividend_yield_metrics.get('performance_level')
                },
                'period_info': {
                    'period_type': period_info.get('period_type'),
                    'period_year': period_info.get('period_year'),
                    'period_month': period_info.get('period_month'),
                    'period_quarter': period_info.get('period_quarter'),
                    'period_display': period_info.get('period_display'),
                    'start_period': period_info.get('start_period'),
                    'end_period': period_info.get('end_period')
                },
                'period_metrics': {
                    'total_dividendo_12m': period_metrics.get('total_dividendo_12m'),
                    'distributions_count': period_metrics.get('distributions_count'),
                    'average_distribution_per_token': period_metrics.get('average_distribution_per_token'),
                    'total_distribution_amount_12m': period_metrics.get('total_distribution_amount_12m')
                },
                'distribution_metrics': distribution_metrics if distribution_metrics else None,
                'fund_metrics': {
                    'price_per_unit': fund_metrics.get('price_per_unit'),
                    'total_tokens_issued': fund_metrics.get('total_tokens_issued')
                },
                'calculation_date': instance.get('calculation_date')
            },
            'message': f"Dividend Yield anualizado: {dividend_yield_metrics.get('dividend_yield_annualized_percentage', 0):.2f}% - {dividend_yield_metrics.get('performance_level', 'N/A').title()}"
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
                
        
class FundDividendYieldMovingAverageSerializer(serializers.Serializer):
    """
    Serializer para calcular Dividend Yield Promedio Móvil de un fondo.
    
    Dividend Yield Promedio = Σ(Dividend Yields) / Número de Períodos
    
    Example:
        >>> data = {'fund_id': 1, 'months_back': 12}
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
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
    
    def validate_fund_id(self, value):
        """Validar que el fondo existe y tiene unidades"""
        try:
            fund = Fund.objects.get(id=value)
            
            if fund.status != 'active':
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no está activo"
                )
            
            if not hasattr(fund, 'amount_tokens') or fund.amount_tokens <= 0:
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no tiene unidades emitidas"
                )
            
            if not hasattr(fund, 'acquisition_value') or not fund.acquisition_value or fund.acquisition_value <= 0:
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no tiene un valor de adquisición válido"
                )
            
            return value
            
        except Fund.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un fondo con el ID {value}"
            )
    
    def create(self, validated_data):
        """Calcular Dividend Yield Promedio Móvil usando el facade"""
        fund_id = validated_data.pop('fund_id')
        
        try:
            fund = Fund.objects.get(id=fund_id)
            facade = FundKPIFacade(fund)
            
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
                'fund_id': instance.get('fund_id'),
                'fund_code': instance.get('fund_code')
            }
        
        # ✅ Extraer estructuras anidadas
        dividend_yield_metrics = instance.get('dividend_yield_metrics', {})
        statistical_metrics = instance.get('statistical_metrics', {})
        trend_analysis = instance.get('trend_analysis', {})
        period_info = instance.get('period_info', {})
        fund_metrics = instance.get('fund_metrics', {})
        
        return {
            'success': True,
            'data': {
                'fund_info': {
                    'fund_id': instance.get('fund_id'),
                    'fund_code': instance.get('fund_code'),
                    'fund_name': instance.get('fund_name'),
                    'status': instance.get('status')
                },
                'dividend_yield_average': {
                    'average_dividend_yield_percentage': dividend_yield_metrics.get('average_dividend_yield_percentage'),
                    'average_dividend_yield_annualized_percentage': dividend_yield_metrics.get('average_dividend_yield_annualized_percentage'),
                    'valor_actual_token': dividend_yield_metrics.get('valor_actual_token'),  # ✅ Nombre correcto
                    'interpretation': dividend_yield_metrics.get('interpretation'),
                    'consistency_rating': dividend_yield_metrics.get('consistency_rating')
                },
                'statistical_metrics': {
                    'max_dividend_yield_percentage': statistical_metrics.get('max_dividend_yield_percentage'),
                    'min_dividend_yield_percentage': statistical_metrics.get('min_dividend_yield_percentage'),
                    'range_percentage': statistical_metrics.get('range_percentage'),
                    'standard_deviation_percentage': statistical_metrics.get('standard_deviation_percentage'),
                    'coefficient_of_variation_percentage': statistical_metrics.get('coefficient_of_variation_percentage'),
                    'variance': statistical_metrics.get('variance')
                },
                'trend_analysis': {
                    'first_half_average_percentage': trend_analysis.get('first_half_average_percentage'),
                    'second_half_average_percentage': trend_analysis.get('second_half_average_percentage'),
                    'trend_percentage': trend_analysis.get('trend_percentage'),
                    'trend_direction': trend_analysis.get('trend_direction')
                },
                'period_info': {
                    'period_analyzed': period_info.get('period_analyzed'),
                    'start_period': period_info.get('start_period'),
                    'end_period': period_info.get('end_period'),
                    'months_analyzed': period_info.get('months_analyzed')
                },
                'fund_metrics': {
                    'price_per_unit': fund_metrics.get('price_per_unit'),
                    'total_tokens_issued': fund_metrics.get('total_tokens_issued')
                },
                'monthly_breakdown': instance.get('monthly_breakdown'),
                'calculation_date': instance.get('calculation_date')
            },
            'message': self._build_message(instance, dividend_yield_metrics)
        }

    def _build_message(self, instance: dict, dividend_yield_metrics: dict) -> str:
        """Construye mensaje descriptivo del resultado"""
        avg = dividend_yield_metrics.get('average_dividend_yield_annualized_percentage', 0)
        consistency = dividend_yield_metrics.get('consistency_rating', 'N/A').title()
        trend = instance.get('trend_analysis', {}).get('trend_direction', 'stable').title()
        
        return f"Dividend Yield Promedio: {avg:.2f}% anualizado | Consistencia: {consistency} | Tendencia: {trend}"      
        
        
class FundIRRCalculationSerializer(serializers.Serializer):
    """
    Serializer para calcular TIR (Tasa Interna de Retorno / IRR) de un fondo.
    
    TIR = Retorno anualizado que iguala el valor presente de flujos de caja a la inversión
    
    Example:
        >>> # Con parámetros manuales
        >>> data = {
        ...     'fund_id': 1,
        ...     'annual_dividends_per_unit': 80000,
        ...     'exit_price_per_unit': 1100000,
        ...     'holding_period_years': 5
        ... }
        >>> 
        >>> # Con datos históricos
        >>> data = {
        ...     'fund_id': 1,
        ...     'use_historical_dividends': True,
        ...     'holding_period_years': 5
        ... }
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
    )
    
    annual_dividends_per_unit = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Dividendos anuales por unidad (opcional, se calcula automáticamente)"
    )
    
    exit_price_per_unit = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Precio de venta final de la unidad (opcional, se calcula usando Output Value)"
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
    
    def validate_fund_id(self, value):
        """Validar que el fondo existe y tiene datos necesarios"""
        try:
            fund = Fund.objects.get(id=value)
            
            if fund.status != 'active':
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no está activo"
                )
            
            if not hasattr(fund, 'amount_tokens') or fund.amount_tokens <= 0:
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no tiene unidades emitidas"
                )
            
            if not hasattr(fund, 'acquisition_value') or not fund.acquisition_value or fund.acquisition_value <= 0:
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no tiene un valor de adquisición válido"
                )
            
            return value
            
        except Fund.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un fondo con el ID {value}"
            )
    
    def create(self, validated_data):
        """Calcular TIR usando el facade"""
        fund_id = validated_data.pop('fund_id')
        
        try:
            fund = Fund.objects.get(id=fund_id)
            facade = FundKPIFacade(fund)
            
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
                'fund_id': instance.get('fund_id'),
                'fund_code': instance.get('fund_code'),
                'cash_flows': instance.get('cash_flows')
            }
        
        return {
            'success': True,
            'data': {
                'fund_info': {
                    'fund_id': instance.get('fund_id'),
                    'fund_code': instance.get('fund_code'),
                    'fund_name': instance.get('fund_name'),
                    'status': instance.get('status')
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
                'fund_metrics': instance.get('fund_metrics', {}),
                'calculation_date': instance.get('calculation_date'),
                'calculation_method': instance.get('calculation_method'),
                'data_source': instance.get('data_source')
            },
            'message': f"TIR calculado: {instance.get('irr_percentage', 0):.2f}% anualizado - {instance.get('performance_level', 'N/A').replace('_', ' ').title()}"
        }        
     
        
class FundMOICCalculationSerializer(serializers.Serializer):
    """
    Serializer para calcular MOIC (Múltiplo de Inversión) de un fondo.
    
    MOIC = Total Recibido / Inversión Inicial
    
    Example:
        >>> # Con parámetros manuales
        >>> data = {
        ...     'fund_id': 1,
        ...     'total_dividends_received': 400000,
        ...     'exit_price_per_unit': 1150000,
        ...     'holding_period_years': 5
        ... }
        >>> 
        >>> # Con datos históricos
        >>> data = {
        ...     'fund_id': 1,
        ...     'use_historical_dividends': True,
        ...     'holding_period_years': 5
        ... }
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
    )
    
    total_dividends_received = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Suma total de dividendos recibidos (opcional, se calcula automáticamente)"
    )
    
    exit_price_per_unit = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Precio de venta final de la unidad (opcional, se calcula usando Output Value)"
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
    
    def validate_fund_id(self, value):
        """Validar que el fondo existe y tiene datos necesarios"""
        try:
            fund = Fund.objects.get(id=value)
            
            if fund.status != 'active':
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no está activo"
                )
            
            if not hasattr(fund, 'amount_tokens') or fund.amount_tokens <= 0:
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no tiene unidades emitidas"
                )
            
            if not hasattr(fund, 'acquisition_value') or not fund.acquisition_value or fund.acquisition_value <= 0:
                raise serializers.ValidationError(
                    f"El fondo '{fund.name}' no tiene un valor de adquisición válido"
                )
            
            return value
            
        except Fund.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un fondo con el ID {value}"
            )
    
    def create(self, validated_data):
        """Calcular MOIC usando el facade"""
        fund_id = validated_data.pop('fund_id')
        
        try:
            fund = Fund.objects.get(id=fund_id)
            facade = FundKPIFacade(fund)
            
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
                'fund_id': instance.get('fund_id'),
                'fund_code': instance.get('fund_code')
            }
        
        return {
            'success': True,
            'data': {
                'fund_info': {
                    'fund_id': instance.get('fund_id'),
                    'fund_code': instance.get('fund_code'),
                    'fund_name': instance.get('fund_name'),
                    'status': instance.get('status')
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
                'fund_metrics': instance.get('fund_metrics', {}),
                'calculation_date': instance.get('calculation_date'),
                'data_source': instance.get('data_source')
            },
            'message': f"MOIC calculado: {instance.get('moic_display', '0.00x')} - {instance.get('outcome', 'N/A').replace('_', ' ').title()}"
        }