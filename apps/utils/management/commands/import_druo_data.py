"""
Comando para importar datos de Druo desde archivos CSV.

Uso:
    python manage.py import_druo_data --all
    python manage.py import_druo_data --banks
    python manage.py import_druo_data --account-types
    python manage.py import_druo_data --account-subtypes
    python manage.py import_druo_data --id-types
"""

import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError

from apps.druo.models import Bank, AccountType, AccountSubtype
from apps.user.models import IdType


class Command(BaseCommand):
    help = 'Importa datos de Druo desde archivos CSV'

    # Ruta base de los archivos CSV
    CSV_BASE_PATH = Path(__file__).resolve().parent.parent.parent

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Importar todos los datos')
        parser.add_argument('--banks', action='store_true', help='Importar bancos')
        parser.add_argument('--account-types', action='store_true', help='Importar tipos de cuenta')
        parser.add_argument('--account-subtypes', action='store_true', help='Importar subtipos de cuenta')
        parser.add_argument('--id-types', action='store_true', help='Importar tipos de identificación')

    def handle(self, *args, **options):
        if options['all']:
            self.import_banks()
            self.import_account_types()
            self.import_account_subtypes()
            self.import_id_types()
        else:
            if options['banks']:
                self.import_banks()
            if options['account_types']:
                self.import_account_types()
            if options['account_subtypes']:
                self.import_account_subtypes()
            if options['id_types']:
                self.import_id_types()

        if not any([options['all'], options['banks'], options['account_types'], 
                    options['account_subtypes'], options['id_types']]):
            self.stdout.write(self.style.WARNING(
                'No se especificó ninguna opción. Usa --help para ver las opciones disponibles.'
            ))

    def import_banks(self):
        """Importa bancos desde Institutions.csv"""
        csv_path = self.CSV_BASE_PATH / 'Institutions.csv'
        
        if not csv_path.exists():
            self.stdout.write(self.style.ERROR(f'Archivo no encontrado: {csv_path}'))
            return

        self.stdout.write('Importando bancos...')
        created, skipped = 0, 0

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 4:
                    obj, was_created = Bank.objects.get_or_create(
                        uuid=row[1],
                        defaults={
                            'institution_name': row[0],
                            'country': row[2],
                            'network': row[3],
                        }
                    )
                    if was_created:
                        created += 1
                        self.stdout.write(f'  Creado: {row[0]}')
                    else:
                        skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'Bancos: {created} creados, {skipped} existentes'
        ))

    def import_account_types(self):
        """Importa tipos de cuenta desde account_type.csv"""
        csv_path = self.CSV_BASE_PATH / 'account_type.csv'
        
        if not csv_path.exists():
            self.stdout.write(self.style.ERROR(f'Archivo no encontrado: {csv_path}'))
            return

        self.stdout.write('Importando tipos de cuenta...')
        created, skipped = 0, 0

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    obj, was_created = AccountType.objects.get_or_create(
                        value=row[0],
                        defaults={
                            'description': row[1],
                            'name': row[2],
                        }
                    )
                    if was_created:
                        created += 1
                        self.stdout.write(f'  Creado: {row[0]}')
                    else:
                        skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'Tipos de cuenta: {created} creados, {skipped} existentes'
        ))

    def import_account_subtypes(self):
        """Importa subtipos de cuenta desde account_subtype.csv"""
        csv_path = self.CSV_BASE_PATH / 'account_subtype.csv'
        
        if not csv_path.exists():
            self.stdout.write(self.style.ERROR(f'Archivo no encontrado: {csv_path}'))
            return

        self.stdout.write('Importando subtipos de cuenta...')
        created, skipped = 0, 0

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    obj, was_created = AccountSubtype.objects.get_or_create(
                        value=row[0],
                        defaults={
                            'description': row[1],
                            'name': row[2],
                        }
                    )
                    if was_created:
                        created += 1
                        self.stdout.write(f'  Creado: {row[0]}')
                    else:
                        skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'Subtipos de cuenta: {created} creados, {skipped} existentes'
        ))

    def import_id_types(self):
        """Importa tipos de identificación desde identification_types.csv"""
        csv_path = self.CSV_BASE_PATH / 'identification_types.csv'
        
        if not csv_path.exists():
            self.stdout.write(self.style.ERROR(f'Archivo no encontrado: {csv_path}'))
            return

        self.stdout.write('Importando tipos de identificación...')
        created, skipped = 0, 0

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    obj, was_created = IdType.objects.get_or_create(
                        value=row[0],
                        defaults={
                            'description': row[1],
                            'name': row[2],
                        }
                    )
                    if was_created:
                        created += 1
                        self.stdout.write(f'  Creado: {row[0]}')
                    else:
                        skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'Tipos de identificación: {created} creados, {skipped} existentes'
        ))
