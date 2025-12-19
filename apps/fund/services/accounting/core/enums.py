"""
Enumeraciones para el sistema de importación contable.
"""

from enum import Enum


# ============================================================================
# ESTADO DE IMPORTACIÓN
# ============================================================================

class ImportStatus(str, Enum):
    """
    Estados del proceso de importación de un batch.
    
    Uso:
        batch.import_status = ImportStatus.PROCESSING.value
        if batch.import_status == ImportStatus.COMPLETED.value:
            ...
    """
    PENDING = 'pending'           # Archivo recibido, esperando procesamiento
    VALIDATING = 'validating'     # Validando estructura y datos
    PROCESSING = 'processing'     # Creando registros en BD
    COMPLETED = 'completed'       # Importación exitosa (100% filas)
    PARTIAL = 'partial'           # Importación parcial (algunas filas fallaron)
    FAILED = 'failed'             # Importación fallida (error crítico)
    CANCELLED = 'cancelled'       # Cancelada por el usuario


# ============================================================================
# TIPO DE ENTRADA CONTABLE
# ============================================================================

class EntryType(str, Enum):
    """
    Tipos de movimiento contable (partida doble).
    
    Uso:
        entry.entry_type = EntryType.DEBIT.value
        if entry.entry_type == EntryType.CREDIT.value:
            ...
    """
    DEBIT = 'debit'     # Débito (cargo) - Aumenta activos/gastos
    CREDIT = 'credit'   # Crédito (abono) - Aumenta pasivos/ingresos/patrimonio


# ============================================================================
# TIPO DE IMPORTACIÓN
# ============================================================================

class ImportType(str, Enum):
    """
    Tipo de datos que se están importando.
    
    Uso:
        service = AccountingImportService(fund, user, ImportType.HISTORICAL.value)
    """
    HISTORICAL = 'historical'   # Datos históricos (años anteriores)
    CURRENT = 'current'         # Datos del período actual
    OPENING = 'opening'         # Saldos de apertura
    ADJUSTMENT = 'adjustment'   # Ajustes contables


# ============================================================================
# SEVERIDAD DE VALIDACIÓN
# ============================================================================

class ValidationSeverity(str, Enum):
    """
    Niveles de severidad para errores de validación.
    
    Uso:
        error = ValidationError(
            severity=ValidationSeverity.ERROR,
            ...
        )
        
        # Filtrar solo errores críticos
        critical_errors = [e for e in errors if e.severity == ValidationSeverity.CRITICAL]
    """
    WARNING = 'warning'     # Advertencia: permite continuar pero se debe revisar
    ERROR = 'error'         # Error: la fila no se procesa, pero el pipeline continúa
    CRITICAL = 'critical'   # Crítico: detiene todo el pipeline


# ============================================================================
# TIPO DE DATO DE COLUMNA
# ============================================================================

class ColumnDataType(str, Enum):
    """
    Tipos de datos soportados para columnas del archivo.
    
    Uso:
        mapping = ColumnMapping(
            file_column="Monto",
            model_field="amount",
            data_type=ColumnDataType.DECIMAL.value
        )
    """
    STRING = 'string'       # Texto libre
    INTEGER = 'integer'     # Número entero
    DECIMAL = 'decimal'     # Número decimal (para montos)
    DATE = 'date'           # Fecha
    BOOLEAN = 'boolean'     # Verdadero/Falso
    CHOICE = 'choice'       # Valor de una lista predefinida


# ============================================================================
# ESTADO DEL PERÍODO CONTABLE
# ============================================================================

class PeriodStatus(str, Enum):
    """
    Estados del período contable.
    
    Uso:
        if period.period_status == PeriodStatus.CLOSED.value:
            raise ValidationError("No se puede registrar en período cerrado")
    """
    OPEN = 'open'           # Abierto para registros
    CLOSING = 'closing'     # En proceso de cierre
    CLOSED = 'closed'       # Cerrado (no admite nuevos registros)
    LOCKED = 'locked'       # Bloqueado (ni siquiera ajustes)


# ============================================================================
# FUENTE DE LA ENTRADA
# ============================================================================

class EntrySource(str, Enum):
    """
    Origen de la entrada contable.
    
    Uso:
        entry.entry_source = EntrySource.IMPORT.value
    """
    MANUAL = 'manual'       # Ingresada manualmente por usuario
    IMPORT = 'import'       # Importada desde archivo
    SYSTEM = 'system'       # Generada automáticamente por el sistema
    API = 'api'             # Recibida por integración API externa


# ============================================================================
# ESTADO DE LA ENTRADA CONTABLE
# ============================================================================

class EntryStatus(str, Enum):
    """
    Estados de una entrada contable.
    
    Flujo típico: DRAFT → PENDING → POSTED
    
    Uso:
        entry.entry_status = EntryStatus.POSTED.value
    """
    DRAFT = 'draft'         # Borrador (editable)
    PENDING = 'pending'     # Pendiente de aprobación
    POSTED = 'posted'       # Contabilizada (no editable)
    VOIDED = 'voided'       # Anulada


# ============================================================================
# CÓDIGOS DE ERROR
# ============================================================================

class ErrorCode(str, Enum):
    """
    Códigos de error estandarizados para el sistema de importación.
    
    Uso:
        error = ValidationError(
            error_code=ErrorCode.INVALID_CATEGORY.value,
            message="La categoría no existe"
        )
        
        # En frontend, mapear código a mensaje traducido
        ERROR_MESSAGES = {
            ErrorCode.INVALID_CATEGORY.value: "La categoría contable no existe",
            ...
        }
    """
    # Errores de archivo
    FILE_EMPTY = 'FILE_EMPTY'
    FILE_TOO_LARGE = 'FILE_TOO_LARGE'
    FILE_INVALID_FORMAT = 'FILE_INVALID_FORMAT'
    FILE_ENCODING_ERROR = 'FILE_ENCODING_ERROR'
    
    # Errores de estructura
    MISSING_COLUMN = 'MISSING_COLUMN'
    INVALID_HEADER = 'INVALID_HEADER'
    ROW_TOO_SHORT = 'ROW_TOO_SHORT'
    
    # Errores de campos requeridos
    REQUIRED_FIELD = 'REQUIRED_FIELD'
    MISSING_DATE = 'MISSING_DATE'
    MISSING_AMOUNT = 'MISSING_AMOUNT'
    MISSING_CATEGORY = 'MISSING_CATEGORY'
    
    # Errores de formato
    INVALID_DATE_FORMAT = 'INVALID_DATE_FORMAT'
    INVALID_AMOUNT_FORMAT = 'INVALID_AMOUNT_FORMAT'
    INVALID_ENTRY_TYPE = 'INVALID_ENTRY_TYPE'
    
    # Errores de validación de negocio
    INVALID_CATEGORY = 'INVALID_CATEGORY'
    INVALID_PERIOD = 'INVALID_PERIOD'
    PERIOD_CLOSED = 'PERIOD_CLOSED'
    INVALID_AMOUNT = 'INVALID_AMOUNT'
    DUPLICATE_ENTRY = 'DUPLICATE_ENTRY'
    
    # Errores de persistencia
    DATABASE_ERROR = 'DATABASE_ERROR'
    CONSTRAINT_VIOLATION = 'CONSTRAINT_VIOLATION'
    
    # Errores generales
    PARSE_ERROR = 'PARSE_ERROR'
    VALIDATION_ERROR = 'VALIDATION_ERROR'
    TRANSFORMATION_ERROR = 'TRANSFORMATION_ERROR'
    UNKNOWN_ERROR = 'UNKNOWN_ERROR'


# ============================================================================
# PASOS DEL PIPELINE
# ============================================================================

class PipelineStep(str, Enum):
    """
    Pasos del pipeline de importación.
    
    Uso:
        context.current_step = PipelineStep.VALIDATING.value
        logger.info(f"Pipeline en paso: {context.current_step}")
    """
    READING = 'reading'           # Leyendo archivo
    VALIDATING = 'validating'     # Validando datos
    NORMALIZING = 'normalizing'   # Normalizando datos
    TRANSFORMING = 'transforming' # Transformando a entidades
    SAVING = 'saving'             # Guardando en BD
    COMPLETED = 'completed'       # Finalizado
    FAILED = 'failed'             # Fallido


# ============================================================================
# DELIMITADORES SOPORTADOS
# ============================================================================

class FileDelimiter(str, Enum):
    """
    Delimitadores soportados para archivos de texto.
    
    Uso:
        parser = TxtReaderStrategy(delimiter=FileDelimiter.SEMICOLON.value)
    """
    TAB = '\t'
    COMMA = ','
    SEMICOLON = ';'
    PIPE = '|'
    SPACE = ' '