from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from ..models.accounting import (
    AccountCategory,
    AccountingBalance,
    AccountingEntry,
    AccountingImportBatch,
    AccountingImportError,
    AccountingPeriod,
    FinancialSummary,
    Accountability
)


# ============================================================================
# ACCOUNT CATEGORY SERIALIZERS
# ============================================================================

class AccountCategorySerializer(serializers.ModelSerializer):
    """Serializer básico para categorías contables"""
    
    class Meta:
        model = AccountCategory
        fields = '__all__'


class AccountCategoryListSerializer(serializers.ModelSerializer):
    """Serializer para listado de categorías con info del padre"""
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    category_type_display = serializers.CharField(source='get_category_type_display', read_only=True)
    
    class Meta:
        model = AccountCategory
        fields = [
            'id', 'code', 'name', 'category_type', 'category_type_display',
            'description', 'parent', 'parent_name', 'fund', 'is_active', 
            'display_order', 'created_at'
        ]


class AccountCategoryTreeSerializer(serializers.ModelSerializer):
    """Serializer recursivo para árbol de categorías"""
    subcategories = serializers.SerializerMethodField()
    category_type_display = serializers.CharField(source='get_category_type_display', read_only=True)
    
    class Meta:
        model = AccountCategory
        fields = [
            'id', 'code', 'name', 'category_type', 'category_type_display',
            'description', 'is_active', 'display_order', 'subcategories'
        ]
    
    def get_subcategories(self, obj):
        children = obj.subcategories.filter(is_active=True).order_by('display_order', 'code')
        return AccountCategoryTreeSerializer(children, many=True).data


# ============================================================================
# ACCOUNTING PERIOD SERIALIZERS
# ============================================================================

class AccountingPeriodSerializer(serializers.ModelSerializer):
    """Serializer básico para períodos contables"""
    
    class Meta:
        model = AccountingPeriod
        fields = '__all__'


class AccountingPeriodListSerializer(serializers.ModelSerializer):
    """Serializer para listado de períodos"""
    period_display = serializers.ReadOnlyField()
    period_status_display = serializers.CharField(source='get_period_status_display', read_only=True)
    fund_name = serializers.CharField(source='fund.name', read_only=True)
    
    class Meta:
        model = AccountingPeriod
        fields = [
            'id', 'fund', 'fund_name', 'year', 'month', 'period_display',
            'start_date', 'end_date', 'period_status', 'period_status_display',
            'closed_at', 'closed_by', 'notes', 'created_at'
        ]


class AccountingPeriodCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear períodos contables"""
    
    class Meta:
        model = AccountingPeriod
        fields = ['fund', 'year', 'month', 'start_date', 'end_date', 'notes']
        validators = [
            UniqueTogetherValidator(
                queryset=AccountingPeriod.objects.all(),
                fields=['fund', 'year', 'month'],
                message="Ya existe un periodo contable para este año/mes en este activo."
            )
        ]
    
    def validate(self, data):
        # Validar que no exista un período duplicado
        if AccountingPeriod.objects.filter(
            fund=data['fund'],
            year=data['year'],
            month=data['month']
        ).exists():
            raise serializers.ValidationError(
                f"Ya existe un período para {data['year']}/{data['month']:02d} en este fondo."
            )
        
        # Validar que start_date < end_date
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError(
                "La fecha de inicio debe ser anterior a la fecha de fin."
            )
        
        return data


# ============================================================================
# ACCOUNTING ENTRY SERIALIZERS
# ============================================================================

class AccountingEntrySerializer(serializers.ModelSerializer):
    """Serializer básico para registros contables"""
    
    class Meta:
        model = AccountingEntry
        fields = '__all__'
        read_only_fields = ['created_at', 'posted_at', 'posted_by']


class AccountingEntryListSerializer(serializers.ModelSerializer):
    """Serializer para listado de registros contables"""
    operational_type = serializers.CharField(source='category.operational_type', read_only=True)
    category_code = serializers.CharField(source='category.code', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    entry_type_display = serializers.CharField(source='get_entry_type_display', read_only=True)
    entry_status_display = serializers.CharField(source='get_entry_status_display', read_only=True)
    entry_source_display = serializers.CharField(source='get_entry_source_display', read_only=True)
    period_display = serializers.CharField(source='period.period_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = AccountingEntry
        fields = [
            'id', 'entry_date', 'fund', 'period', 'period_display',
            'operational_type', 'category', 'category_code', 'category_name',
            'entry_type', 'entry_type_display', 'amount', 'description',
            'entry_status', 'entry_status_display',
            'entry_source', 'entry_source_display',
            'external_reference', 'document_number',
            'third_party_name', 'third_party_id',
            'created_by', 'created_by_name',
            'created_at'
        ]


class AccountingEntryCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear registros contables"""
    
    class Meta:
        model = AccountingEntry
        fields = [
            'fund', 'period', 'category', 'entry_date', 'entry_type',
            'amount', 'description', 'external_reference', 'document_number',
            'third_party_name', 'third_party_id',
            'metadata'
        ]
    
    def validate(self, data):
        # Validar que el período esté abierto
        if data['period'].period_status != 'open':
            raise serializers.ValidationError(
                f"El período {data['period']} está {data['period'].get_period_status_display()}. "
                "Solo se pueden crear registros en períodos abiertos."
            )
        
        # Validar que la fecha esté dentro del período
        if not (data['period'].start_date <= data['entry_date'] <= data['period'].end_date):
            raise serializers.ValidationError(
                f"La fecha {data['entry_date']} no está dentro del período "
                f"({data['period'].start_date} - {data['period'].end_date})."
            )
        
        # Validar que la categoría pertenezca al mismo fondo
        if data['category'].fund != data['fund']:
            raise serializers.ValidationError(
                "La categoría seleccionada no pertenece a este fondo."
            )
        
        return data
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        validated_data['entry_source'] = 'manual'
        validated_data['entry_status'] = 'draft'
        return super().create(validated_data)


class AccountingEntryPostSerializer(serializers.Serializer):
    """Serializer para contabilizar (post) registros"""
    entry_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="Lista de IDs de registros a contabilizar"
    )


# ============================================================================
# ACCOUNTING BALANCE SERIALIZERS
# ============================================================================

class AccountingBalanceSerializer(serializers.ModelSerializer):
    """Serializer básico para saldos contables"""
    
    class Meta:
        model = AccountingBalance
        fields = '__all__'


class AccountingBalanceListSerializer(serializers.ModelSerializer):
    """Serializer para listado de saldos"""
    category_code = serializers.CharField(source='category.code', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_type = serializers.CharField(source='category.category_type', read_only=True)
    period_display = serializers.CharField(source='period.period_display', read_only=True)
    net_movement = serializers.SerializerMethodField()
    
    class Meta:
        model = AccountingBalance
        fields = [
            'id', 'fund', 'period', 'period_display',
            'category', 'category_code', 'category_name', 'category_type',
            'opening_balance', 'total_debits', 'total_credits',
            'net_movement', 'closing_balance', 'last_calculated_at'
        ]
    
    def get_net_movement(self, obj):
        return obj.total_debits - obj.total_credits


# ============================================================================
# ACCOUNTING IMPORT SERIALIZERS
# ============================================================================

class AccountingImportBatchSerializer(serializers.ModelSerializer):
    """Serializer básico para lotes de importación"""
    
    class Meta:
        model = AccountingImportBatch
        fields = '__all__'
        read_only_fields = [
            'created_at', 'started_at', 'completed_at', 'imported_by',
            'total_rows', 'processed_rows', 'successful_rows', 'failed_rows',
            'validation_errors'
        ]


class AccountingImportBatchListSerializer(serializers.ModelSerializer):
    """Serializer para listado de importaciones"""
    import_type_display = serializers.CharField(source='get_import_type_display', read_only=True)
    import_status_display = serializers.CharField(source='get_import_status_display', read_only=True)
    imported_by_name = serializers.CharField(source='imported_by.get_full_name', read_only=True)
    fund_name = serializers.CharField(source='fund.name', read_only=True)
    success_rate = serializers.ReadOnlyField()
    error_count = serializers.IntegerField(source='errors.count', read_only=True)
    
    class Meta:
        model = AccountingImportBatch
        fields = [
            'id', 'fund', 'fund_name', 'original_filename',
            'import_type', 'import_type_display',
            'import_status', 'import_status_display',
            'data_start_date', 'data_end_date',
            'total_rows', 'processed_rows', 'successful_rows', 'failed_rows',
            'success_rate', 'error_count',
            'imported_by', 'imported_by_name',
            'created_at', 'started_at', 'completed_at', 'notes'
        ]


class AccountingImportBatchCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear lotes de importación"""
    
    class Meta:
        model = AccountingImportBatch
        fields = ['fund', 'file', 'import_type', 'column_mapping', 'notes']
    
    def validate_file(self, value):
        # Validar extensión del archivo
        if not value.name.endswith(('.xlsx', '.xls')):
            raise serializers.ValidationError(
                "Solo se permiten archivos Excel (.xlsx, .xls)"
            )
        
        # Validar tamaño (máximo 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError(
                "El archivo no puede superar los 10MB"
            )
        
        return value
    
    def create(self, validated_data):
        validated_data['imported_by'] = self.context['request'].user
        validated_data['original_filename'] = validated_data['file'].name
        return super().create(validated_data)


class AccountingImportBatchDetailSerializer(AccountingImportBatchListSerializer):
    """Serializer detallado para importaciones (incluye errores)"""
    errors = serializers.SerializerMethodField()
    
    class Meta(AccountingImportBatchListSerializer.Meta):
        fields = AccountingImportBatchListSerializer.Meta.fields + [
            'file', 'column_mapping', 'validation_errors', 'errors'
        ]
    
    def get_errors(self, obj):
        errors = obj.errors.all()[:50]  # Limitar a 50 errores
        return AccountingImportErrorSerializer(errors, many=True).data


# ============================================================================
# ACCOUNTING IMPORT ERROR SERIALIZERS
# ============================================================================

class AccountingImportErrorSerializer(serializers.ModelSerializer):
    """Serializer para errores de importación"""
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    
    class Meta:
        model = AccountingImportError
        fields = [
            'id', 'batch', 'row_number', 'column_name',
            'severity', 'severity_display', 'error_code',
            'error_message', 'original_value', 'is_resolved'
        ]


# ============================================================================
# FINANCIAL SUMMARY SERIALIZERS
# ============================================================================

class FinancialSummarySerializer(serializers.ModelSerializer):
    """Serializer básico para resúmenes financieros"""
    
    class Meta:
        model = FinancialSummary
        fields = '__all__'


class FinancialSummaryListSerializer(serializers.ModelSerializer):
    """Serializer para listado de resúmenes financieros"""
    summary_type_display = serializers.CharField(source='get_summary_type_display', read_only=True)
    summary_status_display = serializers.CharField(source='get_summary_status_display', read_only=True)
    period_display = serializers.CharField(source='period.period_display', read_only=True)
    fund_name = serializers.CharField(source='fund.name', read_only=True)
    
    class Meta:
        model = FinancialSummary
        fields = [
            'id', 'fund', 'fund_name', 'period', 'period_display',
            'summary_type', 'summary_type_display',
            'summary_status', 'summary_status_display',
            'total_assets', 'total_liabilities', 'total_equity',
            'total_income', 'total_expenses', 'net_result',
            'generated_by', 'generated_at', 'notes', 'created_at'
        ]


class FinancialSummaryDetailSerializer(FinancialSummaryListSerializer):
    """Serializer detallado con datos completos"""
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    
    class Meta(FinancialSummaryListSerializer.Meta):
        fields = FinancialSummaryListSerializer.Meta.fields + ['data', 'generated_by_name']
        
        
# ============================================================================
# ACCOUNTABILITY SERIALIZERS
# ============================================================================
class AccountabilitySerializer(serializers.ModelSerializer):
    """Serializer para Accountability"""
    
    class Meta:
        model = Accountability
        fields = '__all__'
        read_only_fields = ['id', 'created_at']