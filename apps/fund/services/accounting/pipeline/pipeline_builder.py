"""
Builder para construir el pipeline de importación.
"""

from typing import List

from apps.fund.services.accounting.pipeline.base_filter import BaseFilter
from apps.fund.services.accounting.pipeline.filters.reader_filter import ReaderFilter
from apps.fund.services.accounting.pipeline.filters.validator_filter import ValidatorFilter
from apps.fund.services.accounting.pipeline.filters.normalizer_filter import NormalizerFilter
from apps.fund.services.accounting.pipeline.filters.transformer_filter import TransformerFilter
from apps.fund.services.accounting.pipeline.filters.saver_filter import SaverFilter


class PipelineBuilder:
    """
    Builder para construir el pipeline de importación.
    
    Uso:
        pipeline = PipelineBuilder() \\
            .add_reader() \\
            .add_validator() \\
            .add_normalizer() \\
            .add_transformer() \\
            .add_saver() \\
            .build()
    """
    
    def __init__(self):
        self._filters: List[BaseFilter] = []
    
    def add_reader(self) -> 'PipelineBuilder':
        """Agrega filtro de lectura."""
        self._filters.append(ReaderFilter())
        return self
    
    def add_validator(self, validator_chain=None) -> 'PipelineBuilder':
        """Agrega filtro de validación."""
        self._filters.append(ValidatorFilter(validator_chain))
        return self
    
    def add_normalizer(self) -> 'PipelineBuilder':
        """Agrega filtro de normalización."""
        self._filters.append(NormalizerFilter())
        return self
    
    def add_transformer(self) -> 'PipelineBuilder':
        """Agrega filtro de transformación."""
        self._filters.append(TransformerFilter())
        return self
    
    def add_saver(self) -> 'PipelineBuilder':
        """Agrega filtro de persistencia."""
        self._filters.append(SaverFilter())
        return self
    
    def add_custom(self, filter: BaseFilter) -> 'PipelineBuilder':
        """Agrega un filtro personalizado."""
        self._filters.append(filter)
        return self
    
    def build(self) -> BaseFilter:
        """
        Construye el pipeline encadenando los filtros.
        
        Returns:
            Primer filtro del pipeline
        """
        if not self._filters:
            raise ValueError("Pipeline vacío")
        
        # Encadenar filtros
        for i in range(len(self._filters) - 1):
            self._filters[i].set_next(self._filters[i + 1])
        
        return self._filters[0]
    
    @classmethod
    def create_default_pipeline(cls) -> BaseFilter:
        """
        Crea el pipeline por defecto completo.
        
        Pipeline: Reader → Validator → Normalizer → Transformer → Saver
        """
        return cls() \
            .add_reader() \
            .add_validator() \
            .add_normalizer() \
            .add_transformer() \
            .add_saver() \
            .build()