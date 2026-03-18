from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.utils.views.global_utils_views import validate_entity_exists
from apps.utils.core_permissions.api_permissions import RegistryPermission
from apps.fund.models.core import Fund
from apps.trading.services_core.find_matches_service import (
    FindMatchesService,
    FindMatchesPermissionDenied,
    FindMatchesObjectNotFound,
    FindMatchesBadRequest
)


class FindMatchesAPIView(APIView):
    permission_classes = [IsAuthenticated, RegistryPermission]
    
    def initial(self, request, *args, **kwargs):
        validate_entity_exists(Fund, 'Fideicomiso', self.kwargs.get('fund_id'))
        super().initial(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        service = FindMatchesService()
        purchase_order_id = request.data.get("purchase_order_id")
        sales_order_id = request.data.get("sales_order_id")

        try:
            result = service.execute(
                user=request.user,
                purchase_order_id=purchase_order_id,
                sales_order_id=sales_order_id
            )
            return Response(result, status=status.HTTP_200_OK)

        except FindMatchesBadRequest as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except FindMatchesPermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except FindMatchesObjectNotFound as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {"detail": f"Error al procesar coincidencias: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )