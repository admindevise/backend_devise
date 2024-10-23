from django.core.management.base import BaseCommand
from apps.security.models import SecurityConfiguration
from apps.user.models import User
from django.utils import timezone

config = SecurityConfiguration.objects.first()
max_failed_attempts = config.max_failed_login_attempts
login_lockout_duration = config.login_lockout_duration

class Command(BaseCommand):

    help = u'Go find users with failed attemtps then if time is done reset clear failed attempts'

    def handle(self, *args, **options):
        users = User.objects.filter(failed_attempts__gte=1 )
        now = timezone.now()

        for user in users:
            print("analizando a", user)
            print("analizando ", now - user.last_failed_access)
            if (now - user.last_failed_access) >= login_lockout_duration :
                print("Si ya paso el tiempo")
                user.failed_attempts=0
                user.save()
            else:
                print(" no no ha pasado el tiempo")


