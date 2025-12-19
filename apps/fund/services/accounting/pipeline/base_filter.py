"""
Clase base para filtros del pipeline (Pipes and Filters Pattern).
"""

from abc import ABC, abstractmethod
import logging

from apps.fund.services.accounting.core.data_classes import PipelineContext
from apps.fund.services.accounting.core.exceptions import PipelineError

logger = logging.getLogger(__name__)


class BaseFilter(ABC):
    """
    Filtro base del pipeline.
    
    Cada filtro:
    1. Recibe el contexto
    2. Procesa su tarea específica
    3. Modifica el contexto
    4. Pasa al siguiente filtro
    """
    
    def __init__(self):
        self._next_filter: 'BaseFilter' = None
        self.name: str = self.__class__.__name__
    
    def set_next(self, filter: 'BaseFilter') -> 'BaseFilter':
        """Establece el siguiente filtro en el pipeline."""
        self._next_filter = filter
        return filter
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Ejecuta el filtro y pasa al siguiente.
        
        Args:
            context: Contexto del pipeline
            
        Returns:
            Contexto modificado
        """
        # Verificar si el pipeline está detenido
        if context.is_stopped:
            logger.info(f"Pipeline detenido antes de {self.name}: {context.stop_reason}")
            return context
        
        # Actualizar paso actual
        context.current_step = self.name
        logger.info(f"Ejecutando filtro: {self.name}")
        
        try:
            # Ejecutar procesamiento específico
            context = self._process(context)
            
            # Verificar si debemos continuar
            if context.is_stopped:
                return context
            
            # Pasar al siguiente filtro
            if self._next_filter:
                return self._next_filter.execute(context)
            
            return context
            
        except Exception as e:
            logger.exception(f"Error en filtro {self.name}: {e}")
            context.stop_pipeline(f"Error en {self.name}: {str(e)}")
            raise PipelineError(f"Error en {self.name}: {str(e)}")
    
    @abstractmethod
    def _process(self, context: PipelineContext) -> PipelineContext:
        """
        Procesamiento específico del filtro.
        
        Args:
            context: Contexto del pipeline
            
        Returns:
            Contexto modificado
        """
        pass