"""
Filtro de validación usando Chain of Responsibility.
"""

import logging

from apps.fund.services.accounting.pipeline.base_filter import BaseFilter
from apps.fund.services.accounting.core.data_classes import PipelineContext, ValidationError, ValidationSeverity
from apps.fund.services.accounting.validators.validator_chain_builder import ValidatorChainBuilder

logger = logging.getLogger(__name__)


class ValidatorFilter(BaseFilter):
    """
    Filtro que valida las filas usando la cadena de validadores.
    
    Input: parsed_rows
    Output: valid_rows (solo filas que pasaron validación)
    """
    
    def __init__(self, validator_chain=None):
        super().__init__()
        self.validator_chain = validator_chain or ValidatorChainBuilder.create_default_chain()
    
    def _process(self, context: PipelineContext) -> PipelineContext:
        logger.info(f"Validando {len(context.parsed_rows)} filas")
        
        # Cargar cache de categorías si no existe
        self._load_categories_cache(context)
        
        valid_rows = []
        
        for row in context.parsed_rows:
            # Validar fila con la cadena
            validated_row = self.validator_chain.validate(row, context)
            
            if validated_row.is_valid:
                valid_rows.append(validated_row)
            else:
                # Agregar errores al contexto
                for error_msg in validated_row.errors:
                    context.add_error(ValidationError(
                        row_number=validated_row.row_number,
                        column=None,
                        error_code='VALIDATION_ERROR',
                        message=error_msg,
                        severity=ValidationSeverity.ERROR
                    ))
            
            # Agregar warnings al contexto
            for warning_msg in validated_row.warnings:
                context.add_warning(ValidationError(
                    row_number=validated_row.row_number,
                    column=None,
                    error_code='VALIDATION_WARNING',
                    message=warning_msg,
                    severity=ValidationSeverity.WARNING
                ))
        
        context.valid_rows = valid_rows
        
        logger.info(f"Filas válidas: {len(valid_rows)}/{len(context.parsed_rows)}")
        
        return context
    
    def _load_categories_cache(self, context: PipelineContext):
        """Carga el cache de categorías si está vacío."""
        if context.categories_cache:
            return
        
        from apps.fund.models import AccountCategory
        
        context.categories_cache = {
            cat.code: cat
            for cat in AccountCategory.objects.filter(
                fund=context.fund,
                is_active=True
            )
        }
        
        logger.debug(f"Cache de categorías cargado: {len(context.categories_cache)} categorías")