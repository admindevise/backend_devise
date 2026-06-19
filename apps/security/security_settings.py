from datetime import timedelta

from django.db import connection

from .models import SecurityConfiguration


DEFAULT_SECURITY_SETTINGS = {
    "password_similarity_limit": 5,
    "max_failed_login_attempts": 3,
    "login_lockout_duration": timedelta(minutes=30),
    "password_expiry_days": 90,
    "password_max_delta_change": timedelta(minutes=30),
}


def has_table(table_name):
    return table_name in connection.introspection.table_names()


def get_security_settings():
    if not has_table("security_securityconfiguration"):
        return DEFAULT_SECURITY_SETTINGS.copy()

    security_config = SecurityConfiguration.objects.first()
    if not security_config:
        return DEFAULT_SECURITY_SETTINGS.copy()

    return {
        "password_similarity_limit": security_config.password_similarity_limit,
        "max_failed_login_attempts": security_config.max_failed_login_attempts,
        "login_lockout_duration": security_config.login_lockout_duration,
        "password_expiry_days": security_config.password_expiry_days,
        "password_max_delta_change": security_config.password_max_delta_change,
    }


def get_password_expiry_days():
    return get_security_settings()["password_expiry_days"]


def get_password_max_delta_change():
    return get_security_settings()["password_max_delta_change"]


def get_max_failed_login_attempts():
    return get_security_settings()["max_failed_login_attempts"]


def get_login_lockout_duration():
    return get_security_settings()["login_lockout_duration"]

