"""
Excepciones personalizadas para el sistema de KPIs
"""


class FundKPIError(Exception):
    """Excepción base para errores de KPIs"""
    pass


class DataValidationError(FundKPIError):
    """Error cuando los datos no pasan validación"""
    pass


class PeriodValidationError(FundKPIError):
    """Error cuando el período especificado es inválido"""
    pass


class InsufficientDataError(FundKPIError):
    """Error cuando no hay suficientes datos para el cálculo"""
    pass


class CalculationError(FundKPIError):
    """Error durante el proceso de cálculo"""
    pass


class ConfigurationError(FundKPIError):
    """Error en la configuración del calculador"""
    pass