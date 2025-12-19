"""
Excepciones personalizadas para el sistema de importación contable.
"""


class AccountingImportError(Exception):
    """Error base para importación contable."""
    pass


class FileParsingError(AccountingImportError):
    """Error al parsear el archivo."""
    pass


class ValidationError(AccountingImportError):
    """Error de validación de datos."""
    def __init__(self, message: str, row_number: int = None, column: str = None):
        self.row_number = row_number
        self.column = column
        super().__init__(message)


class TransformationError(AccountingImportError):
    """Error al transformar datos."""
    pass


class PersistenceError(AccountingImportError):
    """Error al guardar en base de datos."""
    pass


class PipelineError(AccountingImportError):
    """Error en el pipeline de procesamiento."""
    pass