from decimal import Decimal
from typing import Dict, Optional, Any
from django.db import transaction
from django.utils import timezone
from datetime import date
from django.core.exceptions import ValidationError

from apps.fund.models.core import Fund
from apps.fund.models.distributions import DistributionPeriod
from apps.fund.services.fund_calculations import FundCalculationService
from apps.audit.audit_service import AuditService


class DistributionServiceError(Exception):
    """Excepción personalizada para errores del servicio de distribuciones"""
    pass


class DistributionService:
    """
    Servicio básico para gestionar distribuciones de fondos.
    Se enfoca en la creación de períodos de distribución.
    """
    
    def __init__(self, fund: Fund):
        self.fund = fund
        self.calc_service = FundCalculationService(fund)
    
    # ========================================
    # MÉTODOS PRINCIPALES
    # ========================================
    
    def create_distribution_period(
        self,
        total_amount: Decimal,
        distribution_type: str,
        period_year: int,
        period_month: Optional[int] = None,
        period_quarter: Optional[int] = None,
        payment_date: Optional[date] = None,
        record_date: Optional[date] = None,
        created_by=None,
        distribution_notes: str = "",
        request=None
    ) -> DistributionPeriod:
        """
        Crea un nuevo período de distribución.
        
        Args:
            total_amount: Monto total a distribuir
            distribution_type: Tipo de distribución (monthly, quarterly, etc.)
            period_year: Año del período
            period_month: Mes del período (requerido para monthly)
            period_quarter: Trimestre del período (requerido para quarterly)
            payment_date: Fecha de pago (por defecto hoy)
            record_date: Fecha de registro (por defecto hoy)
            created_by: Usuario que crea la distribución
            distribution_notes: Notas adicionales
            request: Request para auditoría
            
        Returns:
            DistributionPeriod: Período de distribución creado
            
        Raises:
            DistributionServiceError: Si hay errores en la validación o creación
        """
        audit_log = None
        
        try:
            # 1. Crear log de auditoría inicial
            if request and created_by:
                audit_log = AuditService.log_action(
                    request=request,
                    action_code="DISTRIBUTION_CREATE",
                    obj=self.fund,
                    details={
                        'fund_name': self.fund.name,
                        'total_amount': str(total_amount),
                        'distribution_type': distribution_type,
                        'period_year': period_year,
                        'period_month': period_month,
                        'created_by_email': created_by.email if created_by else None
                    },
                    status='PENDING'
                )
            
            # 2. Validar datos de entrada
            self._validate_distribution_data(
                total_amount, distribution_type, period_year, 
                period_month, period_quarter
            )
            
            # 3. Validar monto de distribución
            validation_result = self.calc_service.validate_distribution_amount(total_amount)
            if not validation_result['is_valid']:
                errors = '; '.join(validation_result['errors'])
                raise DistributionServiceError(f"Validación fallida: {errors}")
            
            # 4. Calcular información de distribución
            distribution_info = self.calc_service.calculate_distributions(total_amount)
            if 'error' in distribution_info:
                raise DistributionServiceError(distribution_info['error'])
            
            # 5. Establecer fechas por defecto
            today = timezone.now().date()
            payment_date = payment_date or today
            record_date = record_date or today
            
            # 6. Verificar duplicados
            self._check_duplicate_distribution(
                distribution_type, period_year, period_month, period_quarter
            )
            
            with transaction.atomic():
                # 7. Crear período de distribución
                distribution_period = DistributionPeriod.objects.create(
                    fund=self.fund,
                    distribution_type=distribution_type,
                    period_year=period_year,
                    period_month=period_month,
                    period_quarter=period_quarter,
                    total_distribution_amount=total_amount,
                    total_tokens_outstanding=distribution_info['total_issued_tokens'],
                    distribution_per_token=distribution_info['rent_per_token'],
                    record_date=record_date,
                    ex_dividend_date=record_date,  # Por simplicidad, misma fecha
                    payment_date=payment_date,
                    created_by=created_by,
                    status=DistributionPeriod.DistributionStatus.DRAFT,
                    distribution_notes=distribution_notes,
                    calculation_metadata={
                        'calculation_info': str(distribution_info),
                        'validation_warnings': validation_result.get('warnings', []),
                        'creation_timestamp': timezone.now().isoformat()
                    }
                )
            
            # 8. Actualizar auditoría a SUCCESS
            if audit_log:
                audit_log.status = 'SUCCESS'
                audit_log.details.update({
                    'distribution_period_id': distribution_period.id,
                    'distribution_per_token': str(distribution_period.distribution_per_token),
                    'total_tokens_outstanding': distribution_period.total_tokens_outstanding
                })
                audit_log.save(update_fields=['status', 'details'])
            
            return distribution_period
            
        except Exception as e:
            # Actualizar auditoría a ERROR si existe
            if audit_log:
                audit_log.status = 'ERROR'
                audit_log.details.update({
                    'error_message': str(e),
                    'error_type': type(e).__name__
                })
                audit_log.save(update_fields=['status', 'details'])
            
            if isinstance(e, DistributionServiceError):
                raise e
            else:
                raise DistributionServiceError(f"Error creando período de distribución: {str(e)}")
    
    # ========================================
    # MÉTODOS DE VALIDACIÓN
    # ========================================
    
    def _validate_distribution_data(
        self, 
        total_amount: Decimal, 
        distribution_type: str, 
        period_year: int,
        period_month: Optional[int] = None,
        period_quarter: Optional[int] = None
    ):
        """Valida los datos de entrada para crear distribución"""
        
        # Validar monto
        if total_amount <= 0:
            raise DistributionServiceError("El monto total debe ser mayor a cero")
        
        # Validar tipo de distribución
        valid_types = [choice[0] for choice in DistributionPeriod.DistributionType.choices]
        if distribution_type not in valid_types:
            raise DistributionServiceError(f"Tipo de distribución inválido. Opciones: {valid_types}")
        
        # Validar año
        current_year = timezone.now().year
        if period_year < 2020 or period_year > current_year + 5:
            raise DistributionServiceError("Año del período fuera del rango válido")
        
        # Validar mes para distribuciones mensuales
        if distribution_type == DistributionPeriod.DistributionType.MONTHLY:
            if not period_month or period_month < 1 or period_month > 12:
                raise DistributionServiceError("Distribuciones mensuales requieren un mes válido (1-12)")
        
        # Validar trimestre para distribuciones trimestrales
        if distribution_type == DistributionPeriod.DistributionType.QUARTERLY:
            if not period_quarter or period_quarter < 1 or period_quarter > 4:
                raise DistributionServiceError("Distribuciones trimestrales requieren un trimestre válido (1-4)")
    
    def _check_duplicate_distribution(
        self,
        distribution_type: str,
        period_year: int,
        period_month: Optional[int] = None,
        period_quarter: Optional[int] = None
    ):
        """Verifica que no exista una distribución duplicada"""
        
        filters = {
            'fund': self.fund,
            'distribution_type': distribution_type,
            'period_year': period_year
        }
        
        if period_month:
            filters['period_month'] = period_month
        if period_quarter:
            filters['period_quarter'] = period_quarter
        
        if DistributionPeriod.objects.filter(**filters).exists():
            period_desc = f"{period_year}"
            if period_month:
                period_desc += f"-{period_month:02d}"
            elif period_quarter:
                period_desc += f" Q{period_quarter}"
            
            raise DistributionServiceError(
                f"Ya existe una distribución {distribution_type} para el período {period_desc}"
            )
    
    # ========================================
    # MÉTODOS DE CONSULTA
    # ========================================
    
    def get_distribution_by_id(self, distribution_id: int) -> Optional[DistributionPeriod]:
        """Obtiene una distribución por ID"""
        try:
            return DistributionPeriod.objects.get(id=distribution_id, fund=self.fund)
        except DistributionPeriod.DoesNotExist:
            return None
    
    def get_fund_distributions(self, status: Optional[str] = None, limit: int = 10) -> list:
        """
        Obtiene las distribuciones del fondo
        
        Args:
            status: Filtro por estado (opcional)
            limit: Número máximo de resultados
            
        Returns:
            list: Lista de distribuciones
        """
        queryset = DistributionPeriod.objects.filter(fund=self.fund)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return list(queryset.order_by('-payment_date')[:limit])
    
    def calculate_distribution_preview(self, total_amount: Decimal) -> Dict[str, Any]:
        """
        Calcula una vista previa de distribución sin crearla
        
        Args:
            total_amount: Monto total a distribuir
            
        Returns:
            dict: Vista previa de la distribución
        """
        try:
            # Validar monto básico
            if total_amount <= 0:
                return {'error': 'El monto debe ser mayor a cero'}
            
            # Obtener cálculos de distribución
            distribution_info = self.calc_service.calculate_distributions(total_amount)
            
            if 'error' in distribution_info:
                return distribution_info
            
            # Obtener validaciones
            validation_result = self.calc_service.validate_distribution_amount(total_amount)
            
            return {
                'fund_info': {
                    'fund_id': self.fund.id,
                    'fund_name': self.fund.name
                },
                'distribution_calculation': distribution_info,
                'validation_result': validation_result,
                'preview_timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {'error': f'Error calculando vista previa: {str(e)}'}
    
    # ========================================
    # MÉTODOS DE ESTADO
    # ========================================
    
    @transaction.atomic
    def update_distribution_status(
        self, 
        distribution_id: int, 
        new_status: str,
        updated_by=None,
        notes: str = "",
        request=None
    ) -> DistributionPeriod:
        """
        Actualiza el estado de una distribución
        
        Args:
            distribution_id: ID de la distribución
            new_status: Nuevo estado
            updated_by: Usuario que actualiza
            notes: Notas adicionales
            request: Request para auditoría
            
        Returns:
            DistributionPeriod: Distribución actualizada
        """
        try:
            distribution = self.get_distribution_by_id(distribution_id)
            if not distribution:
                raise DistributionServiceError("Distribución no encontrada")
            
            # Validar nuevo estado
            valid_statuses = [choice[0] for choice in DistributionPeriod.DistributionStatus.choices]
            if new_status not in valid_statuses:
                raise DistributionServiceError(f"Estado inválido. Opciones: {valid_statuses}")
            
            old_status = distribution.status
            distribution.status = new_status
            
            # Actualizar campos adicionales según el estado
            if new_status == DistributionPeriod.DistributionStatus.APPROVED:
                distribution.approved_by = updated_by
                distribution.approved_at = timezone.now()
            elif new_status == DistributionPeriod.DistributionStatus.COMPLETED:
                distribution.processed_at = timezone.now()
            
            # Agregar notas si se proporcionaron
            if notes:
                current_notes = distribution.distribution_notes or ""
                timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                new_note = f"[{timestamp}] {notes}"
                distribution.distribution_notes = f"{current_notes}\n{new_note}".strip()
            
            distribution.save()
            
            # Crear log de auditoría
            if request and updated_by:
                AuditService.log_action(
                    request=request,
                    action_code="DISTRIBUTION_STATUS_UPDATE",
                    obj=distribution,
                    details={
                        'distribution_id': distribution.id,
                        'old_status': old_status,
                        'new_status': new_status,
                        'updated_by_email': updated_by.email,
                        'notes': notes
                    }
                )
            
            return distribution
            
        except Exception as e:
            if isinstance(e, DistributionServiceError):
                raise e
            else:
                raise DistributionServiceError(f"Error actualizando estado: {str(e)}")
            
            
    # ============================================
    # DISTRIBUCIONES POR INVERSIÓN
    # ============================================
    @transaction.atomic
    def create_distribution_records(
        self,
        distribution_period: DistributionPeriod,
        created_by=None,
        request=None
    ) -> Dict[str, any]:
        """
        Crea registros de distribución en COP para todos los inversores.
        
        Args:
            distribution_period: Período de distribución
            created_by: Usuario que crea los registros
            request: Request para auditoría
            
        Returns:
            dict: Resumen de registros creados
        """
        from apps.fund.models.distributions import InvestmentDistributionRecord
        from apps.fund.models.membership import FundInvestment
        
        try:
            # Obtener distribuciones calculadas en COP
            cop_distributions = self.calc_service.calculate_batch_distributions(
                distribution_period.total_distribution_amount
            )
            
            if 'error' in cop_distributions:
                raise DistributionServiceError(cop_distributions['error'])
            
            records_created = []
            total_records = 0
            
            for user_dist in cop_distributions['user_distributions']:
                # Obtener inversiones activas del usuario
                user_investments = FundInvestment.objects.filter(
                    application__user_id=user_dist['user_id'],
                    application__fund=self.fund,
                    investment_status=FundInvestment.InvestmentStatus.ACTIVE
                )
                
                for investment in user_investments:
                    # Crear registro de distribución en COP
                    distribution_record = InvestmentDistributionRecord.objects.create(
                        distribution_period=distribution_period,
                        investment=investment,
                        distribution_type=InvestmentDistributionRecord.DistributionType.COP_AMOUNT,
                        
                        # Montos en COP
                        gross_distribution_amount_cop=user_dist['user_distribution_amount'],
                        withholding_tax_cop=Decimal('0.00'),  # Configurar según necesidades
                        net_distribution_amount_cop=user_dist['user_distribution_amount'],
                        
                        # Información de tokens
                        tokens_held_on_record_date=user_dist['user_tokens'],
                        token_ids_snapshot=[],  # Llenar según necesidades
                        participation_percentage=user_dist['participation_percentage'],
                        
                        # Estado inicial
                        payment_status=InvestmentDistributionRecord.PaymentStatus.CALCULATED,
                        
                        # Metadatos
                        calculation_metadata={
                            'participation_percentage': str(user_dist['participation_percentage']),
                            'calculation_timestamp': timezone.now().isoformat(),
                            'created_by': created_by.email if created_by else None,
                            'distribution_method': 'COP_BASED'
                        }
                    )
                    
                    records_created.append({
                        'record_id': distribution_record.id,
                        'user_email': user_dist['user_email'],
                        'cop_amount': float(user_dist['user_distribution_amount']),
                        'tokens_held': user_dist['user_tokens']
                    })
                    total_records += 1
            
            # Crear log de auditoría
            if request and created_by:
                AuditService.log_action(
                    request=request,
                    action_code="DISTRIBUTION_RECORDS_CREATED",
                    obj=distribution_period,
                    details={
                        'distribution_period_id': distribution_period.id,
                        'total_records_created': total_records,
                        'total_amount_cop': str(distribution_period.total_distribution_amount),
                        'distribution_type': 'COP_BASED'
                    }
                )
            
            return {
                'success': True,
                'distribution_period_id': distribution_period.id,
                'total_records_created': total_records,
                'records_summary': records_created,
                'fund_info': cop_distributions['fund_info'],
                'summary': cop_distributions['summary']
            }
            
        except Exception as e:
            raise DistributionServiceError(f"Error creando registros de distribución COP: {str(e)}")
    
    @transaction.atomic
    def verify_and_convert_to_tokens(
        self,
        distribution_record_id: int,
        token_price_cop: Optional[Decimal] = None,
        verified_by=None,
        request=None
    ) -> Dict[str, any]:
        """
        Verifica y convierte una distribución COP a tokens.
        
        Args:
            distribution_record_id: ID del registro de distribución
            token_price_cop: Precio del token en COP (opcional)
            verified_by: Usuario que verifica
            request: Request para auditoría
            
        Returns:
            dict: Resultado de la verificación y conversión
        """
        from apps.fund.models.distributions import InvestmentDistributionRecord
        
        try:
            # Obtener registro de distribución
            record = InvestmentDistributionRecord.objects.select_related(
                'distribution_period',
                'investment__application__user'
            ).get(id=distribution_record_id)
            
            # Validar estado
            if record.payment_status not in [
                InvestmentDistributionRecord.PaymentStatus.CALCULATED,
                InvestmentDistributionRecord.PaymentStatus.PENDING
            ]:
                raise DistributionServiceError(
                    f"El registro debe estar en estado CALCULATED o PENDING, actual: {record.payment_status}"
                )
            
            # Usar precio del fondo si no se proporciona
            if token_price_cop is None:
                token_price_cop = self.fund.price_per_unit
            
            # Calcular conversión
            conversion_info = self.calc_service.calculate_cop_to_token_conversion(
                record.net_distribution_amount_cop,
                token_price_cop
            )
            
            if 'error' in conversion_info:
                raise DistributionServiceError(conversion_info['error'])
            
            # Actualizar registro con información de tokens
            record.cop_to_token_exchange_rate = Decimal('1') / token_price_cop  # Tokens por COP
            record.equivalent_tokens_calculated = conversion_info['exact_tokens_calculated']
            record.tokens_to_transfer = conversion_info['whole_tokens_to_transfer']
            record.remaining_cop_amount = conversion_info['remaining_cop_amount']
            record.payment_status = InvestmentDistributionRecord.PaymentStatus.VERIFIED
            record.verification_date = timezone.now()
            record.verified_by = verified_by
            
            # Actualizar metadatos
            record.calculation_metadata.update({
                'token_conversion': {
                    'token_price_cop': str(token_price_cop),
                    'conversion_timestamp': timezone.now().isoformat(),
                    'verified_by': verified_by.email if verified_by else None,
                    'conversion_efficiency': str(conversion_info['conversion_efficiency_percentage'])
                }
            })
            
            record.save()
            
            # Crear log de auditoría
            if request and verified_by:
                AuditService.log_action(
                    request=request,
                    action_code="DISTRIBUTION_VERIFIED_FOR_TOKENS",
                    obj=record,
                    details={
                        'record_id': record.id,
                        'user_email': record.investment.application.user.email,
                        'cop_amount': str(record.net_distribution_amount_cop),
                        'tokens_to_transfer': record.tokens_to_transfer,
                        'remaining_cop': str(record.remaining_cop_amount),
                        'token_price_used': str(token_price_cop)
                    }
                )
            
            return {
                'success': True,
                'record_id': record.id,
                'user_email': record.investment.application.user.email,
                'conversion_summary': conversion_info,
                'verification_timestamp': record.verification_date.isoformat()
            }
            
        except InvestmentDistributionRecord.DoesNotExist:
            raise DistributionServiceError("Registro de distribución no encontrado")
        except Exception as e:
            raise DistributionServiceError(f"Error verificando conversión a tokens: {str(e)}")    