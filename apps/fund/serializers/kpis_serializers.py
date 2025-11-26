from rest_framework import serializers
from apps.fund.models.core import Fund
from apps.fund.services.kpis.facade import FundKPIFacade
from apps.fund.models.membership import FundInvestment


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
        
        # ✅ Detectar si es período único o últimos 12 meses
        is_12_months = 'total_noi_12m' in instance
        
        if is_12_months:
            # Últimos 12 meses
            total_income = instance.get('total_operating_income_12m')
            total_expenses = instance.get('total_operating_expenses_12m')
            noi = instance.get('total_noi_12m')
        else:
            # Período único
            total_income = instance.get('total_operating_income')
            total_expenses = instance.get('total_operating_expenses')
            noi = instance.get('net_operating_income')
        
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
                    'total_operating_expenses': total_expenses,
                    'net_operating_income': noi,
                    'noi_margin_percentage': instance.get('noi_margin_percentage'),
                    'average_monthly_noi': instance.get('average_monthly_noi')
                },
                'fund_metrics': instance.get('fund_metrics') or instance.get('per_area_metrics', {}),
                'calculation_date': instance.get('calculation_date')
            },
            'message': f"NOI calculado exitosamente: ${noi or 0:,.2f} COP"
        }


class FundValuationCalculationSerializer(serializers.Serializer):
    """
    Serializer para calcular Valor del Fondo basado en Cap Rate.
    
    Formula: Valor del Fondo = (NOI Anual / Cap Rate) × 100
    
    Example:
        >>> data = {
        ...     'fund_id': 1,
        ...     'target_cap_rate': 7.0
        ... }
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
    )
    
    target_cap_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=True,
        help_text="Cap Rate objetivo en porcentaje (ej: 7.0 para 7%)"
    )
    
    months_back = serializers.IntegerField(
        required=False,
        default=12,
        min_value=1,
        max_value=36,
        help_text="Meses hacia atrás para calcular NOI (default: 12)"
    )
    
    noi_override = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="NOI manual (opcional, si se omite usa NOI calculado)"
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
    
    def validate_target_cap_rate(self, value):
        """Validar cap rate objetivo"""
        if value <= 0:
            raise serializers.ValidationError(
                "Cap Rate debe ser mayor a cero"
            )
        
        if value > 50:
            raise serializers.ValidationError(
                "Cap Rate parece excesivamente alto (>50%)"
            )
        
        return value
    
    def validate_noi_override(self, value):
        """Validar NOI manual"""
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "NOI debe ser mayor a cero"
            )
        
        return value
    
    def create(self, validated_data):
        """Calcular valoración del fondo usando el facade"""
        fund_id = validated_data.pop('fund_id')
        
        try:
            fund = Fund.objects.get(id=fund_id)
            facade = FundKPIFacade(fund)
            
            result = facade.calculate_fund_valuation(**validated_data)
            
            return result
            
        except Exception as e:
            raise serializers.ValidationError(
                f"Error calculando valoración del fondo: {str(e)}"
            )
    
    def to_representation(self, instance):
        """Formatear la respuesta"""
        
        if 'error' in instance:
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
                'valuation_metrics': {
                    'fund_value': instance.get('fund_value'),
                    'fund_value_display': instance.get('fund_value_display')
                },
                'calculation_components': instance.get('calculation_components'),
                'current_value_comparison': instance.get('current_value_comparison'),
                'valuation_scenarios': instance.get('valuation_scenarios'),
                'per_unit_metrics': instance.get('per_unit_metrics'),
                'per_area_metrics': instance.get('per_area_metrics'),
                'interpretation': instance.get('interpretation'),
                'valuation_level': instance.get('valuation_level'),
                'calculation_date': instance.get('calculation_date')
            },
            'message': f"Valoración calculada: {instance.get('fund_value_display')} (Cap Rate: {instance.get('calculation_components', {}).get('target_cap_rate')}%)"
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
    
    Output Value = (NOI Proyectado / Cap Rate de Salida) × 100
    
    Modos de uso:
    1. Crecimiento uniforme: Un solo valor de tasa de crecimiento
    2. Crecimiento variable: Tasas diferentes por año
    3. Sin proyección: NOI estabilizado (últimos 12 meses)
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
    )
    
    # ✅ EXIT CAP RATE (REQUERIDO)
    exit_cap_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=True,  # ✅ REQUERIDO (digitado por usuario)
        help_text="Cap Rate de salida esperado en % (REQUERIDO, ej: 7.5)"
    )
    
    current_cap_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Cap Rate actual del fondo en % (opcional, para calcular acquisition_value)"
    )    
    
    # ✅ NOI MANUAL (OPCIONAL)
    projected_noi = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="NOI estabilizado manual (opcional, si se omite se calcula automáticamente)"
    )
    
    # ✅ MODO PROYECCIÓN
    use_projection = serializers.BooleanField(
        default=False,
        required=False,
        help_text="Si usar proyección con crecimiento (default: False)"
    )
    
    # ✅ AÑO INICIAL DE PROYECCIÓN
    projection_start_year = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=2000,
        max_value=2100,
        help_text="Año base para empezar proyección (ej: 2024, opcional)"
    )
    
    # ✅ AÑOS A PROYECTAR
    projection_years = serializers.IntegerField(
        default=5,
        required=False,
        min_value=1,
        max_value=30,
        help_text="Número de años a proyectar (default: 5)"
    )
    
    # ✅ OPCIÓN 1: CRECIMIENTO UNIFORME (SIMPLE)
    annual_noi_growth_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Tasa de crecimiento uniforme % para TODOS los años (ej: 3.5 = 3.5% anual)"
    )
    
    # ✅ OPCIÓN 2: CRECIMIENTO VARIABLE (AVANZADO)
    growth_rates_by_year = serializers.DictField(
        child=serializers.DecimalField(max_digits=5, decimal_places=2),
        required=False,
        allow_null=True,
        help_text="OPCIONAL: Dict con tasas específicas por año. Ejemplo: {'2025': 3.0, '2026': 3.5, '2027': 4.0}"
    )
    
    # ========================================
    # VALIDACIONES
    # ========================================
    
    def validate_current_cap_rate(self, value):
        """Validar cap rate actual"""
        if value is not None:
            if value <= 0:
                raise serializers.ValidationError(
                    "Cap Rate actual debe ser mayor a cero"
                )
            if value > 50:
                raise serializers.ValidationError(
                    "Cap Rate actual parece demasiado alto (>50%)"
                )
        return value    
    
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
    
    def validate_exit_cap_rate(self, value):
        """Validar cap rate de salida"""
        if value <= 0:
            raise serializers.ValidationError(
                "Cap Rate debe ser mayor a cero"
            )
        
        if value > 50:
            raise serializers.ValidationError(
                "Cap Rate parece demasiado alto (>50%)"
            )
        
        return value
    
    def validate_projected_noi(self, value):
        """Validar NOI proyectado"""
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "NOI proyectado debe ser mayor a cero"
            )
        return value
    
    def validate_annual_noi_growth_rate(self, value):
        """Validar tasa de crecimiento uniforme"""
        if value is not None:
            if value < -50 or value > 50:
                raise serializers.ValidationError(
                    "Tasa de crecimiento debe estar entre -50% y 50%"
                )
        return value
    
    def validate_growth_rates_by_year(self, value):
        """Validar formato del diccionario de tasas por año"""
        if value:
            for year, rate in value.items():
                # Validar año
                try:
                    year_int = int(year)
                    if year_int < 2000 or year_int > 2100:
                        raise serializers.ValidationError(
                            f"Año {year} fuera de rango válido (2000-2100)"
                        )
                except ValueError:
                    raise serializers.ValidationError(
                        f"Clave '{year}' no es un año válido"
                    )
                
                # Validar tasa
                if rate < -50 or rate > 50:
                    raise serializers.ValidationError(
                        f"Tasa de crecimiento para año {year} ({rate}%) debe estar entre -50% y 50%"
                    )
        
        return value
    
    def validate_projection_start_year(self, value):
        """Validar año de inicio de proyección"""
        if value is not None:
            from django.utils import timezone
            current_year = timezone.now().year
            
            if value < 2000:
                raise serializers.ValidationError(
                    "Año de inicio debe ser 2000 o posterior"
                )
            
            if value > current_year + 10:
                raise serializers.ValidationError(
                    f"Año de inicio no puede ser mayor a {current_year + 10}"
                )
        
        return value
    
    def validate(self, attrs):
        """Validaciones a nivel de objeto"""
        use_projection = attrs.get('use_projection', False)
        projection_start_year = attrs.get('projection_start_year')
        annual_noi_growth_rate = attrs.get('annual_noi_growth_rate')
        growth_rates_by_year = attrs.get('growth_rates_by_year')
        
        # Si usa proyección, validar coherencia
        if use_projection:
            # Si no especifica año de inicio, usar año actual
            if projection_start_year is None:
                from django.utils import timezone
                attrs['projection_start_year'] = timezone.now().year
            
            # Si especifica ambos modos de crecimiento, dar error
            if annual_noi_growth_rate is not None and growth_rates_by_year is not None:
                raise serializers.ValidationError({
                    'detail': 'No puede especificar annual_noi_growth_rate y growth_rates_by_year simultáneamente. Use solo uno.'
                })
        
        return attrs
    
    # ========================================
    # CÁLCULO
    # ========================================
    
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
    
    # ========================================
    # REPRESENTACIÓN
    # ========================================
    
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
        
        # ✅ Extraer estructuras anidadas
        calculation_components = instance.get('calculation_components', {})
        calculation_context = instance.get('calculation_context', {})
        return_metrics = instance.get('return_metrics', {})
        per_unit_metrics = instance.get('per_unit_metrics', {})
        portfolio_metrics = instance.get('portfolio_metrics', {})
        market_comparison = instance.get('market_comparison', {})
        
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
                'output_value_metrics': {
                    'output_value': instance.get('output_value'),
                    'output_value_display': instance.get('output_value_display')
                },
                'calculation_components': {
                    'projected_noi': calculation_components.get('projected_noi'),
                    'exit_cap_rate': calculation_components.get('exit_cap_rate'),
                    'exit_cap_rate_source': calculation_components.get('exit_cap_rate_source'),
                    'noi_source': calculation_components.get('noi_source'),
                    'use_projection': calculation_components.get('use_projection'),
                    'projection_start_year': calculation_components.get('projection_start_year'),
                    'projection_years': calculation_components.get('projection_years')
                },
                'calculation_context': {
                    'method': calculation_context.get('method'),
                    'noi_current_12m': calculation_context.get('noi_current_12m'),
                    'annual_noi_growth_rate': calculation_context.get('annual_noi_growth_rate'),
                    'growth_rates_by_year': calculation_context.get('growth_rates_by_year'),
                    'current_cap_rate': calculation_context.get('current_cap_rate'),
                    'cap_rate_spread': calculation_context.get('cap_rate_spread'),
                    'description': calculation_context.get('description')
                },
                'projection_breakdown': instance.get('projection_breakdown', []),
                'return_metrics': {
                    'acquisition_value': return_metrics.get('acquisition_value'),
                    'capital_gain_loss': return_metrics.get('capital_gain_loss'),
                    'capital_gain_percentage': return_metrics.get('capital_gain_percentage'),
                    'moic': return_metrics.get('moic'),
                    'interpretation': return_metrics.get('interpretation')
                },
                'per_unit_metrics': {
                    'total_units_issued': per_unit_metrics.get('total_units_issued'),
                    'output_value_per_unit': per_unit_metrics.get('output_value_per_unit'),
                    'initial_price_per_unit': per_unit_metrics.get('initial_price_per_unit'),
                    'unit_price_appreciation': per_unit_metrics.get('unit_price_appreciation'),
                    'unit_price_appreciation_pct': per_unit_metrics.get('unit_price_appreciation_pct')
                },
                'portfolio_metrics': {
                    'total_area_m2': portfolio_metrics.get('total_area_m2'),
                    'output_value_per_m2': portfolio_metrics.get('output_value_per_m2')
                },
                'market_comparison': market_comparison,
                'interpretation': instance.get('interpretation'),
                'valuation_assessment': instance.get('valuation_assessment'),
                'calculation_date': instance.get('calculation_date')
            },
            'message': self._build_message(instance, calculation_context, return_metrics)
        }
    
    def _build_message(
        self, 
        instance: dict, 
        calculation_context: dict,
        return_metrics: dict
    ) -> str:
        """Construye mensaje descriptivo del resultado"""
        output_value = instance.get('output_value', 0)
        exit_cap_rate = instance.get('calculation_components', {}).get('exit_cap_rate', 0)
        moic = return_metrics.get('moic', 0)
        method = calculation_context.get('method', 'unknown')
        
        # Mensaje base
        base_msg = f"Output Value: ${output_value:,.2f} COP (Cap Rate: {exit_cap_rate:.2f}%)"
        
        # Agregar MOIC si está disponible
        if moic:
            base_msg += f" | MOIC: {moic:.2f}x"
        
        # Agregar método de cálculo
        if method == 'projected_uniform':
            growth_rate = calculation_context.get('annual_noi_growth_rate', 0)
            base_msg += f" | Proyección uniforme ({growth_rate:.2f}% anual)"
        elif method == 'projected_variable':
            base_msg += " | Proyección con crecimiento variable"
        elif method == 'stabilized':
            base_msg += " | NOI estabilizado (sin proyección)"
        
        return base_msg
        
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
                    'total_units': instance.get('total_units')
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
            if not hasattr(fund, 'initial_capex') or not fund.initial_capex or fund.initial_capex <= 0:
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
       
       
# apps/fund/serializers/kpis_serializers.py

class FundDividendYieldCalculationSerializer(serializers.Serializer):
    """
    Serializer para calcular Dividend Yield de una inversión específica.
    
    Dividend Yield = (Dividendo Pagado / Valor Compra Inicial) × 100
    
    Example:
        >>> # Rendimiento acumulado total
        >>> data = {
        ...     'fund_id': 1,
        ...     'investment_id': 5
        ... }
        >>> 
        >>> # Rendimiento de un mes específico
        >>> data = {
        ...     'fund_id': 1,
        ...     'investment_id': 5,
        ...     'period_year': 2024,
        ...     'period_month': 12
        ... }
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
    )
    
    investment_id = serializers.IntegerField(
        required=True,
        help_text="ID de la inversión (FundInvestment)"
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
        help_text="Año específico (opcional, si no se proporciona calcula acumulado total)"
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
        required=False,
        allow_null=True,
        min_value=1,
        max_value=60,
        help_text="Número de meses hacia atrás (opcional, ej: 12 para últimos 12 meses)"
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
    
    def validate_investment_id(self, value):
        """Validar que la inversión existe"""
        try:
            investment = FundInvestment.objects.get(id=value)
            return value
            
        except FundInvestment.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe una inversión con el ID {value}"
            )
    
    def validate(self, attrs):
        """Validaciones cruzadas"""
        fund_id = attrs.get('fund_id')
        investment_id = attrs.get('investment_id')
        period_type = attrs.get('period_type')
        period_year = attrs.get('period_year')
        period_month = attrs.get('period_month')
        period_quarter = attrs.get('period_quarter')
        
        # ✅ CORRECCIÓN: Validar que la inversión pertenezca al fondo
        try:
            investment = FundInvestment.objects.select_related('application__fund').get(id=investment_id)
            
            # ✅ ACCESO CORRECTO: investment.application.fund.id
            if investment.application.fund.id != fund_id:
                raise serializers.ValidationError({
                    'investment_id': f'La inversión {investment_id} no pertenece al fondo {fund_id}'
                })
        except FundInvestment.DoesNotExist:
            pass  # Ya se validó en validate_investment_id
        
        # Si especifica año, validar coherencia con period_type
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
                'fund_code': instance.get('fund_code'),
                'investment_id': instance.get('investment_id')
            }
        
        # ✅ Extraer estructuras anidadas
        investment_info = instance.get('investment_info', {})
        period_info = instance.get('period_info', {})
        dividend_yield_metrics = instance.get('dividend_yield_metrics', {})
        distribution_metrics = instance.get('distribution_metrics', {})
        cumulative_metrics = instance.get('cumulative_metrics', {})
        
        # Respuesta exitosa
        response = {
            'success': True,
            'data': {
                'fund_info': {
                    'fund_id': instance.get('fund_id'),
                    'fund_code': instance.get('fund_code'),
                    'fund_name': instance.get('fund_name'),
                    'status': instance.get('status')
                },
                'investment_info': investment_info,
                'period_info': period_info,
                'dividend_yield_metrics': dividend_yield_metrics,
                'calculation_date': instance.get('calculation_date')
            }
        }
        
        # Agregar métricas opcionales según el tipo de cálculo
        if distribution_metrics:
            response['data']['distribution_metrics'] = distribution_metrics
        
        if cumulative_metrics:
            response['data']['cumulative_metrics'] = cumulative_metrics
        
        # Mensaje personalizado
        if period_info.get('period_type') == 'cumulative':
            message = f"Dividend Yield Acumulado: {dividend_yield_metrics.get('dividend_yield_total_percentage', 0):.2f}% total | {dividend_yield_metrics.get('dividend_yield_annualized_percentage', 0):.2f}% anualizado"
        else:
            message = f"Dividend Yield: {dividend_yield_metrics.get('dividend_yield_period_percentage', 0):.2f}% ({period_info.get('period_display', 'N/A')})"
        
        response['message'] = message
        
        return response       
                
        
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
    Serializer para calcular TIR (IRR) de una inversión específica del usuario.
    
    TIR = Tasa interna de retorno considerando:
    - Inversión inicial
    - Distribuciones reales recibidas
    - Valor de salida de los tokens
    
    Example:
        >>> # TIR con precio actual
        >>> data = {
        ...     'fund_id': 1,
        ...     'investment_id': 123
        ... }
        >>> 
        >>> # TIR con precio de salida específico
        >>> data = {
        ...     'fund_id': 1,
        ...     'investment_id': 123,
        ...     'exit_price_per_unit': 1100000
        ... }
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
    )
    
    investment_id = serializers.IntegerField(
        required=True,
        help_text="ID de la inversión (FundInvestment)"
    )
    
    exit_price_per_unit = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Precio de salida/venta por unidad (opcional, usa precio actual si no se provee)"
    )
    
    exit_date = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Fecha de salida/venta (opcional, usa fecha actual si no se provee)"
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
    
    def validate(self, attrs):
        """Validar que la inversión pertenece al fondo"""
        fund_id = attrs.get('fund_id')
        investment_id = attrs.get('investment_id')
        
        try:
            investment = FundInvestment.objects.select_related(
                'application__fund'
            ).get(id=investment_id)
            
            if investment.application.fund.id != fund_id:
                raise serializers.ValidationError({
                    'investment_id': f'La inversión {investment_id} no pertenece al fondo {fund_id}'
                })
            
            return attrs
            
        except FundInvestment.DoesNotExist:
            raise serializers.ValidationError({
                'investment_id': f'No existe una inversión con el ID {investment_id}'
            })
    
    def create(self, validated_data):
        """Calcular TIR usando el facade"""
        fund_id = validated_data.pop('fund_id')
        
        try:
            fund = Fund.objects.get(id=fund_id)
            facade = FundKPIFacade(fund)
            
            result = facade.calculate_irr(**validated_data)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error calculando TIR: {str(e)}',
                'fund_id': fund_id,
                'investment_id': validated_data.get('investment_id')
            }
    
    def to_representation(self, instance):
        """Formatear la respuesta de salida"""
        
        # Si hay error
        if isinstance(instance, dict) and 'error' in instance:
            return {
                'success': False,
                'error': instance['error'],
                'fund_id': instance.get('fund_id'),
                'fund_code': instance.get('fund_code'),
                'investment_id': instance.get('investment_id')
            }
        
        # Extraer estructuras anidadas
        investment_info = instance.get('investment_info', {})
        investment_parameters = instance.get('investment_parameters', {})
        cash_flows_simple = instance.get('cash_flows_simple', {})
        return_metrics = instance.get('return_metrics', {})
        
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
                'investment_info': {
                    'investment_id': investment_info.get('investment_id'),
                    'user_id': investment_info.get('user_id'),
                    'user_email': investment_info.get('user_email'),
                    'units_owned': investment_info.get('units_owned'),
                    'investment_date': investment_info.get('investment_date'),
                    'exit_date': investment_info.get('exit_date'),
                    'holding_period_days': investment_info.get('holding_period_days'),
                    'holding_period_years': investment_info.get('holding_period_years')
                },
                'irr_metrics': {
                    'irr_percentage': instance.get('irr_percentage'),
                    'irr_decimal': instance.get('irr_decimal'),
                    'performance_level': instance.get('performance_level')
                },
                'investment_parameters': {
                    'initial_investment': investment_parameters.get('initial_investment'),
                    'total_distributions_received': investment_parameters.get('total_distributions_received'),
                    'exit_price_per_unit': investment_parameters.get('exit_price_per_unit'),
                    'exit_value_total': investment_parameters.get('exit_value_total')
                },
                'cash_flows_detailed': instance.get('cash_flows_detailed', []),
                'cash_flows_simple': {
                    'period_0_investment': cash_flows_simple.get('period_0_investment'),
                    'annual_cash_flows': cash_flows_simple.get('annual_cash_flows', []),
                    'all_cash_flows': cash_flows_simple.get('all_cash_flows', [])
                },
                'return_metrics': {
                    'total_distributions_received': return_metrics.get('total_distributions_received'),
                    'capital_gain_loss': return_metrics.get('capital_gain_loss'),
                    'total_return': return_metrics.get('total_return'),
                    'moic': return_metrics.get('moic'),
                    'roi_percentage': return_metrics.get('roi_percentage'),
                    'distributions_count': return_metrics.get('distributions_count')
                },
                'annual_breakdown': instance.get('annual_breakdown', []),
                'interpretation': instance.get('interpretation'),
                'calculation_date': instance.get('calculation_date'),
                'calculation_method': instance.get('calculation_method'),
                'data_source': instance.get('data_source')
            },
            'message': self._build_message(instance)
        }
    
    def _build_message(self, instance: dict) -> str:
        """Construye mensaje descriptivo del resultado"""
        irr = instance.get('irr_percentage', 0)
        investment_info = instance.get('investment_info', {})
        return_metrics = instance.get('return_metrics', {})
        
        holding_years = investment_info.get('holding_period_years', 0)
        moic = return_metrics.get('moic', 0)
        performance = instance.get('performance_level', 'unknown')
        
        performance_text = {
            'excellent': 'Excelente',
            'very_good': 'Muy bueno',
            'good': 'Bueno',
            'moderate': 'Moderado',
            'poor': 'Bajo',
            'negative': 'Negativo'
        }.get(performance, 'Desconocido')
        
        return (
            f"TIR: {irr:.2f}% ({performance_text}) | "
            f"MOIC: {moic:.2f}x | "
            f"Período: {holding_years:.2f} años"
        )    
     
        
class FundMOICCalculationSerializer(serializers.Serializer):
    """
    Serializer para calcular MOIC (Múltiplo de Inversión) de una inversión específica.
    
    MOIC = (Distribuciones Recibidas + Valor Actual) / Inversión Inicial
    
    Example:
        >>> # MOIC total (distribuciones + valor actual)
        >>> data = {
        ...     'fund_id': 1,
        ...     'investment_id': 5,
        ...     'include_unrealized_value': True
        ... }
        >>> 
        >>> # MOIC solo distribuciones realizadas
        >>> data = {
        ...     'fund_id': 1,
        ...     'investment_id': 5,
        ...     'include_unrealized_value': False
        ... }
    """
    
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo"
    )
    
    investment_id = serializers.IntegerField(
        required=True,
        help_text="ID de la inversión (FundInvestment)"
    )
    
    exit_price_per_unit = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Precio de salida/venta del token (opcional, usa precio actual si no se provee)"
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
    
    def validate(self, attrs):
        """Validar que la inversión pertenece al fondo"""
        fund_id = attrs.get('fund_id')
        investment_id = attrs.get('investment_id')
        
        try:
            investment = FundInvestment.objects.select_related(
                'application__fund'
            ).get(id=investment_id)
            
            if investment.application.fund.id != fund_id:
                raise serializers.ValidationError({
                    'investment_id': f'La inversión {investment_id} no pertenece al fondo {fund_id}'
                })
            
            return attrs
            
        except FundInvestment.DoesNotExist:
            raise serializers.ValidationError({
                'investment_id': f'No existe una inversión con el ID {investment_id}'
            })
    
    def create(self, validated_data):
        """Calcular MOIC usando el facade"""
        fund_id = validated_data.pop('fund_id')
        
        try:
            fund = Fund.objects.get(id=fund_id)
            facade = FundKPIFacade(fund)
            
            result = facade.calculate_moic(**validated_data)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error calculando MOIC: {str(e)}',
                'fund_id': fund_id,
                'investment_id': validated_data.get('investment_id')
            }
    
    def to_representation(self, instance):
        """Formatear la respuesta de salida"""
        
        # Si hay error
        if isinstance(instance, dict) and 'error' in instance:
            return {
                'success': False,
                'error': instance['error'],
                'fund_id': instance.get('fund_id'),
                'fund_code': instance.get('fund_code'),
                'investment_id': instance.get('investment_id')
            }
        
        # ✅ Extraer estructuras anidadas
        investment_info = instance.get('investment_info', {})
        moic_metrics = instance.get('moic_metrics', {})
        investment_components = instance.get('investment_components', {})
        return_metrics = instance.get('return_metrics', {})
        distributions_summary = instance.get('distributions_summary', {})
        
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
                'investment_info': investment_info,
                'moic_metrics': moic_metrics,
                'investment_components': investment_components,
                'return_metrics': return_metrics,
                'distributions_summary': distributions_summary,
                'interpretation': instance.get('interpretation'),
                'performance_level': instance.get('performance_level'),
                'outcome': instance.get('outcome'),
                'calculation_date': instance.get('calculation_date'),
                'calculation_method': instance.get('calculation_method')
            },
            'message': f"MOIC calculado: {moic_metrics.get('moic', 0):.2f}x | Retorno: {return_metrics.get('return_percentage', 0):.2f}% | {instance.get('outcome', 'N/A').title()}"
        }