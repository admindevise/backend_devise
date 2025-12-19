"""
Validador de tipo de entrada (débito/crédito).
"""

from apps.fund.services.accounting.validators.base_validator import BaseValidator
from apps.fund.services.accounting.core.data_classes import ParsedRow, PipelineContext


class EntryTypeValidator(BaseValidator):
    """Valida el tipo de entrada contable."""
    
    VALID_DEBIT = ['debit', 'débito', 'd', 'db', 'deb']
    VALID_CREDIT = ['credit', 'crédito', 'c', 'cr', 'cred']
    
    def _do_validate(self, row: ParsedRow, context: PipelineContext) -> ParsedRow:
        entry_type = row.data.get('entry_type', '').lower().strip()
        
        if not entry_type:
            return row  # Ya manejado por RequiredFieldsValidator
        
        if entry_type in self.VALID_DEBIT:
            row.data['entry_type'] = 'debit'
        elif entry_type in self.VALID_CREDIT:
            row.data['entry_type'] = 'credit'
        else:
            self._add_error(
                row,
                'INVALID_ENTRY_TYPE',
                f"Tipo de entrada inválido: '{entry_type}'. Use 'debit' o 'credit'",
                column='entry_type'
            )
        
        return row