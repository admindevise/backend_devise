"""
Validador de monto.
"""

from decimal import Decimal, InvalidOperation

from apps.fund.services.accounting.validators.base_validator import BaseValidator
from apps.fund.services.accounting.core.data_classes import ParsedRow, PipelineContext


class AmountValidator(BaseValidator):
    """Valida y convierte el monto a Decimal."""
    
    def _do_validate(self, row: ParsedRow, context: PipelineContext) -> ParsedRow:
        amount = row.data.get('amount')
        
        if amount is None:
            return row  # Ya manejado por RequiredFieldsValidator
        
        # Si ya es Decimal, validar valor
        if isinstance(amount, Decimal):
            if amount <= 0:
                self._add_error(
                    row,
                    'INVALID_AMOUNT',
                    f"Monto debe ser mayor a cero: {amount}",
                    column='amount'
                )
            return row
        
        # Convertir string a Decimal
        try:
            clean_value = str(amount).replace('$', '').replace(',', '').replace(' ', '').strip()
            decimal_amount = Decimal(clean_value)
            
            if decimal_amount <= 0:
                self._add_error(
                    row,
                    'INVALID_AMOUNT',
                    f"Monto debe ser mayor a cero: {amount}",
                    column='amount'
                )
            else:
                row.data['amount'] = decimal_amount
                
        except (InvalidOperation, ValueError):
            self._add_error(
                row,
                'INVALID_AMOUNT_FORMAT',
                f"Formato de monto inválido: '{amount}'",
                column='amount'
            )
        
        return row