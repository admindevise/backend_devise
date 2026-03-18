from rest_framework.exceptions import NotFound

def validate_entity_exists(entity_model, entity_name, entity_id):
    """Respuesta de error para entidad no encontrada"""
    if not entity_model.objects.filter(id=entity_id).exists():
        raise NotFound(
            detail=f'{entity_name} con ID {entity_id} no existe.',
            code=404
        )