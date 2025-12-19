"""
Servicio principal de importación contable.
Orquesta el pipeline de importación.
"""

import logging
from typing import List, Optional

from django.utils import timezone

from apps.fund.services.accounting.core.data_classes import (
    PipelineContext,
    ImportResult,
    ColumnMapping,
    ValidationSeverity
)
from apps.fund.services.accounting.core.exceptions import AccountingImportError
from apps.fund.services.accounting.pipeline.pipeline_builder import PipelineBuilder
from apps.fund.services.accounting.validators.validator_chain_builder import ValidatorChainBuilder

logger = logging.getLogger(__name__)


# Mapeos por defecto para TXT (por índice de columna)
DEFAULT_TXT_MAPPING = [
    ColumnMapping(file_column="0", model_field="entry_date", data_type="date", required=True),
    ColumnMapping(file_column="1", model_field="category_code", data_type="string", required=True),
    ColumnMapping(file_column="2", model_field="entry_type", data_type="string", required=True),
    ColumnMapping(file_column="3", model_field="amount", data_type="decimal", required=True),
    ColumnMapping(file_column="4", model_field="description", data_type="string", required=True),
    ColumnMapping(file_column="5", model_field="third_party_name", data_type="string", required=False),
    ColumnMapping(file_column="6", model_field="third_party_id", data_type="string", required=False),
    ColumnMapping(file_column="7", model_field="external_reference", data_type="string", required=False),
]

# Mapeos por defecto para XLSX (por nombre de columna)
DEFAULT_XLSX_MAPPING = [
    ColumnMapping(file_column="Fecha", model_field="entry_date", data_type="date", required=True),
    ColumnMapping(file_column="Código Categoría", model_field="category_code", data_type="string", required=True),
    ColumnMapping(file_column="Tipo", model_field="entry_type", data_type="string", required=True),
    ColumnMapping(file_column="Monto", model_field="amount", data_type="decimal", required=True),
    ColumnMapping(file_column="Descripción", model_field="description", data_type="string", required=True),
    ColumnMapping(file_column="Tercero", model_field="third_party_name", data_type="string", required=False),
    ColumnMapping(file_column="NIT/Cédula", model_field="third_party_id", data_type="string", required=False),
    ColumnMapping(file_column="Referencia", model_field="external_reference", data_type="string", required=False),
]


class AccountingImportService:
    """
    Servicio de importación de datos contables.
    
    Orquesta el pipeline:
    Reader → Validators → Normalizers → Transformers → Saver
    
    Ejemplo:
        service = AccountingImportService(fund, user)
        result = service.import_file(file_content, 'datos.txt')
    """
    
    def __init__(self, fund, user, import_type: str = 'historical'):
        """
        Inicializa el servicio de importación.
        
        Args:
            fund: Instancia del modelo Fund
            user: Usuario que realiza la importación
            import_type: Tipo de importación ('historical', 'current', 'opening')
        """
        self.fund = fund
        self.user = user
        self.import_type = import_type
        self.pipeline = None
    
    def import_file(
        self,
        file_content: bytes,
        filename: str,
        column_mapping: List[ColumnMapping] = None,
        encoding: str = 'utf-8',
        dry_run: bool = False,
        custom_pipeline: bool = False
    ) -> ImportResult:
        """
        Importa datos contables desde un archivo.
        
        Args:
            file_content: Contenido del archivo en bytes
            filename: Nombre del archivo (para detectar tipo)
            column_mapping: Mapeo personalizado de columnas (opcional)
            encoding: Codificación del archivo
            dry_run: Si True, solo valida sin guardar
            custom_pipeline: Si True, usa pipeline personalizado
            
        Returns:
            ImportResult con el resultado de la importación
        """
        logger.info(f"Iniciando importación: {filename} para fondo {self.fund.id}")
        
        try:
            # Determinar mapeo de columnas
            if column_mapping is None:
                column_mapping = self._get_default_mapping(filename)
            
            # Crear contexto del pipeline
            context = self._create_context(
                file_content=file_content,
                filename=filename,
                column_mapping=column_mapping,
                encoding=encoding,
                dry_run=dry_run
            )
            
            # Crear batch de importación si no es dry_run
            if not dry_run:
                context.batch = self._create_import_batch(filename)
            
            # Construir y ejecutar pipeline
            pipeline = self._build_pipeline(custom_pipeline)
            context = pipeline.execute(context)
            
            # Construir resultado
            result = self._build_result(context)
            
            # Actualizar batch con resultado
            if context.batch and not dry_run:
                self._update_import_batch(context.batch, result)
            
            logger.info(f"Importación completada: {result.successful_rows}/{result.total_rows} exitosas")
            return result
            
        except AccountingImportError as e:
            logger.error(f"Error de importación: {e}")
            return ImportResult(
                success=False,
                message=str(e)
            )
        except Exception as e:
            logger.exception(f"Error inesperado en importación: {e}")
            return ImportResult(
                success=False,
                message=f"Error inesperado: {str(e)}"
            )
    
    def validate_file(
        self,
        file_content: bytes,
        filename: str,
        column_mapping: List[ColumnMapping] = None,
        encoding: str = 'utf-8'
    ) -> ImportResult:
        """
        Valida un archivo sin importar (dry_run).
        
        Args:
            file_content: Contenido del archivo
            filename: Nombre del archivo
            column_mapping: Mapeo de columnas
            encoding: Codificación
            
        Returns:
            ImportResult con errores de validación
        """
        return self.import_file(
            file_content=file_content,
            filename=filename,
            column_mapping=column_mapping,
            encoding=encoding,
            dry_run=True
        )
    
    def _get_default_mapping(self, filename: str) -> List[ColumnMapping]:
        """Obtiene el mapeo por defecto según el tipo de archivo."""
        filename_lower = filename.lower()
        
        if filename_lower.endswith(('.xlsx', '.xls')):
            return DEFAULT_XLSX_MAPPING
        else:
            return DEFAULT_TXT_MAPPING
    
    def _create_context(
        self,
        file_content: bytes,
        filename: str,
        column_mapping: List[ColumnMapping],
        encoding: str,
        dry_run: bool
    ) -> PipelineContext:
        """Crea el contexto inicial del pipeline."""
        return PipelineContext(
            file_content=file_content,
            filename=filename,
            fund=self.fund,
            user=self.user,
            import_type=self.import_type,
            encoding=encoding,
            column_mapping=column_mapping,
            dry_run=dry_run
        )
    
    def _build_pipeline(self, custom: bool = False):
        """Construye el pipeline de importación."""
        if custom and self.pipeline:
            return self.pipeline
        
        return PipelineBuilder.create_default_pipeline()
    
    def _create_import_batch(self, filename: str):
        """Crea el registro de lote de importación."""
        from apps.fund.models import AccountingImportBatch
        
        batch = AccountingImportBatch.objects.create(
            fund=self.fund,
            original_filename=filename,
            import_type=self.import_type,
            import_status='importing',
            imported_by=self.user,
            started_at=timezone.now()
        )
        
        logger.debug(f"Batch de importación creado: {batch.id}")
        return batch
    
    def _update_import_batch(self, batch, result: ImportResult):
        """Actualiza el batch con los resultados de la importación."""
        from django.utils import timezone
        
        if result.success:
            batch.import_status = 'completed'
        elif result.successful_rows > 0:
            batch.import_status = 'partial'
        else:
            batch.import_status = 'failed'
        
        batch.total_rows = result.total_rows
        batch.processed_rows = result.processed_rows
        batch.successful_rows = result.successful_rows
        batch.failed_rows = result.failed_rows
        batch.validation_errors = [
            {
                'row': e.row_number,
                'column': e.column,
                'code': e.error_code,
                'message': e.message
            }
            for e in result.errors[:100]  # Limitar a 100 errores
        ]
        batch.completed_at = timezone.now()
        batch.save()
        
        logger.debug(f"Batch {batch.id} actualizado: {batch.import_status}")
    
    def _build_result(self, context: PipelineContext) -> ImportResult:
        """Construye el resultado final desde el contexto."""
        total_rows = len(context.parsed_rows)
        valid_rows = len(context.valid_rows)
        failed_rows = total_rows - valid_rows
        
        success = failed_rows == 0 and not context.is_stopped
        
        if context.is_stopped:
            message = f"Importación detenida: {context.stop_reason}"
        elif success:
            message = f"Importación exitosa: {valid_rows} registros procesados"
        else:
            message = f"Importación con errores: {valid_rows} exitosos, {failed_rows} fallidos"
        
        return ImportResult(
            success=success,
            total_rows=total_rows,
            processed_rows=total_rows,
            successful_rows=valid_rows,
            failed_rows=failed_rows,
            errors=context.errors,
            warnings=context.warnings,
            created_entries_ids=[],  # Se llenaría desde el SaverFilter
            message=message,
            batch_id=context.batch.id if context.batch else None
        )
    
    def set_custom_pipeline(self, pipeline):
        """
        Establece un pipeline personalizado.
        
        Args:
            pipeline: Pipeline construido con PipelineBuilder
        """
        self.pipeline = pipeline
    
    def set_custom_validator_chain(self, validator_chain):
        """
        Establece una cadena de validadores personalizada.
        
        Args:
            validator_chain: Cadena construida con ValidatorChainBuilder
        """
        self.validator_chain = validator_chain


# ============================================================================
# FUNCIONES DE CONVENIENCIA
# ============================================================================

def import_accounting_txt(
    fund,
    user,
    file_content: bytes,
    filename: str,
    delimiter: str = None,
    encoding: str = 'utf-8',
    import_type: str = 'historical',
    custom_mapping: List[dict] = None,
    dry_run: bool = False
) -> ImportResult:
    """
    Función de conveniencia para importar archivo TXT.
    
    Args:
        fund: Instancia del Fund
        user: Usuario que importa
        file_content: Contenido del archivo
        filename: Nombre del archivo
        delimiter: Delimitador (auto-detectar si None)
        encoding: Codificación del archivo
        import_type: 'historical', 'current', 'opening'
        custom_mapping: Lista de dicts con mapeo personalizado
        dry_run: Solo validar sin guardar
        
    Returns:
        ImportResult
        
    Ejemplo de custom_mapping:
        [
            {'file_column': '0', 'model_field': 'entry_date', 'data_type': 'date', 'required': True},
            {'file_column': '1', 'model_field': 'category_code', 'data_type': 'string', 'required': True},
        ]
    """
    column_mapping = None
    if custom_mapping:
        column_mapping = [
            ColumnMapping(**mapping) for mapping in custom_mapping
        ]
    
    service = AccountingImportService(fund, user, import_type)
    return service.import_file(
        file_content=file_content,
        filename=filename,
        column_mapping=column_mapping,
        encoding=encoding,
        dry_run=dry_run
    )


def import_accounting_xlsx(
    fund,
    user,
    file_content: bytes,
    filename: str,
    sheet_name: str = None,
    import_type: str = 'historical',
    custom_mapping: List[dict] = None,
    dry_run: bool = False
) -> ImportResult:
    """
    Función de conveniencia para importar archivo XLSX.
    
    Args:
        fund: Instancia del Fund
        user: Usuario que importa
        file_content: Contenido del archivo
        filename: Nombre del archivo
        sheet_name: Nombre de la hoja (opcional)
        import_type: 'historical', 'current', 'opening'
        custom_mapping: Lista de dicts con mapeo personalizado
        dry_run: Solo validar sin guardar
        
    Returns:
        ImportResult
    """
    column_mapping = None
    if custom_mapping:
        column_mapping = [
            ColumnMapping(**mapping) for mapping in custom_mapping
        ]
    
    service = AccountingImportService(fund, user, import_type)
    return service.import_file(
        file_content=file_content,
        filename=filename,
        column_mapping=column_mapping,
        dry_run=dry_run
    )


def validate_accounting_file(
    fund,
    user,
    file_content: bytes,
    filename: str,
    custom_mapping: List[dict] = None
) -> ImportResult:
    """
    Valida un archivo sin importar.
    
    Args:
        fund: Instancia del Fund
        user: Usuario
        file_content: Contenido del archivo
        filename: Nombre del archivo
        custom_mapping: Mapeo personalizado
        
    Returns:
        ImportResult con errores de validación
    """
    column_mapping = None
    if custom_mapping:
        column_mapping = [
            ColumnMapping(**mapping) for mapping in custom_mapping
        ]
    
    service = AccountingImportService(fund, user)
    return service.validate_file(
        file_content=file_content,
        filename=filename,
        column_mapping=column_mapping
    )


def get_default_mapping(file_type: str = 'txt') -> List[dict]:
    """
    Retorna el mapeo por defecto como lista de dicts.
    Útil para mostrar al usuario y permitir personalización.
    
    Args:
        file_type: 'txt' o 'xlsx'
        
    Returns:
        Lista de diccionarios con la configuración de mapeo
    """
    mapping = DEFAULT_TXT_MAPPING if file_type == 'txt' else DEFAULT_XLSX_MAPPING
    
    return [
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