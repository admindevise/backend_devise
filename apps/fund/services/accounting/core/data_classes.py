"""
Data classes para el sistema de importacion contable
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import List, Dict, Any, Optional
from enum import Enum

class ImportStatus(str, Enum):
    PENDING = 'pending'
    VALIDATING = 'validating'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    PARTIAL = 'partial'
    
class EntryType(str, Enum):
    DEBIT = 'debit'
    CREDIT = 'credit'

class ValidationSeverity(str, Enum):
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


@dataclass
class ColumnMapping:
    file_column: str
    model_field: str
    data_type: str = "string"
    required: bool = False
    default_value: Any = None
    date_format: str = "%Y-%m-%d"

@dataclass
class ParsedRow:
    row_number: int
    raw_data: List[str]    
    data: Dict[str, Any] = field(default_factory=dict)
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

@dataclass
class ValidationError:
    row_number: int
    column: Optional[str]
    error_code: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    original_value: Any = None
    
@dataclass
class ImportResult:
    success: bool
    total_rows: int = 0
    processed_rows: int = 0
    successful_rows: int = 0
    failed_rows: int = 0
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    created_entries_ids: List[int] = field(default_factory=list)
    message: str = ""
    batch_id: Optional[int] = None

@dataclass
class PipelineContext:
    """
    Contexto compartido entre todos los filtros del pipeline.
    Actua como el 'mensaje' que fluye por el pipeline.
    """
    # Datos de entrada
    file_content: bytes
    filename: str
    fund: Any
    user: Any
    import_type: str = 'historical'
    
    # Configuracion
    encoding: str = 'utf-8'
    column_mapping: List[ColumnMapping] = field(default_factory=list)
    dry_run: bool = False
    
    # Estado del pipeline
    current_step: str = ''
    is_stopped: bool = False
    stop_reason: Optional[str] = None
    
    # Datos procesados (se van llenando en cada filtro)
    parsed_rows: List[ParsedRow] = field(default_factory=list)
    valid_rows: List[ParsedRow] = field(default_factory=list)
    normalized_rows: List[Dict[str, Any]] = field(default_factory=list)
    transformed_entries: List[Any] = field(default_factory=list)
    
    # Resultados
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    
    # Caches (para optimizacion)
    categories_cache: Dict[str, Any] = field(default_factory=dict)
    periods_cache: Dict[tuple, Any] = field(default_factory=dict)
    
    # Batch de importacion
    batch: Any = None
    
    def add_error(self, error: ValidationError):
        """Agrega un error al contexto."""
        self.errors.append(error)
        
    def add_warning(self, warning: ValidationError):
        """Agrega una advertencia al contexto."""
        self.warnings.append(warning)
        
    def stop_pipeline(self, reason: str): 
        """Detiene el pipeline con una razon."""
        self.is_stopped = True
        self.stop_reason = reason