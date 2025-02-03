from django.db import models

class Fund(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    hd_wallet = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class FundPrice(models.Model):
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE)
    unitPrice = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField()

    def __str__(self):
        return f"{self.fund.name} - {self.timestamp}"