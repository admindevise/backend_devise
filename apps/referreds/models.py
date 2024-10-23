from django.db import models
from apps.user.models import User
from config.settings import COMMISION_DC

class ReferralRegisterManager(models.Manager):

    def get_referrals_by_user(self, username):
        return list(
            self.filter(user_referred=username).order_by('level').values_list('user', flat=True)
        )
    

class ReferralRegister(models.Model):

    objects = ReferralRegisterManager()

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
    )
    user_referred = models.CharField(
        User,
        on_delete=models.PROTECT,
    )
    
    commission = models.FloatField(
        default = COMMISION_DC
    )
    
    class Meta:
        ordering = ['user']

    def __str__(self):
        return '{} -  {} - {}'.format(self.user, self.user_referred )
    
