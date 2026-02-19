from django.utils import timezone
from datetime import datetime, timedelta
import pytz
from rest_framework.exceptions import ValidationError

class DateFilterMixin:
    """
    Mixin para aplicar filtros de fecha a un queryset.
    Procesa los parámetros 'start_date' y 'end_date' de la consulta
    y aplica los filtros correspondientes al queryset.
    """
    date_field = 'created_at'  # Campo de fecha predeterminado, puede ser sobreescrito en las clases hijas
    
    def apply_date_filters(self, queryset):
        """
        Aplica filtros de fecha al queryset basado en los parámetros de consulta.
        
        Acepta formatos:
        - YYYY-MM-DD HH:MM:SS
        - YYYY-MM-DD
        
        Parámetros:
        - queryset: QuerySet al que se aplicarán los filtros
        
        Retorna:
        - QuerySet filtrado
        """
        # Obtener parámetros de consulta
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        # Aplicar filtro de fecha de inicio
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
                except ValueError:
                    raise ValidationError({
                        "start_date": "Formato de fecha inválido. Use 'YYYY-MM-DD' o 'YYYY-MM-DD HH:MM:SS'."
                    })
            
            # Hacer la fecha consciente de la zona horaria
            current_tz = timezone.get_current_timezone()
            start_date_aware = timezone.make_aware(start_date_obj, timezone=current_tz)
            
            # Aplicar filtro
            filter_kwargs = {f'{self.date_field}__gte': start_date_aware}
            queryset = queryset.filter(**filter_kwargs)
        
        # Aplicar filtro de fecha de fin
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                    # Si solo es fecha sin hora, establecer a final del día
                    end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)
                except ValueError:
                    raise ValidationError({
                        "end_date": "Formato de fecha inválido. Use 'YYYY-MM-DD' o 'YYYY-MM-DD HH:MM:SS'."
                    })
            
            # Hacer la fecha consciente de la zona horaria
            current_tz = timezone.get_current_timezone()
            end_date_aware = timezone.make_aware(end_date_obj, timezone=current_tz)
            
            # Aplicar filtro
            filter_kwargs = {f'{self.date_field}__lte': end_date_aware}
            queryset = queryset.filter(**filter_kwargs)
        
        return queryset