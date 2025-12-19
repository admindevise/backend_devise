"""
Filtro de transformación a entidades del modelo.
"""

import logging
from datetime import date
import calendar

from apps.fund.services.accounting.pipeline.base_filter import BaseFilter
from apps.fund.services.accounting.core.data_classes import PipelineContext

logger = logging.getLogger(__name__)


class TransformerFilter(BaseFilter):
    """
    Filtro que transforma datos normalizados a instancias del modelo.
    
    Input: normalized_rows
    Output: transformed_entries
    """
    
    def _process(self, context: PipelineContext) -> PipelineContext:
        logger.info(f"Transformando {len(context.normalized_rows)} filas a entidades")
        
        from apps.fund.models import AccountingEntry, AccountingPeriod
        
        entries = []
        
        for data in context.normalized_rows:
            entry_dict = self._transform_to_entry(data, context)
            entries.append(entry_dict)
        
        context.transformed_entries = entries
        
        logger.info(f"Entidades creadas: {len(entries)}")
        
        return context
    
    def _transform_to_entry(self, data: dict, context: PipelineContext) -> dict:
        """Transforma datos normalizados a diccionario para crear entrada."""
        entry_date = data.get('entry_date')
        
        # Obtener o crear período
        period = self._get_or_create_period(entry_date, context)
        
        # Obtener categoría del cache
        category = context.categories_cache.get(data.get('category_code'))
        
        return {
            'fund': context.fund,
            'period': period,
            'category': category,
            'entry_date': entry_date,
            'entry_type': data.get('entry_type'),
            'amount': data.get('amount'),
            'description': data.get('description', ''),
            'entry_status': 'draft',
            'entry_source': 'import',
            'third_party_name': data.get('third_party_name'),
            'third_party_id': data.get('third_party_id'),
            'external_reference': data.get('external_reference'),
            'import_batch': context.batch,
            'original_row_number': data.get('_row_number'),
            'created_by': context.user,
        }
    
    def _get_or_create_period(self, entry_date: date, context: PipelineContext):
        """Obtiene o crea el período contable."""
        from apps.fund.models import AccountingPeriod
        
        period_key = (entry_date.year, entry_date.month)
        
        if period_key in context.periods_cache:
            return context.periods_cache[period_key]
        
        # Calcular fecha de fin del mes
        last_day = calendar.monthrange(entry_date.year, entry_date.month)[1]
        end_date = entry_date.replace(day=last_day)
        
        period, _ = AccountingPeriod.objects.get_or_create(
            fund=context.fund,
            year=entry_date.year,
            month=entry_date.month,
            defaults={
                'start_date': entry_date.replace(day=1),
                'end_date': end_date,
                'period_status': 'open'
            }
        )
        
        context.periods_cache[period_key] = period
        return period