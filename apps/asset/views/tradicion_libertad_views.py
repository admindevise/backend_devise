from apps.asset.serializers.serializers_activo import ActivoTradLibertadSerializer
from ..models import ActivoInversion, EstadoAprobacion
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from django.utils.translation import ugettext as _

from rest_framework.exceptions import PermissionDenied


@permission_classes([IsAuthenticated])
class CreateTradicionLibertadView(generics.UpdateAPIView):
    serializer_class = ActivoTradLibertadSerializer
    queryset = ActivoInversion.objects.all()

    def perform_update(self, serializer):
        user = self.request.user
        activo = ActivoInversion.objects.get(id=self.kwargs.get('pk'))
        user_sponsor = activo.sponsor.user
        if user != user_sponsor:
            raise PermissionDenied("Para cargar el Certificado de Tradición y Libertad debes der el Sponsor del activo")
        serializer.save(
                estado_aprobacion = EstadoAprobacion.objects.get(codigo="NUEVO_CERTIFICADO_TRADICION_Y_LIBERTAD"),
            )



