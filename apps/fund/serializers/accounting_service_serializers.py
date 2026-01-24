"""
Serializers para el módulo de contabilidad.
"""

from rest_framework import serializers
from decimal import Decimal

from apps.fund.models.core import (
    Fund,
    TrustAgreement
)
from apps.fund.models.accounting import (
    AccountCategory,
    AccountingPeriod,
    AccountingEntry,
    InvoiceRecord,
    Account,
    AccountingBalance,
    AccountingImportBatch,
    AccountingImportError,
    FinancialSummary
)
from apps.fund.services.accounting.strategies.reader_factory import ReaderFactory
from apps.fund.services.accounting.core.data_classes import ColumnMapping
from apps.fund.services.accounting.import_service import (
    AccountingImportService,
    DEFAULT_TXT_MAPPING,
    DEFAULT_XLSX_MAPPING
)
from apps.fund.services.invoices.invoices_service import InvoiceRecordService

# ============================================================================
# SERIALIZERS PARA IMPORTACIÓN DE ARCHIVOS
# ============================================================================

class ColumnMappingSerializer(serializers.Serializer):
    """Serializer para mapeo de columnas."""
    
    file_column = serializers.CharField(
        required=True,
        help_text="Nombre o índice de la columna en el archivo"
    )
    model_field = serializers.CharField(
        required=True,
        help_text="Nombre del campo en el modelo"
    )
    data_type = serializers.ChoiceField(
        choices=['string', 'decimal', 'date', 'integer'],
        default='string',
        help_text="Tipo de dato esperado"
    )
    required = serializers.BooleanField(
        default=False,
        help_text="Si el campo es obligatorio"
    )
    default_value = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Valor por defecto si está vacío"
    )
    date_format = serializers.CharField(
        default='%Y-%m-%d',
        required=False,
        help_text="Formato de fecha (ej: %Y-%m-%d, %d/%m/%Y)"
    )


class AccountingFileValidateSerializer(serializers.Serializer):
    """
    Serializer para validar un archivo antes de importar.
    Usa el ReaderFactory para detectar el tipo y parsear una muestra.
    """
    
    file = serializers.FileField(
        required=True,
        help_text="Archivo a validar (TXT, CSV, XLSX)"
    )
    encoding = serializers.CharField(
        default='utf-8',
        required=False,
        help_text="Codificación del archivo"
    )
    
    def validate_file(self, value):
        """Validar extensión del archivo."""
        filename = value.name.lower()
        valid_extensions = ['.txt', '.csv', '.tsv', '.xlsx', '.xls']
        
        if not any(filename.endswith(ext) for ext in valid_extensions):
            raise serializers.ValidationError(
                f"Extensión no soportada. Use: {', '.join(valid_extensions)}"
            )
        
        # Validar tamaño (máximo 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError(
                "El archivo excede el tamaño máximo de 10MB"
            )
        
        return value
    
    def create(self, validated_data):
        """Validar archivo y retornar información de estructura."""
        file = validated_data['file']
        encoding = validated_data.get('encoding', 'utf-8')
        filename = file.name
        
        try:
            # Leer contenido del archivo
            file_content = file.read()
            
            # Crear reader usando Factory
            reader = ReaderFactory.create(filename=filename)
            
            # Parsear primeras filas como muestra
            parsed_rows = list(reader.read(file_content, encoding))
            sample_rows = parsed_rows[:10]
            
            # Detectar delimitador si es TXT
            detected_delimiter = getattr(reader, 'detected_delimiter', None)
            
            return {
                'valid': len(reader.errors) == 0,
                'filename': filename,
                'file_type': 'xlsx' if filename.endswith(('.xlsx', '.xls')) else 'txt',
                'detected_delimiter': detected_delimiter,
                'total_rows': len(parsed_rows),
                'column_count': len(sample_rows[0].raw_data) if sample_rows else 0,
                'sample_rows': [
                    {
                        'row_number': row.row_number,
                        'data': row.raw_data,
                        'is_valid': row.is_valid
                    }
                    for row in sample_rows
                ],
                'errors': [
                    {
                        'row': e.row_number,
                        'message': e.message
                    }
                    for e in reader.errors
                ],
                'warnings': [
                    {
                        'row': w.row_number,
                        'message': w.message
                    }
                    for w in reader.warnings
                ],
                'suggested_mapping': self._get_suggested_mapping(filename)
            }
            
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        except Exception as e:
            raise serializers.ValidationError(f"Error procesando archivo: {str(e)}")
    
    def _get_suggested_mapping(self, filename: str) -> list:
        """Retorna el mapeo sugerido según el tipo de archivo."""
        if filename.lower().endswith(('.xlsx', '.xls')):
            mapping = DEFAULT_XLSX_MAPPING
        else:
            mapping = DEFAULT_TXT_MAPPING
        
        return [
            {
                'file_column': m.file_column,
                'model_field': m.model_field,
                'data_type': m.data_type,
                'required': m.required
            }
            for m in mapping
        ]
    
    def to_representation(self, instance):
        """Formatear respuesta."""
        return {
            'success': instance['valid'],
            'data': {
                'filename': instance['filename'],
                'file_type': instance['file_type'],
                'detected_delimiter': instance['detected_delimiter'],
                'total_rows': instance['total_rows'],
                'column_count': instance['column_count'],
                'sample_rows': instance['sample_rows'],
                'suggested_mapping': instance['suggested_mapping']
            },
            'errors': instance['errors'],
            'warnings': instance['warnings'],
            'message': 'Archivo válido' if instance['valid'] else 'Archivo con errores'
        }


class AccountingFileImportSerializer(serializers.Serializer):
    """
    Serializer para importar archivo de contabilidad.
    Orquesta el pipeline completo de importación.
    """
    
    file = serializers.FileField(
        required=True,
        help_text="Archivo a importar (TXT, CSV, XLSX)"
    )
    fund_id = serializers.IntegerField(
        required=True,
        help_text="ID del fondo al que pertenecen los registros"
    )
    import_type = serializers.ChoiceField(
        choices=['historical', 'current', 'opening'],
        default='historical',
        help_text="Tipo de importación: historical (histórico), current (corriente), opening (saldos iniciales)"
    )
    encoding = serializers.CharField(
        default='utf-8',
        required=False,
        help_text="Codificación del archivo"
    )
    dry_run = serializers.BooleanField(
        default=False,
        required=False,
        help_text="Si es True, solo valida sin guardar"
    )
    column_mapping = ColumnMappingSerializer(
        many=True,
        required=False,
        help_text="Mapeo personalizado de columnas (opcional)"
    )
    
    def validate_file(self, value):
        """Validar extensión y tamaño del archivo."""
        filename = value.name.lower()
        valid_extensions = ['.txt', '.csv', '.tsv', '.xlsx', '.xls']
        
        if not any(filename.endswith(ext) for ext in valid_extensions):
            raise serializers.ValidationError(
                f"Extensión no soportada. Use: {', '.join(valid_extensions)}"
            )
        
        if value.size > 50 * 1024 * 1024:  # 50MB para importación
            raise serializers.ValidationError(
                "El archivo excede el tamaño máximo de 50MB"
            )
        
        return value
    
    def validate_fund_id(self, value):
        """Validar que el fondo existe."""
        from apps.fund.models import Fund
        
        try:
            fund = Fund.objects.get(id=value)
            return fund
        except Fund.DoesNotExist:
            raise serializers.ValidationError(
                f"El fondo con ID {value} no existe"
            )
    
    def validate(self, attrs):
        """Validaciones a nivel de objeto."""
        request = self.context.get('request')
        
        if not request or not request.user:
            raise serializers.ValidationError("Usuario no autenticado")
        
        attrs['_user'] = request.user
        attrs['_fund'] = attrs['fund_id']
        
        return attrs
    
    def create(self, validated_data):
        """Ejecutar importación usando el servicio."""
        file = validated_data['file']
        fund = validated_data['_fund']
        user = validated_data['_user']
        import_type = validated_data.get('import_type', 'historical')
        encoding = validated_data.get('encoding', 'utf-8')
        dry_run = validated_data.get('dry_run', False)
        custom_mapping = validated_data.get('column_mapping')
        
        # Convertir mapeo personalizado si existe
        column_mapping = None
        if custom_mapping:
            column_mapping = [
                ColumnMapping(
                    file_column=m['file_column'],
                    model_field=m['model_field'],
                    data_type=m.get('data_type', 'string'),
                    required=m.get('required', False),
                    default_value=m.get('default_value'),
                    date_format=m.get('date_format', '%Y-%m-%d')
                )
                for m in custom_mapping
            ]
        
        # Leer contenido del archivo
        file_content = file.read()
        filename = file.name
        
        # Crear servicio e importar
        service = AccountingImportService(fund, user, import_type)
        result = service.import_file(
            file_content=file_content,
            filename=filename,
            column_mapping=column_mapping,
            encoding=encoding,
            dry_run=dry_run
        )
        
        return result
    
    def to_representation(self, instance):
        """Formatear respuesta del resultado de importación."""
        return {
            'success': instance.success,
            'data': {
                'batch_id': instance.batch_id,
                'total_rows': instance.total_rows,
                'processed_rows': instance.processed_rows,
                'successful_rows': instance.successful_rows,
                'failed_rows': instance.failed_rows,
                'created_entries': instance.created_entries_ids[:100]  # Limitar a 100
            },
            'errors': [
                {
                    'row': e.row_number,
                    'column': e.column,
                    'code': e.error_code,
                    'message': e.message,
                    'severity': e.severity.value if hasattr(e.severity, 'value') else str(e.severity)
                }
                for e in instance.errors[:50]  # Limitar a 50 errores
            ],
            'warnings': [
                {
                    'row': w.row_number,
                    'message': w.message
                }
                for w in instance.warnings[:50]
            ],
            'message': instance.message
        }


class AccountingDefaultMappingSerializer(serializers.Serializer):
    """
    Serializer para obtener el mapeo por defecto según tipo de archivo.
    """
    
    file_type = serializers.ChoiceField(
        choices=['txt', 'xlsx'],
        default='txt',
        help_text="Tipo de archivo"
    )
    
    def create(self, validated_data):
        """Retorna el mapeo por defecto."""
        file_type = validated_data.get('file_type', 'txt')
        
        if file_type == 'xlsx':
            mapping = DEFAULT_XLSX_MAPPING
        else:
            mapping = DEFAULT_TXT_MAPPING
        
        return {
            'file_type': file_type,
            'mapping': [
                {
                    'file_column': m.file_column,
                    'model_field': m.model_field,
                    'data_type': m.data_type,
                    'required': m.required,
                    'default_value': m.default_value,
                    'date_format': m.date_format
                }
                for m in mapping
            ]
        }
    
    def to_representation(self, instance):
        """Formatear respuesta."""
        return {
            'success': True,
            'data': instance,
            'message': f"Mapeo por defecto para archivos {instance['file_type'].upper()}"
        }


# ============================================================================
# SERIALIZERS PARA MODELOS DE CONTABILIDAD
# ============================================================================

class AccountCategorySerializer(serializers.ModelSerializer):
    """Serializer para categorías contables."""
    
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    subcategories_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AccountCategory
        fields = [
            'id', 'code', 'name', 'category_type', 'operational_type',
            'description', 'parent', 'parent_name', 'fund',
            'is_active', 'display_order', 'subcategories_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_subcategories_count(self, obj):
        return obj.subcategories.count()


class AccountingPeriodSerializer(serializers.ModelSerializer):
    """Serializer para períodos contables."""
    
    period_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_period_status_display', read_only=True)
    
    class Meta:
        model = AccountingPeriod
        fields = [
            'id', 'fund', 'year', 'month', 'start_date', 'end_date',
            'period_status', 'status_display', 'period_display',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_period_display(self, obj):
        return f"{obj.year}/{obj.month:02d}"


class AccountingEntrySerializer(serializers.ModelSerializer):
    """Serializer para registros contables."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_code = serializers.CharField(source='category.code', read_only=True)
    period_display = serializers.SerializerMethodField()
    entry_type_display = serializers.CharField(source='get_entry_type_display', read_only=True)
    entry_status_display = serializers.CharField(source='get_entry_status_display', read_only=True)
    
    class Meta:
        model = AccountingEntry
        fields = [
            'id', 'fund', 'period', 'period_display', 'category',
            'category_code', 'category_name', 'entry_date',
            'entry_type', 'entry_type_display', 'amount', 'description',
            'entry_status', 'entry_status_display', 'entry_source',
            'third_party_name', 'third_party_id', 'external_reference',
            'import_batch', 'original_row_number',
            'created_at', 'updated_at', 'created_by'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    def get_period_display(self, obj):
        if obj.period:
            return f"{obj.period.year}/{obj.period.month:02d}"
        return None

# ========================= FACTURAS =========================
class InvoiceRecordSerializer(serializers.ModelSerializer):
    """ Serializer para Registros de Facturas."""
    # Identificacion de la factura
    invoice_number = serializers.CharField(max_length=100, required=True)
    invoice_type = serializers.ChoiceField(choices=InvoiceRecord.InvoiceType.choices)
    
    # Emisor y receptor
    issuer_name = serializers.CharField(max_length=255, required=True)
    issuer_nit = serializers.CharField(max_length=50, required=True)
    receiver_name = serializers.CharField(max_length=255, required=True)
    receiver_nit = serializers.CharField(max_length=50, required=True)
    
    # Fechas
    issued_date = serializers.DateField(required=True, format="%Y-%m-%d")
    expiration_date = serializers.DateField(required=False, allow_null=True)
    
    # Conceptos
    notion = serializers.CharField(max_length=500, required=False, allow_blank=True)
    items_details = serializers.JSONField(required=False, help_text="Detalles de los ítems en formato JSON")
    
    # Pagos
    invoice_status = serializers.ChoiceField(choices=InvoiceRecord.InvoiceStatus.choices, default=InvoiceRecord.InvoiceStatus.ISSUED)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    
    created_at = serializers.DateTimeField(read_only=True, format="%Y-%m-%d %H:%M:%S")
    expiration_date = serializers.DateField(required=True, allow_null=True, format="%Y-%m-%d")
    invoice_status = serializers.ChoiceField(choices=InvoiceRecord.InvoiceStatus.choices, read_only=True)
    
    class Meta:
        model = InvoiceRecord
        fields = [
            'id', 'fund', 'trust_agreement', 'accounting_account', 'accounting_period',
            'invoice_number', 'invoice_type',
            'issuer_name', 'issuer_nit', 'receiver_name', 'receiver_nit',
            'issued_date', 'expiration_date',
            'notion', 'items_details',
            'subtotal', 'value_iva', 'withholding_tax', 'ica_withholding_tax', 'total_amount',
            'invoice_status', 'payment_date', 'payment_amount', 'payment_type',
            'attachment', 'xml_attachment', 'created_at' 
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_fund(self, value):
        """Validar que el fondo existe."""
        from apps.fund.models import Fund
        
        if not value:
            raise serializers.ValidationError("El campo 'fund' es obligatorio.")
        
        try:
            fund = Fund.objects.get(id=value.id)
            return fund
        except Fund.DoesNotExist:
            raise serializers.ValidationError(
                f"El fondo con ID {value.id} no existe"
            )
    
    def create(self, validated_data):
        """Crear un nuevo registro de factura."""
        try:
            request = self.context.get('request')
            user = request.user if request else None
            
            invoice_record = InvoiceRecordService.create_invoice_record(
                user=user,
                invoice_data=validated_data,
                request=request
            )
            
            return invoice_record
        except Exception as e:
            raise serializers.ValidationError(f"Error creando registro de factura: {str(e)}")
    

class AccountingBalanceSerializer(serializers.ModelSerializer):
    """Serializer para saldos contables."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    period_display = serializers.SerializerMethodField()
    
    class Meta:
        model = AccountingBalance
        fields = [
            'id', 'fund', 'period', 'period_display', 'category',
            'category_name', 'opening_balance', 'total_debits',
            'total_credits', 'closing_balance',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_period_display(self, obj):
        if obj.period:
            return f"{obj.period.year}/{obj.period.month:02d}"
        return None


class AccountingImportBatchSerializer(serializers.ModelSerializer):
    """Serializer para lotes de importación."""
    
    imported_by_email = serializers.CharField(source='imported_by.email', read_only=True)
    import_status_display = serializers.CharField(source='get_import_status_display', read_only=True)
    import_type_display = serializers.CharField(source='get_import_type_display', read_only=True)
    
    class Meta:
        model = AccountingImportBatch
        fields = [
            'id', 'fund', 'original_filename', 'import_type', 'import_type_display',
            'import_status', 'import_status_display', 'total_rows',
            'processed_rows', 'successful_rows', 'failed_rows',
            'validation_errors', 'imported_by', 'imported_by_email',
            'started_at', 'completed_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class FinancialSummarySerializer(serializers.ModelSerializer):
    """Serializer para resúmenes financieros."""
    
    period_display = serializers.SerializerMethodField()
    summary_type_display = serializers.CharField(source='get_summary_type_display', read_only=True)
    summary_status_display = serializers.CharField(source='get_summary_status_display', read_only=True)
    generated_by_email = serializers.CharField(source='generated_by.email', read_only=True)
    
    class Meta:
        model = FinancialSummary
        fields = [
            'id', 'fund', 'period', 'period_display',
            'summary_type', 'summary_type_display',
            'summary_status', 'summary_status_display',
            'total_assets', 'total_liabilities', 'total_equity',
            'operational_income', 'non_operational_income', 'total_income',
            'operational_expenses', 'non_operational_expenses', 'total_expenses',
            'operational_result', 'net_result',
            'data', 'generated_by', 'generated_by_email',
            'generated_at', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_period_display(self, obj):
        if obj.period:
            return f"{obj.period.year}/{obj.period.month:02d}"
        return None