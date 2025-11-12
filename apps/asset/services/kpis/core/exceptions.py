"""
Excepciones personalizadas para el sistema de KPIs
"""


class AssetKPIError(Exception):
    """Excepción base para errores de KPIs"""
    pass


class DataValidationError(AssetKPIError):
    """Error cuando los datos no pasan validación"""
    pass


class PeriodValidationError(AssetKPIError):
    """Error cuando el período especificado es inválido"""
    pass


class InsufficientDataError(AssetKPIError):
    """Error cuando no hay suficientes datos para el cálculo"""
    pass


class CalculationError(AssetKPIError):
    """Error durante el proceso de cálculo"""
    pass


class ConfigurationError(AssetKPIError):
    """Error en la configuración del calculador"""
    pass