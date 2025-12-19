"""
Clase base abstracta para readers (Strategy Pattern).
"""

from abc import ABC, abstractmethod
from typing import Iterator, List, Optional

from apps.fund.services.accounting.core.data_classes import (
    ParsedRow, 
    ColumnMapping,
    ValidationError,
    ValidationSeverity
)


class BaseReaderStrategy(ABC):
    """
    Strategy base para lectura de archivos.
    
    Cada implementación concreta maneja un formato específico
    pero todas producen el mismo resultado: Iterator[ParsedRow]
    """
    
    def __init__(self, column_mapping: List[ColumnMapping] = None):
        self.column_mapping = column_mapping or []
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []
    
    @abstractmethod
    def read(self, file_content: bytes, encoding: str = 'utf-8') -> Iterator[ParsedRow]:
        """
        Lee el archivo y genera filas parseadas.
        
        Args:
            file_content: Contenido del archivo en bytes
            encoding: Codificación del archivo
            
        Yields:
            ParsedRow: Fila parseada del archivo
        """
        pass
    
    @abstractmethod
    def can_handle(self, filename: str) -> bool:
        """
        Indica si este reader puede manejar el archivo.
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            bool: True si puede manejar el archivo
        """
        pass
    
    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Extensiones de archivo soportadas."""
        pass
    
    def add_error(self, row: int, message: str, column: str = None):
        """Agrega un error de lectura."""
        self.errors.append(ValidationError(
            row_number=row,
            column=column,
            error_code='READ_ERROR',
            message=message,
            severity=ValidationSeverity.ERROR
        ))
    
    def add_warning(self, row: int, message: str, column: str = None):
        """Agrega una advertencia de lectura."""
        self.warnings.append(ValidationError(
            row_number=row,
            column=column,
            error_code='READ_WARNING',
            message=message,
            severity=ValidationSeverity.WARNING
        ))