from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from apps.kaleido.models import Wallet
from apps.kaleido.serializers.serializer_wallet import WalletSerializer

class ListUserWalletsView(APIView):
    """
    List all wallets associated with the authenticated user
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        wallets = Wallet.objects.filter(user=request.user)
        serializer = WalletSerializer(wallets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)