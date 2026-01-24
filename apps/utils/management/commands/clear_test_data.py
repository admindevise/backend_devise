"""
Comando para limpiar datos de testing de Fund, Asset, Trading y Kaleido.

⚠️  PELIGRO: Este comando borra TODOS los registros de estos módulos.
Solo usar en entornos de desarrollo/testing.

Uso:
    python manage.py clear_test_data --confirm
    python manage.py clear_test_data --fund-only --confirm
    python manage.py clear_test_data --trading-only --confirm
    python manage.py clear_test_data --kaleido-only --confirm
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.apps import apps
from django.conf import settings


class Command(BaseCommand):
    help = '⚠️  Borra TODOS los registros de Fund, Asset, Trading y Kaleido (solo testing)'
    
    # Modelos a limpiar en orden (por dependencias)
    KALEIDO_MODELS = [
        # Kaleido debe borrarse primero (puede tener relaciones con Fund/Asset)
        'kaleido.InstanceOfTokenContract721',
        'kaleido.WalletSmartContract',
        'kaleido.Wallet',
        'kaleido.PromoteContract',
        'kaleido.CompileContract',
        'kaleido.AppContract',
    ]
    
    ASSET_MODELS = [
        # Assets dependen de Fund, deben borrarse primero
        'asset.AssetOperatingExpense',
        'asset.AssetOperatingIncome',
        'asset.AssetImage',
        'asset.Asset',
        # No borrar AssetType (es catálogo)
    ]
    
    FUND_MODELS = [
        # Dependientes de otros modelos
        'fund.TokenDistributionDetail',
        'fund.InvestmentDistributionRecord',
        'fund.DistributionPeriod',
        'fund.TokenTransaction',
        'fund.FundToken',
        'fund.AccountingImportError',
        'fund.AccountingImportBatch',
        'fund.FinancialSummary',
        'fund.AccountingBalance',
        'fund.InvoiceRecord',
        'fund.AccountingEntry',
        'fund.Account',
        'fund.AccountingPeriod',
        'fund.AccountCategory',
        'fund.Accountability',
        'fund.ReceipType',
        'fund.Transfers',
        'fund.Meetings',
        'fund.AccountStatement',
        'fund.Commissions',
        'fund.FundInvestment',
        'fund.InvestmentApplication',
        'fund.InvestorContract',
        'fund.TransferReceipt',
        'fund.FundOperatingExpense',
        'fund.FundOperatingIncome',
        'fund.TrustAgreement',
        'fund.FundPriceHistory',
        'fund.OthersI',
        'fund.FundSemestralDocument',
        # Modelo principal al final
        'fund.Fund',
    ]
    
    TRADING_MODELS = [
        # Dependientes primero
        'trading.PaymentRecord',
        'trading.TokenTransferRecord',
        'trading.MatchSelectionItem',
        'trading.MatchSelection',
        'trading.OrderContract',
        'trading.OrderBook',
        'trading.Transaction',
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirmar eliminación sin prompt interactivo',
        )
        parser.add_argument(
            '--fund-only',
            action='store_true',
            help='Solo borrar datos de Fund (incluye Asset y Kaleido)',
        )
        parser.add_argument(
            '--trading-only',
            action='store_true',
            help='Solo borrar datos de Trading',
        )
        parser.add_argument(
            '--asset-only',
            action='store_true',
            help='Solo borrar datos de Asset',
        )
        parser.add_argument(
            '--kaleido-only',
            action='store_true',
            help='Solo borrar datos de Kaleido',
        )

    def handle(self, *args, **options):
        # Verificar entorno (solo desarrollo)
        if not settings.DEBUG:
            raise CommandError(
                '❌ Este comando solo puede ejecutarse en modo DEBUG=True\n'
                'Para producción, use el admin de Django o scripts específicos.'
            )
        
        confirm = options.get('confirm')
        fund_only = options.get('fund_only')
        trading_only = options.get('trading_only')
        asset_only = options.get('asset_only')
        kaleido_only = options.get('kaleido_only')
        
        # Determinar qué modelos limpiar
        models_to_clear = []
        if kaleido_only:
            models_to_clear = self.KALEIDO_MODELS
            self.stdout.write(self.style.WARNING('🗑️  Limpiando solo módulo KALEIDO'))
        elif asset_only:
            models_to_clear = self.ASSET_MODELS
            self.stdout.write(self.style.WARNING('🗑️  Limpiando solo módulo ASSET'))
        elif fund_only:
            # Fund incluye Kaleido y Asset porque dependen de Fund
            models_to_clear = self.KALEIDO_MODELS + self.ASSET_MODELS + self.FUND_MODELS
            self.stdout.write(self.style.WARNING('🗑️  Limpiando módulos KALEIDO, ASSET y FUND'))
        elif trading_only:
            models_to_clear = self.TRADING_MODELS
            self.stdout.write(self.style.WARNING('🗑️  Limpiando solo módulo TRADING'))
        else:
            # Todo: Kaleido, Asset primero (dependen de Fund), luego Fund, luego Trading
            models_to_clear = self.KALEIDO_MODELS + self.ASSET_MODELS + self.FUND_MODELS + self.TRADING_MODELS
            self.stdout.write(self.style.WARNING('🗑️  Limpiando módulos KALEIDO, ASSET, FUND y TRADING'))
        
        # Contar registros antes
        total_before = self.count_records(models_to_clear)
        self.stdout.write(f'\n📊 Total de registros actuales: {total_before}\n')
        
        # Confirmación interactiva
        if not confirm:
            self.stdout.write(self.style.ERROR(
                '\n⚠️  ADVERTENCIA: Esta operación es IRREVERSIBLE\n'
            ))
            self.stdout.write('Se borrarán los siguientes modelos:')
            for model_path in models_to_clear:
                try:
                    app_label, model_name = model_path.split('.')
                    model = apps.get_model(app_label, model_name)
                    count = model.objects.count()
                    if count > 0:
                        self.stdout.write(f'  - {model_path}: {count} registros')
                except:
                    self.stdout.write(f'  - {model_path}: (modelo no encontrado)')
            
            response = input('\n¿Estás seguro? Escribe "y" para confirmar: ')
            if response != 'y':
                self.stdout.write(self.style.SUCCESS('✅ Operación cancelada'))
                return
        
        # Ejecutar limpieza
        self.clear_data(models_to_clear)

    def count_records(self, models_to_clear):
        """Cuenta el total de registros en los modelos especificados."""
        total = 0
        for model_path in models_to_clear:
            try:
                app_label, model_name = model_path.split('.')
                model = apps.get_model(app_label, model_name)
                total += model.objects.count()
            except:
                pass
        return total

    @transaction.atomic
    def clear_data(self, models_to_clear):
        """Borra todos los registros de los modelos especificados."""
        total_deleted = 0
        errors = []
        
        self.stdout.write('\n🔄 Iniciando limpieza...\n')
        
        for model_path in models_to_clear:
            try:
                app_label, model_name = model_path.split('.')
                model = apps.get_model(app_label, model_name)
                
                count = model.objects.count()
                if count > 0:
                    deleted, details = model.objects.all().delete()
                    total_deleted += deleted
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ {model_name}: {deleted} registros eliminados')
                    )
                else:
                    self.stdout.write(f'ℹ️  {model_name}: sin registros')
                    
            except LookupError:
                msg = f'⚠️  Modelo {model_path} no encontrado, omitiendo...'
                self.stdout.write(self.style.WARNING(msg))
                errors.append(msg)
            except Exception as e:
                msg = f'❌ Error eliminando {model_path}: {str(e)}'
                self.stdout.write(self.style.ERROR(msg))
                errors.append(msg)
        
        # Resumen final
        self.stdout.write('\n' + '='*60)
        self.stdout.write(
            self.style.SUCCESS(f'🎉 Total eliminado: {total_deleted} registros')
        )
        
        if errors:
            self.stdout.write(self.style.WARNING(f'\n⚠️  Se encontraron {len(errors)} errores'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ Limpieza completada sin errores'))
        
        self.stdout.write('='*60 + '\n')
