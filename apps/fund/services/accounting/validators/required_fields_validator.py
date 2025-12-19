"""
Validador de campos requeridos.
"""

from apps.fund.services.accounting.validators.base_validator import BaseValidator
from apps.fund.services.accounting.core.data_classes import ParsedRow, PipelineContext


class RequiredFieldsValidator(BaseValidator):
    """Valida que los campos requeridos estén presentes."""
    
    REQUIRED_FIELDS = ['entry_date', 'category_code', 'entry_type', 'amount']
    
    def _do_validate(self, row: ParsedRow, context: PipelineContext) -> ParsedRow:
        for field in self.REQUIRED_FIELDS:
            value = row.data.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                self._add_error(
                    row,
                    'REQUIRED_FIELD',
                    f"Campo '{field}' es requerido",
                    column=field
                )
        
        return row