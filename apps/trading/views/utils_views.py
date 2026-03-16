from apps.fund.models.core import Fund
from rest_framework.exceptions import NotFound
from django.db.models import Q

def base_get_queryset(self, model, user_field):
    """Filtra órdenes del usuario o todas si es admin"""
    user = self.request.user
    fund_id = self.kwargs.get('fund_id')
    queryset = model.objects.exclude(status='CANCELLED')

    if fund_id:
        if not Fund.objects.filter(id=fund_id).exists():
            raise NotFound(
                detail=f'El fideicomiso con ID {fund_id} no existe.',
                code=404
            )
        queryset = queryset.filter(fund_id=fund_id)

    if not user.is_staff:
        # Filtrar por el campo de usuario dinámico
        filter_kwargs = {user_field: user}
        queryset = queryset.filter(
            Q(**filter_kwargs) | Q(created_by=user)
        )

    queryset = self.apply_date_filters(queryset)
    return queryset

def validate_entity_exists(entity_model, entity_name, entity_id):
    """Respuesta de error para entidad no encontrada"""
    if not entity_model.objects.filter(id=entity_id).exists():
        raise NotFound(
            detail=f'{entity_name} con ID {entity_id} no existe.',
            code=404
        )