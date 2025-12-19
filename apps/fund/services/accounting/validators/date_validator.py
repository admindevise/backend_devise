"""
Validador de fecha.
"""

from datetime import datetime, date

from apps.fund.services.accounting.validators.base_validator import BaseValidator
from apps.fund.services.accounting.core.data_classes import ParsedRow, PipelineContext


class DateValidator(BaseValidator):
    """Valida y convierte la fecha."""
    
    DATE_FORMATS = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d.%m.%Y",
    ]
    
    def _do_validate(self, row: ParsedRow, context: PipelineContext) -> ParsedRow:
        entry_date = row.data.get('entry_date')
        
        if entry_date is None:
            return row  # Ya manejado por RequiredFieldsValidator
        
        # Si ya es date, validar
        if isinstance(entry_date, date):
            return row
        
        # Convertir string a date
        for fmt in self.DATE_FORMATS:
            try:
                parsed_date = datetime.strptime(str(entry_date), fmt).date()
                row.data['entry_date'] = parsed_date
                return row
            except ValueError:
                continue
        
        self._add_error(
            row,
            'INVALID_DATE_FORMAT',
            f"Formato de fecha inválido: '{entry_date}'",
            column='entry_date'
        )
        
        return row