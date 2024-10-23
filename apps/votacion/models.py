from django.db import models
from apps.asset.models import ActivoInversion
from apps.user.models import User
from apps.utils.models import base_model

#La pregunta que se le va a mostrar a los inversores si la aprueba el admin Devise 
class Pregunta(base_model.BaseModel):
    pregunta = models.TextField(blank=True, null=True)
    activo = models.ForeignKey(
        ActivoInversion,
        on_delete=models.PROTECT
    )
    autor = models.ForeignKey(
        User,
        on_delete=models.PROTECT
    )
    aprobado_admin = models.BooleanField(blank=True, null=True)
    fecha_publicacion = models.DateTimeField()
    porcentaje_ganancia = models.IntegerField(max=100, min=1) #De los que contestan con cuanto % se ganaria el SI o No




