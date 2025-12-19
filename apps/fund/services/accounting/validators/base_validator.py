"""
Clase base para validadores (Chain of Responsibility Pattern).
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from apps.fund.services.accounting.core.data_classes import (
    ParsedRow,
    ValidationError,
    ValidationSeverity,
    PipelineContext
)


class BaseValidator(ABC):
    """
    Handler base para la cadena de validación.
    
    Cada validador puede:
    1. Procesar la validación
    2. Pasar al siguiente handler
    3. Detener la cadena si hay error crítico
    """
    
    def __init__(self):
        self._next_handler: Optional['BaseValidator'] = None
    
    def set_next(self, handler: 'BaseValidator') -> 'BaseValidator':
        """
        Establece el siguiente handler en la cadena.
        
        Args:
            handler: Siguiente validador
            
        Returns:
            El handler pasado (para encadenamiento fluido)
        """
        self._next_handler = handler
        return handler
    
    def validate(self, row: ParsedRow, context: PipelineContext) -> ParsedRow:
        """
        Ejecuta la validación y pasa al siguiente handler.
        
        Args:
            row: Fila a validar
            context: Contexto del pipeline
            
        Returns:
            ParsedRow: Fila validada (posiblemente modificada)
        """
        # Ejecutar validación específica
        row = self._do_validate(row, context)
        
        # Si hay error crítico, no continuar
        if not row.is_valid and self._is_critical():
            return row
        
        # Pasar al siguiente handler
        if self._next_handler:
            return self._next_handler.validate(row, context)
        
        return row
    
    @abstractmethod
    def _do_validate(self, row: ParsedRow, context: PipelineContext) -> ParsedRow:
        """
        Implementación específica de la validación.
        
        Args:
            row: Fila a validar
            context: Contexto del pipeline
            
        Returns:
            ParsedRow: Fila validada
        """
        pass
    
    def _is_critical(self) -> bool:
        """
        Indica si un error en este validador es crítico
        (detiene la cadena).
        """
        return True
    
    def _add_error(self, row: ParsedRow, code: str, message: str, column: str = None):
        """Helper para agregar error a la fila."""
        row.errors.append(f"[{code}] {message}")
        row.is_valid = False
    
    def _add_warning(self, row: ParsedRow, message: str):
        """Helper para agregar advertencia a la fila."""
        row.warnings.append(message)