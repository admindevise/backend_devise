from django.core.management.base import BaseCommand
from apps.info_socioeconomic.models import OriginFund


class Command(BaseCommand):
    help = 'Precarga las opciones más comunes de OriginFund'

    def handle(self, *args, **options):
        origin_funds = [
            'Salario',
            'Negocio propio',
            'Inversiones',
            'Herencia',
            'Préstamo',
            'Bonificación',
            'Pensión',
            'Renta de propiedades',
            'Freelance',
            'Otros',
        ]

        for fund_name in origin_funds:
            obj, created = OriginFund.objects.get_or_create(name=fund_name)
            status = 'Creado' if created else 'Existente'
            self.stdout.write(f'✓ {fund_name} - {status}')

        self.stdout.write('\n✓ Carga de OriginFund completada')