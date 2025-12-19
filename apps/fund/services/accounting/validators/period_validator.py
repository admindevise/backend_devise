"""
Validador de período contable.
"""

from apps.fund.services.accounting.validators.base_validator import BaseValidator
from apps.fund.services.accounting.core.data_classes import ParsedRow, PipelineContext


class PeriodValidator(BaseValidator):
    """Valida que el período esté abierto para registro."""
    
    def _do_validate(self, row: ParsedRow, context: PipelineContext) -> ParsedRow:
        entry_date = row.data.get('entry_date')
        
        if not entry_date:
            return row
        
        period_key = (entry_date.year, entry_date.month)
        
        # Verificar si el período está en cache
        if period_key in context.periods_cache:
            period = context.periods_cache[period_key]
            
            # Verificar si está cerrado
            if period.period_status == 'closed':
                self._add_warning(
                    row,
                    f"El período {entry_date.year}/{entry_date.month:02d} está cerrado"
                )
        
        # Guardar referencia al período
        row.data['_period_key'] = period_key
        
        return row
    
    def _is_critical(self) -> bool:
        """Período cerrado no es crítico, solo advertencia."""
        return False