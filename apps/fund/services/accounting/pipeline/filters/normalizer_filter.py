"""
Filtro de normalización de datos.
"""

import logging
from typing import Dict, Any

from apps.fund.services.accounting.pipeline.base_filter import BaseFilter
from apps.fund.services.accounting.core.data_classes import PipelineContext, ParsedRow

logger = logging.getLogger(__name__)


class NormalizerFilter(BaseFilter):
    """
    Filtro que normaliza los datos validados.
    
    Input: valid_rows
    Output: normalized_rows
    """
    
    def _process(self, context: PipelineContext) -> PipelineContext:
        logger.info(f"Normalizando {len(context.valid_rows)} filas")
        
        normalized_rows = []
        
        for row in context.valid_rows:
            normalized_data = self._normalize_row(row, context)
            normalized_rows.append(normalized_data)
        
        context.normalized_rows = normalized_rows
        
        logger.info(f"Filas normalizadas: {len(normalized_rows)}")
        
        return context
    
    def _normalize_row(self, row: ParsedRow, context: PipelineContext) -> Dict[str, Any]:
        """Normaliza una fila de datos."""
        data = row.data.copy()
        
        # Normalizar texto de descripción
        if 'description' in data:
            data['description'] = self._normalize_text(data.get('description', ''))
        
        # Normalizar nombre de tercero
        if 'third_party_name' in data:
            data['third_party_name'] = self._normalize_text(data.get('third_party_name', ''))
        
        # Normalizar ID de tercero (quitar espacios, guiones extras)
        if 'third_party_id' in data:
            data['third_party_id'] = self._normalize_id(data.get('third_party_id', ''))
        
        # Mantener metadatos
        data['_row_number'] = row.row_number
        data['_raw_data'] = row.raw_data
        
        return data
    
    def _normalize_text(self, text: str) -> str:
        """Normaliza un texto."""
        if not text:
            return ''
        return ' '.join(text.strip().split())
    
    def _normalize_id(self, id_value: str) -> str:
        """Normaliza un ID (NIT, cédula, etc)."""
        if not id_value:
            return ''
        # Quitar espacios y normalizar guiones
        return id_value.strip().replace(' ', '')