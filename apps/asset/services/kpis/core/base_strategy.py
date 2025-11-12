"""
Clase base abstracta para todas las Strategies de KPIs
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from apps.asset.models.core import Asset


class BaseKPIStrategy(ABC):
    """
    Strategy base para cálculos de KPIs.
    
    Todas las strategies concretas (NOI, Cap Rate, ROI, etc.)
    deben heredar de esta clase e implementar los métodos abstractos.
    """
    
    def __init__(self, asset: Asset):
        """
        Args:
            asset: Instancia del Asset
        """
        if not asset:
            raise ValueError("Asset is required")
        
        if not asset.pk:
            raise ValueError("Asset must be saved to database")
        
        self.asset = asset
    
    @abstractmethod
    def calculate(self, **kwargs) -> Dict[str, Any]:
        """
        Método principal de cálculo.
        
        Returns:
            dict: Resultado del cálculo del KPI
        """
        pass
    
    @abstractmethod
    def validate_prerequisites(self) -> Dict[str, Any]:
        """
        Valida que existan los datos mínimos necesarios.
        
        Returns:
            dict: Estado de validación
        """
        pass
    
    def get_strategy_name(self) -> str:
        """Retorna el nombre de la strategy"""
        return self.__class__.__name__