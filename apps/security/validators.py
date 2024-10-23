import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class NoSequenceValidator:
    def __init__(self, min_length=8):
        self.min_length = min_length

    def validate(self, password, user=None):
        sequences = [
            '123', '234', '345', '456', '567', '678', '789',  # Secuencias numéricas
            'abc', 'bcd', 'cde', 'def', 'efg', 'fgh', 'ghi',  # Secuencias de letras
            'qwerty', 'asdf', 'zxcv', 'poiu', 'lkjh'  # Secuencias de letras

        ]

        for sequence in sequences:
            if sequence in password.lower():
                raise ValidationError(
                    _("La contraseña no puede contener secuencias lógicas como '{}'.")
                    .format(sequence),
                    code='password_has_sequence',
                )

    def get_help_text(self):
        return _(
            "La contraseña no puede contener secuencias lógicas de números o letras."
        )