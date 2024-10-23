from django.db import models
from datetime import timedelta

class SecurityConfiguration(models.Model):
    password_change_frecuency = models.PositiveIntegerField(default=30)
    password_similarity_limit = models.PositiveIntegerField(default=5)
    max_failed_login_attempts = models.PositiveIntegerField(default=3)
    login_lockout_duration = models.DurationField(default=timedelta(minutes=30))
    password_expiry_days = models.PositiveIntegerField(default=90)
    password_max_delta_change = models.DurationField(default=timedelta(minutes=30))

