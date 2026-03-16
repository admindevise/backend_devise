from rest_framework import serializers
from apps.fund.models.core import Fund
from apps.trading.models.selection_models import MatchSelection

def _validate_common_context(context, require_selection_id=False):
    request = context.get('request') if context else None
    user = request.user if request else None
    fund_id = context.get('fund_id')
    selection_id = context.get('selection_id')

    if not user:
        raise serializers.ValidationError("Usuario no identificado")

    if not fund_id:
        raise serializers.ValidationError({
            'fund_id': "El campo 'fund_id' es obligatorio en la URL."
        })

    if not Fund.objects.filter(id=fund_id).exists():
        raise serializers.ValidationError({
            'fund_id': f"El fideicomiso con ID {fund_id} no existe."
        })

    if require_selection_id:
        if not selection_id:
            raise serializers.ValidationError({
                'selection_id': "El campo 'selection_id' es obligatorio en la URL."
            })
        if not MatchSelection.objects.filter(id=selection_id).exists():
            raise serializers.ValidationError({
                'selection_id': f"La selección con ID {selection_id} no existe."
            })

    return user, fund_id, selection_id