"""
Builder para construir la cadena de validadores.
"""

from typing import List, Optional

from apps.fund.services.accounting.validators.base_validator import BaseValidator
from apps.fund.services.accounting.validators.required_fields_validator import RequiredFieldsValidator
from apps.fund.services.accounting.validators.category_validator import CategoryValidator
from apps.fund.services.accounting.validators.entry_type_validator import EntryTypeValidator
from apps.fund.services.accounting.validators.amount_validator import AmountValidator
from apps.fund.services.accounting.validators.date_validator import DateValidator
from apps.fund.services.accounting.validators.period_validator import PeriodValidator


class ValidatorChainBuilder:
    """
    Builder para construir la cadena de validadores.
    
    Uso:
        chain = ValidatorChainBuilder() \\
            .add_required_fields() \\
            .add_date_validation() \\
            .add_category_validation() \\
            .add_amount_validation() \\
            .add_entry_type_validation() \\
            .add_period_validation() \\
            .build()
    """
    
    def __init__(self):
        self._validators: List[BaseValidator] = []
    
    def add_required_fields(self) -> 'ValidatorChainBuilder':
        """Agrega validación de campos requeridos."""
        self._validators.append(RequiredFieldsValidator())
        return self
    
    def add_date_validation(self) -> 'ValidatorChainBuilder':
        """Agrega validación de fecha."""
        self._validators.append(DateValidator())
        return self
    
    def add_category_validation(self) -> 'ValidatorChainBuilder':
        """Agrega validación de categoría."""
        self._validators.append(CategoryValidator())
        return self
    
    def add_amount_validation(self) -> 'ValidatorChainBuilder':
        """Agrega validación de monto."""
        self._validators.append(AmountValidator())
        return self
    
    def add_entry_type_validation(self) -> 'ValidatorChainBuilder':
        """Agrega validación de tipo de entrada."""
        self._validators.append(EntryTypeValidator())
        return self
    
    def add_period_validation(self) -> 'ValidatorChainBuilder':
        """Agrega validación de período."""
        self._validators.append(PeriodValidator())
        return self
    
    def add_custom(self, validator: BaseValidator) -> 'ValidatorChainBuilder':
        """Agrega un validador personalizado."""
        self._validators.append(validator)
        return self
    
    def build(self) -> Optional[BaseValidator]:
        """
        Construye la cadena de validadores.
        
        Returns:
            El primer validador de la cadena (o None si está vacía)
        """
        if not self._validators:
            return None
        
        # Encadenar validadores
        for i in range(len(self._validators) - 1):
            self._validators[i].set_next(self._validators[i + 1])
        
        return self._validators[0]
    
    @classmethod
    def create_default_chain(cls) -> BaseValidator:
        """
        Crea la cadena de validación por defecto.
        
        Returns:
            Primer validador de la cadena
        """
        return cls() \
            .add_required_fields() \
            .add_date_validation() \
            .add_category_validation() \
            .add_amount_validation() \
            .add_entry_type_validation() \
            .add_period_validation() \
            .build()