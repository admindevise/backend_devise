"""
Filtro de persistencia en base de datos.
"""

import logging

from django.db import transaction

from apps.fund.services.accounting.pipeline.base_filter import BaseFilter
from apps.fund.services.accounting.core.data_classes import PipelineContext

logger = logging.getLogger(__name__)


class SaverFilter(BaseFilter):
    """
    Filtro que persiste las entidades en la base de datos.
    
    Input: transformed_entries
    Output: created_entries (IDs de entradas creadas)
    """
    
    def _process(self, context: PipelineContext) -> PipelineContext:
        # Si es dry_run, no guardar
        if context.dry_run:
            logger.info("Modo dry_run: saltando persistencia")
            return context
        
        logger.info(f"Guardando {len(context.transformed_entries)} entradas")
        
        from apps.fund.models import AccountingEntry
        
        try:
            with transaction.atomic():
                # Crear entradas en batch
                entries = AccountingEntry.objects.bulk_create([
                    AccountingEntry(**entry_data)
                    for entry_data in context.transformed_entries
                ])
                
                # Guardar IDs creados en contexto
                created_ids = [entry.id for entry in entries]
                
                logger.info(f"Entradas guardadas: {len(created_ids)}")
                
                # Actualizar batch si existe
                if context.batch:
                    self._update_batch(context, len(created_ids))
                
        except Exception as e:
            logger.exception(f"Error guardando entradas: {e}")
            context.stop_pipeline(f"Error de persistencia: {str(e)}")
            raise
        
        return context
    
    def _update_batch(self, context: PipelineContext, created_count: int):
        """Actualiza el batch de importación con los resultados."""
        from django.utils import timezone
        
        context.batch.import_status = 'completed' if not context.errors else 'partial'
        context.batch.total_rows = len(context.parsed_rows)
        context.batch.processed_rows = len(context.parsed_rows)
        context.batch.successful_rows = created_count
        context.batch.failed_rows = len(context.parsed_rows) - len(context.valid_rows)
        context.batch.completed_at = timezone.now()
        context.batch.save()