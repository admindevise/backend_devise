"""
Validador de categoría contable.
"""

from apps.fund.services.accounting.validators.base_validator import BaseValidator
from apps.fund.services.accounting.core.data_classes import ParsedRow, PipelineContext


class CategoryValidator(BaseValidator):
    """Valida que la categoría exista para el fondo."""
    
    def _do_validate(self, row: ParsedRow, context: PipelineContext) -> ParsedRow:
        category_code = row.data.get('category_code')
        
        if not category_code:
            return row  # Ya manejado por RequiredFieldsValidator
        
        # Buscar en cache
        if category_code not in context.categories_cache:
            self._add_error(
                row,
                'INVALID_CATEGORY',
                f"Categoría '{category_code}' no existe para este fondo",
                column='category_code'
            )
        else:
            # Agregar referencia de categoría a los datos
            row.data['_category'] = context.categories_cache[category_code]
        
        return row