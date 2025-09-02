from django.db import models
from apps.utils.models import base_model

class TransferReceipt(base_model.BaseModel):
    user = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name="transfer_receipts")
    transaction_id = models.CharField(max_length=255)
    fund = models.ForeignKey('Fund', on_delete=models.CASCADE, related_name="transfer_receipts", null=True, blank=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.transaction_id} - {self.fund.name if self.fund else 'N/A'}"

    