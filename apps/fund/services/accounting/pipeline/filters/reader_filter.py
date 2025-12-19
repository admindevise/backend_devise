"""
Filtro de lectura de archivo.
"""

import logging

from apps.fund.services.accounting.pipeline.base_filter import BaseFilter
from apps.fund.services.accounting.core.data_classes import PipelineContext, ValidationError
from apps.fund.services.accounting.strategies.reader_factory import ReaderFactory

logger = logging.getLogger(__name__)


class ReaderFilter(BaseFilter):
    """
    Filtro que lee el archivo usando el Strategy apropiado.
    
    Input: file_content, filename
    Output: parsed_rows
    """
    
    def _process(self, context: PipelineContext) -> PipelineContext:
        logger.info(f"Leyendo archivo: {context.filename}")
        
        # Obtener reader usando Factory
        reader = ReaderFactory.create(
            filename=context.filename,
            column_mapping=context.column_mapping
        )
        
        # Leer archivo
        parsed_rows = list(reader.read(context.file_content, context.encoding))
        
        # Agregar errores del reader al contexto
        for error in reader.errors:
            context.add_error(error)
        
        for warning in reader.warnings:
            context.add_warning(warning)
        
        # Guardar filas parseadas
        context.parsed_rows = parsed_rows
        
        logger.info(f"Filas leídas: {len(parsed_rows)}")
        
        # Verificar si hay filas
        if not parsed_rows:
            context.stop_pipeline("No se encontraron filas para procesar")
        
        return context