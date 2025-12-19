"""
Strategy para lectura de archivos TXT/CSV delimitados.
"""

import csv
import logging
from typing import Iterator, List, Optional

from apps.fund.services.accounting.strategies.base_reader import BaseReaderStrategy
from apps.fund.services.accounting.core.data_classes import ParsedRow, ColumnMapping

logger = logging.getLogger(__name__)


class TxtReaderStrategy(BaseReaderStrategy):
    """
    Reader para archivos TXT delimitados.
    Soporta detección automática de delimitador.
    """
    
    DELIMITERS = ['\t', ';', ',', '|']
    
    def __init__(
        self,
        column_mapping: List[ColumnMapping] = None,
        delimiter: str = None,
        has_header: bool = True,
        skip_rows: int = 0
    ):
        super().__init__(column_mapping)
        self.delimiter = delimiter
        self.has_header = has_header
        self.skip_rows = skip_rows
        self.detected_delimiter: Optional[str] = None
    
    @property
    def supported_extensions(self) -> List[str]:
        return ['.txt', '.csv', '.tsv']
    
    def can_handle(self, filename: str) -> bool:
        return any(filename.lower().endswith(ext) for ext in self.supported_extensions)
    
    def read(self, file_content: bytes, encoding: str = 'utf-8') -> Iterator[ParsedRow]:
        """Lee archivo TXT y genera filas."""
        try:
            text_content = self._decode_content(file_content, encoding)
            lines = text_content.splitlines()
            
            if not lines:
                self.add_error(0, 'Archivo vacío')
                return
            
            # Saltar filas iniciales
            lines = lines[self.skip_rows:]
            
            # Detectar delimitador
            delimiter = self._detect_delimiter(lines)
            
            # Parsear con csv.reader
            reader = csv.reader(lines, delimiter=delimiter)
            
            header_row = None
            row_number = self.skip_rows
            
            for row in reader:
                row_number += 1
                
                # Saltar filas vacías
                if not row or all(cell.strip() == '' for cell in row):
                    continue
                
                # Capturar header
                if self.has_header and header_row is None:
                    header_row = [col.strip() for col in row]
                    continue
                
                # Generar ParsedRow
                yield self._create_parsed_row(row, row_number, header_row)
                
        except Exception as e:
            logger.exception(f"Error leyendo archivo TXT: {e}")
            self.add_error(0, f'Error general: {str(e)}')
    
    def _decode_content(self, file_content: bytes, encoding: str) -> str:
        """Decodifica el contenido del archivo."""
        try:
            return file_content.decode(encoding)
        except UnicodeDecodeError:
            self.add_warning(0, f'Archivo decodificado con latin-1 en lugar de {encoding}')
            return file_content.decode('latin-1')
    
    def _detect_delimiter(self, lines: List[str]) -> str:
        """Detecta automáticamente el delimitador."""
        if self.delimiter:
            return self.delimiter
        
        delimiter_counts = {d: 0 for d in self.DELIMITERS}
        
        for line in lines[:5]:
            for delimiter in self.DELIMITERS:
                delimiter_counts[delimiter] += line.count(delimiter)
        
        detected = max(delimiter_counts, key=delimiter_counts.get)
        
        if delimiter_counts[detected] == 0:
            detected = '\t'
        
        self.detected_delimiter = detected
        logger.info(f"Delimitador detectado: {repr(detected)}")
        return detected
    
    def _create_parsed_row(
        self, 
        row: List[str], 
        row_number: int, 
        header_row: Optional[List[str]]
    ) -> ParsedRow:
        """Crea un ParsedRow a partir de una fila."""
        data = {}
        errors = []
        
        for mapping in self.column_mapping:
            value, error = self._extract_value(row, header_row, mapping)
            data[mapping.model_field] = value
            if error:
                errors.append(error)
        
        return ParsedRow(
            row_number=row_number,
            raw_data=row,
            data=data,
            is_valid=len(errors) == 0,
            errors=errors
        )
    
    def _extract_value(
        self,
        row: List[str],
        header_row: Optional[List[str]],
        mapping: ColumnMapping
    ) -> tuple:
        """Extrae un valor de la fila según el mapeo."""
        try:
            # Determinar índice
            if header_row and not mapping.file_column.isdigit():
                col_idx = header_row.index(mapping.file_column)
            else:
                col_idx = int(mapping.file_column)
            
            # Obtener valor
            value = row[col_idx].strip() if col_idx < len(row) else ""
            
            if not value and mapping.required:
                return None, f"Campo '{mapping.model_field}' es requerido"
            
            return value if value else mapping.default_value, None
            
        except (ValueError, IndexError):
            if mapping.required:
                return None, f"Columna '{mapping.file_column}' no encontrada"
            return mapping.default_value, None