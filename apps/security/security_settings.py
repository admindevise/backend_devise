from datetime import timedelta
from .models import SecurityConfiguration
#CONFIGURACION CUSTOM SECURITY
from django.db import connection

def has_table(table_name):
    return table_name in connection.introspection.table_names()

# Comprobamos si la tabla existe antes de acceder a ella
if has_table('security_securityconfiguration'):
    security_config = SecurityConfiguration.objects.first()

    if security_config:
        PASSWORD_SIMILARITY_LIMIT = security_config.password_similarity_limit
        MAX_FAILED_LOGIN_ATTEMPTS = security_config.max_failed_login_attempts
        LOGIN_LOCKOUT_DURATION = security_config.login_lockout_duration
        PASSWORD_EXPIRY_DAYS = security_config.password_expiry_days
        PASSWORD_MAX_DELTA_CHANGE = security_config.password_max_delta_change
    
    else:
        # Valores por defecto si no se ha configurado nada en la base de datos
        PASSWORD_SIMILARITY_LIMIT = 5
        MAX_FAILED_LOGIN_ATTEMPTS = 3
        LOGIN_LOCKOUT_DURATION = timedelta(minutes=30)
        PASSWORD_EXPIRY_DAYS = 90
        PASSWORD_MAX_DELTA_CHANGE = timedelta(minutes=30)

else:
        # Valores por defecto si no se ha configurado nada en la base de datos
        PASSWORD_SIMILARITY_LIMIT = 5
        MAX_FAILED_LOGIN_ATTEMPTS = 3
        LOGIN_LOCKOUT_DURATION = timedelta(minutes=30)
        PASSWORD_EXPIRY_DAYS = 90
        PASSWORD_MAX_DELTA_CHANGE = timedelta(minutes=30)

