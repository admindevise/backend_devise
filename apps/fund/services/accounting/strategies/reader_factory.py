"""
Factory para seleccionar el reader strategy apropiado.
"""

from typing import List, Optional

from apps.fund.services.accounting.strategies.base_reader import BaseReaderStrategy
from apps.fund.services.accounting.strategies.txt_reader_strategy import TxtReaderStrategy
from apps.fund.services.accounting.strategies.xlsx_reader_strategy import XlsxReaderStrategy
from apps.fund.services.accounting.core.data_classes import ColumnMapping


class ReaderFactory:
    """
    Factory que selecciona el reader apropiado según el archivo.
    """
    
    _strategies: List[type] = [
        TxtReaderStrategy,
        XlsxReaderStrategy,
    ]
    
    @classmethod
    def create(
        cls,
        filename: str,
        column_mapping: List[ColumnMapping] = None,
        **kwargs
    ) -> BaseReaderStrategy:
        """
        Crea el reader apropiado para el archivo.
        
        Args:
            filename: Nombre del archivo
            column_mapping: Mapeo de columnas
            **kwargs: Argumentos adicionales para el reader
            
        Returns:
            BaseReaderStrategy: Reader apropiado
            
        Raises:
            ValueError: Si no hay reader para el tipo de archivo
        """
        for strategy_class in cls._strategies:
            # Crear instancia temporal para verificar
            temp_instance = strategy_class(column_mapping)
            if temp_instance.can_handle(filename):
                return strategy_class(column_mapping, **kwargs)
        
        raise ValueError(f"No hay reader disponible para: {filename}")
    
    @classmethod
    def register_strategy(cls, strategy_class: type):
        """Registra un nuevo strategy de lectura."""
        if strategy_class not in cls._strategies:
            cls._strategies.append(strategy_class)