from rest_framework import serializers
from django.db import models, transaction
from django.core.validators import RegexValidator
from datetime import datetime
import pytz
import time

from apps.fund.models.core import Fund
from apps.fund.models.tokens import FundToken, TokenTransaction
from apps.fund.models.receipts import TransferReceipt
from apps.audit.audit_service import AuditService

from apps.kaleido.utils import (
    mint_721_token, burn_721_token, safe_transfer_721,
    safe_transfer_721_index_to_index as st721i,
    is_investor_valid,
    )
from apps.fund.utils import ( 
    get_next_available_token, 
    reserve_next_available_token
    )


class BaseTokenOperationSerializer(serializers.Serializer):
    fund_id = serializers.IntegerField(required=True, help_text="ID del fondo")
    
    def validate_fund_id(self, value):
        """Valida que el fondo exista y tenga un wallet asociado"""
        try:
            fund = Fund.objects.get(id=value)
            
            # Verificar que el fondo tenga un wallet asociado
            if not fund.hd_wallet:
                raise serializers.ValidationError("El fondo no tiene un wallet asociado")
                
            return value
        except Fund.DoesNotExist:
            raise serializers.ValidationError("No existe un fondo con este ID")
    
    def _get_fund(self, fund_id):
        """Obtiene el objeto Fund con el fund_id dado"""
        return Fund.objects.get(id=fund_id)
    
    def _validate_contract_address(self, fund, audit):
        """Verifica que el fondo tenga un contrato asociado"""
        if not fund.contract_address:
            if audit:
                self._update_audit(audit, 'ERROR', {'error': "El fondo no tiene una dirección de contrato"})
            raise serializers.ValidationError("El fondo no tiene una dirección de contrato")
    
    def _update_audit(self, audit, status, details, transaction_id=None):
        """Actualiza un registro de auditoría con los valores proporcionados"""
        audit.status = status
        audit.details.update(details)
        
        if transaction_id:
            audit.transaction_id = transaction_id
        
        # Especificar los campos a actualizar
        update_fields = ['status', 'details']
        if transaction_id:
            update_fields.append('transaction_id')
            
        audit.save(update_fields=update_fields)
    
    def _handle_exception(self, results, audit, token_id, exception):
        """Maneja excepciones genéricas durante las operaciones de tokens"""
        results['failures'] += 1
        results['success'] = False
        results['details'].append({
            'token_id': token_id if 'token_id' in locals() else None,
            'success': False,
            'error': str(exception)
        })
        
        if audit:
            self._update_audit(audit, 'ERROR', {'error': str(exception)})
    
    def _create_initial_audit(self, request, action_code, fund, operation):
        """Crea un registro de auditoría inicial para una operación de token"""
        if not request:
            return None
            
        return AuditService.log_action(
            request=request,
            action_code=action_code,
            obj=fund,
            details={
                'fund_id': fund.id,
                'operation': operation
            },
            status='PENDING'
        )
    
    def _execute_token_operation(self, validated_data):
        """Método plantilla que será implementado por las clases hijas"""
        raise NotImplementedError("Las subclases deben implementar este método")
    
    def create(self, validated_data):
        """Método genérico para ejecutar operaciones de tokens"""
        return self._execute_token_operation(validated_data)

class TokenMintSerializer(BaseTokenOperationSerializer):
    """Serializer para crear (mint) nuevos tokens"""
    nickname = serializers.CharField(
        required=True, 
        max_length=20,
        validators=[RegexValidator(r'^[a-zA-Z0-9_]+$', 'El nickname solo puede contener letras, números y guiones bajos')],
        help_text="Apodo del token (máximo 10 caracteres)"
    )
    
    def _generate_token_id(self, fund, initial_audit):
        """Genera un ID único para un nuevo token"""
        now = datetime.now()
        
        current_token_count = FundToken.objects.filter(fund=fund).count()
        next_token_count = current_token_count + 1
        
        date_part = now.strftime('%y%m%d%H%M')
        fund_id_part = f"{int(fund.id):03d}"   
        
        token_id = int(f"{next_token_count}{fund_id_part}{date_part}")
        
        if initial_audit:
            self._update_audit(initial_audit, 'PENDING', {'token_id': token_id})
        
        return token_id, next_token_count
    
    def _generate_nickname(self, nickname):
        """Genera un apodo único para el nuevo token"""
        fund = self._get_fund(self.validated_data.get('fund_id'))
        
        # Verificar si el fondo ya tiene un nickname_tokens asignado
        if fund.nickname_tokens:
            if nickname and fund.nickname_tokens != nickname:
                # Si se proporciona un nickname diferente al existente, advertir
                # pero mantener el original para consistencia
                # No lanzamos error, solo ignoramos el nuevo valor
                pass
            
            # Usar el nickname existente del fondo
            prefix = fund.nickname_tokens
        else:
            # Si el fondo no tiene nickname, usar el proporcionado
            if not nickname:
                raise serializers.ValidationError("Se requiere un nickname para el token")
            
            # Actualizar el fondo con el nuevo nickname
            fund.nickname_tokens = nickname
            fund.save(update_fields=['nickname_tokens'])
            prefix = nickname
        
        # Generar un nuevo apodo único con contador incremental
        entry_nickname = f"{prefix}_{fund.amount_tokens + 1}"
        
        # Verificar si el apodo ya existe (caso raro pero posible)
        if FundToken.objects.filter(nickname=entry_nickname).exists():
            # Si ya existe, intentar con un número diferente
            # Encontrar el mayor contador usado para este prefix
            max_counter = FundToken.objects.filter(
                nickname__startswith=f"{prefix}_"
            ).count() + 1
            
            entry_nickname = f"{prefix}_{max_counter}"
        
        return entry_nickname
    
    def _handle_mint_error(self, results, initial_audit, token_id, error):
        
        results['failures'] += 1
        results['success'] = False
        results['details'].append({
            'token_id': token_id,
            'success': False,
            'error': error
        })
        
        if initial_audit:
            self._update_audit(initial_audit, 'ERROR', {'error': str(error)})
    
    def _handle_mint_success(self, results, initial_audit, fund, next_token_count, token_id, result_data, user):
        fund.amount_tokens = next_token_count
        fund.save(update_fields=['amount_tokens'])
        
        generated_nickname = self._generate_nickname(self.validated_data.get('nickname'))    
        
        fund_token = FundToken.objects.create(
            fund=fund,
            token_id=token_id,
            nickname=generated_nickname,
            created_by=user,
            owner_user=user,
        )
        
        TokenTransaction.objects.create(
            fund=fund,
            token=fund_token,
            transaction_type=TokenTransaction.TransactionTypes.MINT,
            to_user=user,
            amount=1,
            kaleido_transaction_id=result_data.get('id', None),
            price_per_unit=0,
            description=f"Token {token_id} minted with nickname {generated_nickname}",
            metadata={
                'nickname': generated_nickname,
                'token_id': token_id,
                'mint_result': result_data
            }
        )
        
        results['minted'] += 1
        results['details'].append({
            'token_id': token_id,
            'nickname': generated_nickname,
            'success': True,
            'transaction_id': result_data.get('id'),
            'new_token_count': fund.amount_tokens
        })
        
        if initial_audit:
            audit_details = {
                'transaction_id': result_data.get('id'),
                'new_token_count': fund.amount_tokens
            }
            self._update_audit(initial_audit, 'SUCCESS', audit_details, 
                              transaction_id=result_data.get('id') if 'id' in result_data else None)
    
    def _execute_token_operation(self, validated_data):
        fund_id = validated_data.get('fund_id')
        fund = self._get_fund(fund_id)
        
        # Datos para auditoría
        request = self.context.get('request')
        user = request.user if request else None
        
        # Crear auditoría inicial
        initial_audit = self._create_initial_audit(request, 'TOKEN_CREATE', fund, 'mint_token')
        
        # Calcular cuántos tokens necesitamos crear (solo uno)
        tokens_to_mint = 1
        
        # Resultados para un solo token
        results = {
            'success': True,
            'total_to_mint': tokens_to_mint,
            'minted': 0,
            'failures': 0,
            'details': []
        }
        
        # Verificar si el fondo tiene un contrato de token
        self._validate_contract_address(fund, initial_audit)
        
        # Usar transacción atómica para el proceso de mint
        with transaction.atomic():
            fund = Fund.objects.select_for_update().get(id=fund_id)
            
            try:
                # Generar ID para el nuevo token
                token_id, next_token_count = self._generate_token_id(fund, initial_audit)
                
                result_data, error = mint_721_token(token_id, fund.id, fund.contract_address)
                
                if not error:
                    self._handle_mint_success(results, initial_audit, fund, next_token_count, token_id, result_data, user)
                else:
                    self._handle_mint_error(results, initial_audit, token_id, error)
                    
            except Exception as e:
                self._handle_exception(results, initial_audit, token_id if 'token_id' in locals() else None, e)
        
        return results

class TokenMintBatchSerializer(BaseTokenOperationSerializer):
    """Serializer para crear (mint) tokens masivamente en lotes"""
    nickname = serializers.CharField(
        required=True, 
        max_length=20,
        validators=[RegexValidator(r'^[a-zA-Z0-9_]+$', 'El nickname solo puede contener letras, números y guiones bajos')],
        help_text="Apodo base para los tokens"
    )
    quantity = serializers.IntegerField(
        required=True,
        min_value=1,
        max_value=2000,  # Límite máximo por operación
        help_text="Cantidad total de tokens a crear"
    )
    batch_size = serializers.IntegerField(
        default=40,
        min_value=1,
        max_value=50,
        help_text="Tamaño del lote (máximo 50 tokens por lote)"
    )
    
    def validate(self, data):
        """Validaciones adicionales"""
        if data['quantity'] > 1000:
            raise serializers.ValidationError("No se pueden crear más de 1000 tokens en una sola operación")
        return data
    
    def _generate_batch_token_ids(self, fund, quantity, initial_audit):
        """Genera múltiples IDs únicos para un lote de tokens - VERSIÓN FIJA"""
        # SOLUCION: Generar timestamp una sola vez y reutilizarlo
        now = datetime.now()
        date_part = now.strftime('%y%m%d')
        fund_id_part = f"{int(fund.id):03d}"
        
        # Usar transacción atómica para obtener el contador actual y bloquearlo
        with transaction.atomic():
            # Bloquear el fondo para evitar condiciones de carrera
            fund = Fund.objects.select_for_update().get(id=fund.id)
            current_token_count = FundToken.objects.filter(fund=fund).count()
            
            token_ids = []
            for i in range(quantity):
                next_token_count = current_token_count + i + 1
                # CLAVE: Usar el mismo timestamp para todos los tokens del lote
                token_id = int(f"{next_token_count}{fund_id_part}{date_part}")
                token_ids.append((token_id, next_token_count))
        
        if initial_audit:
            self._update_audit(initial_audit, 'PENDING', {
                'batch_size': quantity,
                'first_token_id': token_ids[0][0] if token_ids else None,
                'last_token_id': token_ids[-1][0] if token_ids else None,
                'timestamp_used': date_part,  # Agregar para debugging
                'generation_time': now.isoformat()
            })
            
            return token_ids
    
    def _generate_batch_nicknames(self, nickname, quantity):
        """Genera múltiples apodos únicos y secuenciales para un lote de tokens"""
        fund = self._get_fund(self.validated_data.get('fund_id'))

        # Usar el nickname base del fondo
        if fund.nickname_tokens:
            prefix = fund.nickname_tokens
        else:
            fund.nickname_tokens = nickname
            fund.save(update_fields=['nickname_tokens'])
            prefix = nickname

        nicknames = []
        base_count = fund.amount_tokens + 1
        current_index = base_count

        # Obtener todos los nicknames existentes para este fondo y prefix
        existing_nicknames = set(
            FundToken.objects.filter(
                fund=fund,
                nickname__startswith=f"{prefix}_"
            ).values_list('nickname', flat=True)
        )

        tokens_needed = quantity
        while len(nicknames) < tokens_needed:
            candidate = f"{prefix}_{current_index}"
            if candidate not in existing_nicknames:
                nicknames.append(candidate)
            current_index += 1

        return nicknames
    
    def _process_batch(self, fund, token_batch, nickname_batch, user, results, initial_audit):
        """Procesa un lote de tokens"""
        batch_results = []
        
        for (token_id, next_token_count), nickname in zip(token_batch, nickname_batch):
            try:
                # Crear token en Kaleido
                result_data, error = mint_721_token(token_id, fund.id, fund.contract_address)
                
                price_per_unit = Fund.objects.get(id=fund.id).price_per_unit
                
                if not error:
                    # Crear token en Django
                    fund_token = FundToken.objects.create(
                        fund=fund,
                        token_id=token_id,
                        nickname=nickname,
                        created_by=user,
                        owner_user=user,
                    )
                    
                    # Crear transacción de tracking
                    TokenTransaction.objects.create(
                        fund=fund,
                        token=fund_token,
                        transaction_type=TokenTransaction.TransactionTypes.MINT,
                        to_user=user,
                        amount=1,
                        kaleido_transaction_id=result_data.get('id', None),
                        price_per_unit=price_per_unit,
                        description=f"Token {token_id} minted with nickname {nickname} (batch operation)",
                        metadata={
                            'nickname': nickname,
                            'token_id': token_id,
                            'mint_result': result_data,
                            'batch_operation': True
                        }
                    )
                    
                    batch_results.append({
                        'token_id': token_id,
                        'nickname': nickname,
                        'success': True,
                        'transaction_id': result_data.get('id'),
                        'next_token_count': next_token_count
                    })
                    
                    results['minted'] += 1
                    
                else:
                    batch_results.append({
                        'token_id': token_id,
                        'nickname': nickname,
                        'success': False,
                        'error': str(error)
                    })
                    
                    results['failures'] += 1
                    
            except Exception as e:
                batch_results.append({
                    'token_id': token_id,
                    'nickname': nickname,
                    'success': False,
                    'error': str(e)
                })
                
                results['failures'] += 1
        
        return batch_results
    
    def _execute_token_operation(self, validated_data):
        """Implementación específica para mint masivo en lotes"""
        fund_id = validated_data.get('fund_id')
        quantity = validated_data.get('quantity')
        batch_size = validated_data.get('batch_size', 40)
        nickname = validated_data.get('nickname')
        
        fund = self._get_fund(fund_id)
        
        # Datos para auditoría
        request = self.context.get('request')
        user = request.user if request else None
        
        # Crear auditoría inicial
        initial_audit = self._create_initial_audit(
            request, 
            'TOKEN_BATCH_CREATE', 
            fund, 
            'mint_tokens_batch'
        )
        
        # Resultados generales
        results = {
            'success': True,
            'total_requested': quantity,
            'total_batches': 0,
            'minted': 0,
            'failures': 0,
            'batch_details': [],
            'summary': {
                'completed_batches': 0,
                'failed_batches': 0,
                'total_processing_time': 0
            }
        }
        
        # Verificar si el fondo tiene un contrato de token
        self._validate_contract_address(fund, initial_audit)
        
        start_time = time.time()
        
        try:
            # Generar todos los token_ids y nicknames
            token_ids_with_counts = self._generate_batch_token_ids(fund, quantity, initial_audit)
            nicknames = self._generate_batch_nicknames(nickname, quantity)
            
            # Dividir en lotes
            total_batches = (quantity + batch_size - 1) // batch_size  # Ceiling division
            results['total_batches'] = total_batches
            
            # Procesar lote por lote
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, quantity)
                
                # Obtener datos del lote actual
                token_batch = token_ids_with_counts[start_idx:end_idx]
                nickname_batch = nicknames[start_idx:end_idx]
                
                print(f"Procesando lote {batch_num + 1}/{total_batches} - Tokens {start_idx + 1} a {end_idx}")
                
                # Usar transacción atómica para cada lote
                with transaction.atomic():
                    fund = Fund.objects.select_for_update().get(id=fund_id)
                    
                    batch_start_time = time.time()
                    
                    # Procesar el lote
                    batch_results = self._process_batch(
                        fund, token_batch, nickname_batch, user, results, initial_audit
                    )
                    
                    # Actualizar contador de tokens del fondo
                    successful_tokens = sum(1 for r in batch_results if r['success'])
                    if successful_tokens > 0:
                        fund.amount_tokens += successful_tokens
                        fund.save(update_fields=['amount_tokens'])
                    
                    batch_processing_time = time.time() - batch_start_time
                    
                    # Registrar resultados del lote
                    batch_summary = {
                        'batch_number': batch_num + 1,
                        'tokens_in_batch': len(token_batch),
                        'successful': successful_tokens,
                        'failed': len(token_batch) - successful_tokens,
                        'processing_time': round(batch_processing_time, 2),
                        'details': batch_results
                    }
                    
                    results['batch_details'].append(batch_summary)
                    
                    if successful_tokens == len(token_batch):
                        results['summary']['completed_batches'] += 1
                        print(f"✅ Lote {batch_num + 1} completado exitosamente")
                    else:
                        results['summary']['failed_batches'] += 1
                        print(f"❌ Lote {batch_num + 1} completado con errores")
                
                # Pequeña pausa entre lotes para evitar saturar el sistema
                time.sleep(0.1)
            
            # Calcular tiempo total
            total_processing_time = time.time() - start_time
            results['summary']['total_processing_time'] = round(total_processing_time, 2)
            
            # Determinar si la operación fue exitosa
            if results['failures'] == 0:
                results['success'] = True
                status = 'SUCCESS'
            elif results['minted'] > 0:
                results['success'] = False  # Parcialmente exitoso
                status = 'PARTIAL_SUCCESS'
            else:
                results['success'] = False
                status = 'ERROR'
            
            # Actualizar auditoría final
            if initial_audit:
                self._update_audit(initial_audit, status, {
                    'total_requested': quantity,
                    'total_minted': results['minted'],
                    'total_failed': results['failures'],
                    'total_batches': total_batches,
                    'completed_batches': results['summary']['completed_batches'],
                    'processing_time': results['summary']['total_processing_time']
                })
            
            print(f"Operación completada: {results['minted']}/{quantity} tokens creados en {total_processing_time:.2f}s")
            
        except Exception as e:
            results['success'] = False
            results['error'] = str(e)
            
            if initial_audit:
                self._update_audit(initial_audit, 'ERROR', {'error': str(e)})
            
            print(f"Error en operación masiva: {str(e)}")
        
        return results

def get_batch_creation_progress(fund_id, start_time=None):
    """
    Obtiene el progreso de creación de tokens para un fondo
    
    Args:
        fund_id (int): ID del fondo
        start_time (datetime): Tiempo de inicio para filtrar
    
    Returns:
        dict: Información del progreso con timestamps en zona horaria de Colombia
    """
    # NUEVO: Configurar zona horaria de Colombia explícitamente
    bogota_tz = pytz.timezone('America/Bogota')
    
    queryset = TokenTransaction.objects.filter(
        fund_id=fund_id,
        transaction_type=TokenTransaction.TransactionTypes.MINT
    )
    
    if start_time:
        queryset = queryset.filter(created_at__gte=start_time)
    
    total_created = queryset.count()
    
    # Agrupar por lotes (usando metadata)
    batch_transactions = queryset.filter(
        metadata__has_key='batch_operation'
    ).values('created_at').annotate(
        batch_count=models.Count('id')
    ).order_by('created_at')
    
    # NUEVO: Convertir explícitamente la fecha a zona horaria de Colombia
    latest_batch_time = None
    if batch_transactions:
        latest_utc = batch_transactions.last()['created_at']
        # Convertir de UTC a Bogotá
        latest_batch_time = latest_utc.astimezone(bogota_tz).isoformat()
    
    return {
        'total_tokens_created': total_created,
        'batch_operations': len(batch_transactions),
        'latest_batch_time': latest_batch_time,  # Ahora en zona horaria de Colombia
        'average_batch_size': sum(b['batch_count'] for b in batch_transactions) / len(batch_transactions) if batch_transactions else 0
    }
      
class TokenBurnSerializer(BaseTokenOperationSerializer):
    """Serializer para quemar tokens existentes"""
    token_id = serializers.IntegerField(required=True, help_text="ID del token a quemar")

    def _handle_burn_error(self, results, init_audit, token_id, error):
        """Maneja los errores durante el proceso de burn."""
        results['failures'] += 1
        results['success'] = False
        results['details'].append({
            'token_id': token_id,
            'success': False,
            'error': error
        })
        
        if init_audit:
            self._update_audit(init_audit, 'ERROR', {'error': str(error)})
    
    def _handle_burn_success(self, results, init_audit, fund, token_id, result_data, user):
        """Maneja el éxito durante el proceso de burn."""
        try:
            fund_token = FundToken.objects.get(fund=fund, token_id=token_id)
            original_nickname = fund_token.nickname
            
            TokenTransaction.objects.create(
                fund=fund,
                token=fund_token,
                transaction_type=TokenTransaction.TransactionTypes.BURN,
                from_user=user,
                amount=1,
                kaleido_transaction_id=result_data.get('id'),
                description=f'Token {token_id} ({original_nickname}) quemado por {user.email}',
                metadata={
                    'original_nickname': original_nickname,
                    'burn_result': result_data,
                    'token_id': token_id
                }
            )
            
            fund_token.status = False
            fund_token.owner_user = None  # Opcional: quitar propietario
            fund_token.save(update_fields=['status', 'owner_user'])
            
            active_tokens_count = FundToken.objects.filter(fund=fund, status=True).count()
            fund.amount_tokens = active_tokens_count
            fund.save(update_fields=['amount_tokens'])
            
            burned = True
            
        except FundToken.DoesNotExist:
            burned = False
        
        results['burned'] += 1
        results['details'].append({
            'token_id': token_id,
            'success': True,
            'transaction_id': result_data.get('id')
        })
        
        if init_audit:
            audit_details = {
                'transaction_id': result_data.get('id')
            }
            self._update_audit(init_audit, 'SUCCESS', audit_details, 
                              transaction_id=result_data.get('id') if 'id' in result_data else None)
    
    def _execute_token_operation(self, validated_data):
        """Implementación específica para quemar tokens"""
        fund_id = validated_data.get('fund_id')
        token_id = validated_data.get('token_id')
        
        fund = self._get_fund(fund_id)
        
        # Datos para auditoría
        request = self.context.get('request')
        user = request.user if request else None
        
        # Crear auditoría inicial
        init_audit = self._create_initial_audit(request, 'TOKEN_BURN', fund, 'burn_token')
        
        # Resultados para un solo token
        results = {
            'success': True,
            'total_to_burn': 1,
            'burned': 0,
            'failures': 0,
            'details': []
        }
        
        # Verificar si el fondo tiene un contrato de token
        self._validate_contract_address(fund, init_audit)
        
        # Usar transacción atómica
        with transaction.atomic():
            fund = Fund.objects.select_for_update().get(id=fund_id)
            
            try:
                # Ejecutar burn
                result_data, error = burn_721_token(token_id, fund.id, fund.contract_address)
                
                if not error:
                    self._handle_burn_success(results, init_audit, fund, token_id, result_data, user)
                else:
                    self._handle_burn_error(results, init_audit, token_id, error)
                    
            except Exception as e:
                self._handle_exception(results, init_audit, token_id, e)
            
            return results    

class TokenBurnBatchSerializer(BaseTokenOperationSerializer):
    """Serializer para quemar tokens masivamente en lotes"""
    quantity = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=1000,
        help_text="Cantidad total de tokens a quemar"
    )
    batch_size = serializers.IntegerField(
        default=40,
        min_value=1,
        max_value=50,
        help_text="Tamaño del lote (máximo 50 tokens por lote)"
    )
    burn_criteria = serializers.CharField(
        default='oldest',
        help_text="Criterio para seleccionar tokens: 'oldest', 'newest', 'random'"
    )
    burn_all = serializers.BooleanField(
        default=False,
        help_text="Si se activa, quemará todos los tokens activos del fondo sin necesidad de especificar 'quantity'"
        )
    
    def validate(self, data):
        """Validaciones adicionales"""
        burn_all = data.get('burn_all', False)
        quantity = data.get('quantity')
        burn_criteria = data.get('burn_criteria', 'oldest')
        
        # Validar que se proporcione quantity O burn_all
        if not burn_all and not quantity:
            raise serializers.ValidationError("Debe especificar 'quantity' o activar 'burn_all'")
        
        # Si burn_all está activado, quantity es opcional
        if burn_all:
            if quantity:
                raise serializers.ValidationError("No puede especificar 'quantity' cuando 'burn_all' está activado")
            # Forzar burn_criteria a 'all' cuando burn_all=True
            data['burn_criteria'] = 'all'
        else:
            # Validaciones normales cuando no es burn_all
            if quantity > 1000:
                raise serializers.ValidationError("No se pueden quemar más de 1000 tokens en una sola operación")
        
        # Validar criterios
        valid_criteria = ['oldest', 'newest', 'random', 'all']
        if burn_criteria not in valid_criteria:
            raise serializers.ValidationError(f"burn_criteria debe ser uno de: {', '.join(valid_criteria)}")
        
        return data
    
    def _get_batch_tokens_to_burn(self, fund, quantity, burn_criteria, initial_audit):
        """Obtiene múltiples tokens disponibles para quemar en lote"""
        try:
            # Obtener tokens activos para quemar según el criterio
            base_queryset = FundToken.objects.filter(
                fund=fund,
                status=True  # Solo tokens activos
            )
            
            # Si es 'all', obtener todos los tokens sin límite
            if burn_criteria == 'all':
                available_tokens = base_queryset.order_by('created_at', 'token_id')
                total_tokens = available_tokens.count()
                
                if total_tokens == 0:
                    raise serializers.ValidationError("No hay tokens activos para quemar en este fondo")
                
                # Actualizar quantity con el total de tokens encontrados
                quantity = total_tokens
                
            else:
                # Lógica original para criterios específicos
                if burn_criteria == 'oldest':
                    available_tokens = base_queryset.order_by('created_at', 'token_id')
                elif burn_criteria == 'newest':
                    available_tokens = base_queryset.order_by('-created_at', '-token_id')
                else:  # random
                    available_tokens = base_queryset.order_by('?')
                
                available_tokens = available_tokens[:quantity]
                
                if len(available_tokens) < quantity:
                    available_count = len(available_tokens)
                    raise serializers.ValidationError(
                        f"Solo hay {available_count} tokens activos para quemar, pero se solicitaron {quantity}"
                    )
            
            token_ids = [token.token_id for token in available_tokens]
            
            if initial_audit:
                self._update_audit(initial_audit, 'PENDING', {
                    'batch_size': quantity,
                    'burn_criteria': burn_criteria,
                    'burn_all_tokens': burn_criteria == 'all',
                    'total_tokens_in_fund': base_queryset.count(),
                    'tokens_to_burn': len(token_ids),
                    'first_token_id': token_ids[0] if token_ids else None,
                    'last_token_id': token_ids[-1] if token_ids else None,
                })
            
            return token_ids
            
        except Exception as e:
            raise serializers.ValidationError(f"Error obteniendo tokens para quemar: {str(e)}")
    
    def _process_burn_batch(self, fund, token_batch, user, results, initial_audit):
        """Procesa un lote de quemas de tokens"""
        batch_results = []
        
        for token_id in token_batch:
            try:
                # Ejecutar quema individual
                result_data, error = burn_721_token(token_id, fund.id, fund.contract_address)

                if not error:
                    # Actualizar estado en la base de datos
                    try:
                        fund_token = FundToken.objects.get(fund=fund, token_id=token_id)
                        original_nickname = fund_token.nickname
                        
                        # Crear transacción de quema
                        TokenTransaction.objects.create(
                            fund=fund,
                            token=fund_token,
                            transaction_type=TokenTransaction.TransactionTypes.BURN,
                            from_user=user,
                            amount=1,
                            kaleido_transaction_id=result_data.get('id'),
                            description=f'Token {token_id} ({original_nickname}) quemado por {user.email}',
                            metadata={
                                'original_nickname': original_nickname,
                                'burn_result': result_data,
                                'token_id': token_id,
                                'batch_operation': True
                            }
                        )
                        
                        # Desactivar token
                        fund_token.status = False
                        fund_token.owner_user = None
                        fund_token.save(update_fields=['status', 'owner_user'])
                        
                        results['burned'] += 1
                        batch_results.append({
                            'token_id': token_id,
                            'success': True,
                            'transaction_id': result_data.get('id'),
                            'original_nickname': original_nickname
                        })
                        
                    except FundToken.DoesNotExist:
                        results['failures'] += 1
                        batch_results.append({
                            'token_id': token_id,
                            'success': False,
                            'error': f'Token {token_id} no encontrado en base de datos'
                        })
                else:
                    results['failures'] += 1
                    batch_results.append({
                        'token_id': token_id,
                        'success': False,
                        'error': error
                    })
                    
            except Exception as e:
                results['failures'] += 1
                batch_results.append({
                    'token_id': token_id,
                    'success': False,
                    'error': str(e)
                })
        
        return batch_results
    
    def _analyze_burn_errors(self, batch_details):
        """Analiza los errores para generar un resumen comprehensivo"""
        error_analysis = {
            'total_errors': 0,
            'error_types': {},
            'failed_tokens': []
        }
        
        for batch in batch_details:
            for token_result in batch.get('results', []):
                if not token_result.get('success', False):
                    error_analysis['total_errors'] += 1
                    error_type = token_result.get('error', 'Unknown error')
                    
                    if error_type not in error_analysis['error_types']:
                        error_analysis['error_types'][error_type] = 0
                    error_analysis['error_types'][error_type] += 1
                    
                    error_analysis['failed_tokens'].append({
                        'token_id': token_result.get('token_id'),
                        'error': error_type
                    })
        
        return error_analysis
    
    def _execute_token_operation(self, validated_data):
        """Implementación específica para quema masiva en lotes"""
        fund_id = validated_data.get('fund_id')
        quantity = validated_data.get('quantity')
        batch_size = validated_data.get('batch_size', 40)
        burn_criteria = validated_data.get('burn_criteria', 'oldest')
        burn_all = validated_data.get('burn_all', False)
        
        fund = self._get_fund(fund_id)
        
        # Datos para auditoría
        request = self.context.get('request')
        user = request.user if request else None
        
        # Crear auditoría inicial
        action_code = 'TOKEN_BATCH_BURN_ALL' if burn_all else 'TOKEN_BATCH_BURN'
        operation_type = 'burn_all_tokens' if burn_all else 'burn_tokens_batch'
        
        initial_audit = self._create_initial_audit(
            request, 
            action_code, 
            fund, 
            operation_type
        )
        
        # Resultados generales
        results = {
            'success': True,
            'burn_all_requested': burn_all,
            'total_requested': quantity,
            'total_batches': 0,
            'burned': 0,
            'failures': 0,
            'batch_details': [],
            'summary': {
                'completed_batches': 0,
                'failed_batches': 0,
                'total_processing_time': 0,
                'operation_type': 'BURN_ALL' if burn_all else 'BURN_PARTIAL'
            }
        }
        
        # Verificar si el fondo tiene un contrato de token
        self._validate_contract_address(fund, initial_audit)
        
        start_time = time.time()
        
        try:
            # Obtener todos los token_ids disponibles para quemar
            available_token_ids = self._get_batch_tokens_to_burn(
                fund, quantity, burn_criteria, initial_audit
            )
            
            # Actualizar quantity si era burn_all
            actual_quantity = len(available_token_ids)
            results['total_requested'] = actual_quantity
            
            # Dividir en lotes
            total_batches = (actual_quantity + batch_size - 1) // batch_size
            results['total_batches'] = total_batches
            
            # Mensaje especial para burn_all
            if burn_all:
                results['message'] = f"Iniciando quema de TODOS los tokens del fondo ({actual_quantity} tokens)"
            
            # Procesar lote por lote
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, actual_quantity)
                
                token_batch = available_token_ids[start_idx:end_idx]
                
                batch_start_time = time.time()
                
                # Procesar este lote
                batch_results = self._process_burn_batch(
                    fund, token_batch, user, results, initial_audit
                )
                
                batch_end_time = time.time()
                batch_processing_time = batch_end_time - batch_start_time
                
                # Registrar detalles del lote
                batch_detail = {
                    'batch_number': batch_num + 1,
                    'tokens_in_batch': len(token_batch),
                    'successful_burns': len([r for r in batch_results if r.get('success', False)]),
                    'failed_burns': len([r for r in batch_results if not r.get('success', False)]),
                    'processing_time': batch_processing_time,
                    'results': batch_results
                }
                
                results['batch_details'].append(batch_detail)
                
                # Actualizar contadores de lotes
                if batch_detail['failed_burns'] == 0:
                    results['summary']['completed_batches'] += 1
                else:
                    results['summary']['failed_batches'] += 1
            
            # Actualizar contador de tokens activos del fondo
            with transaction.atomic():
                fund_updated = Fund.objects.select_for_update().get(id=fund_id)
                active_tokens_count = FundToken.objects.filter(fund=fund_updated, status=True).count()
                fund_updated.amount_tokens = active_tokens_count
                fund_updated.save(update_fields=['amount_tokens'])
            
            # Calcular tiempo total y determinar estado final
            end_time = time.time()
            results['summary']['total_processing_time'] = end_time - start_time
            
            # Análisis de errores
            if results['failures'] > 0:
                results['error_analysis'] = self._analyze_burn_errors(results['batch_details'])
            
            # Determinar estado final
            if results['burned'] == actual_quantity:
                results['success'] = True
                if burn_all:
                    results['message'] = f"Se han quemado TODOS los tokens del fondo exitosamente ({results['burned']} tokens)"
                else:
                    results['message'] = f"Se han quemado {results['burned']} tokens exitosamente"
            elif results['burned'] > 0:
                results['success'] = 'partial'
                results['message'] = f"Se han quemado {results['burned']} tokens con {results['failures']} errores"
            else:
                results['success'] = False
                results['message'] = f"Error al quemar tokens: {results['failures']} fallidos"
            
            # Actualizar auditoría final
            if initial_audit:
                final_status = 'SUCCESS' if results['success'] is True else 'PARTIAL' if results['success'] == 'partial' else 'ERROR'
                self._update_audit(initial_audit, final_status, {
                    'total_burned': results['burned'],
                    'total_failed': results['failures'],
                    'processing_time': results['summary']['total_processing_time'],
                    'completed_batches': results['summary']['completed_batches'],
                    'burn_all_operation': burn_all,
                    'final_tokens_remaining': FundToken.objects.filter(fund=fund, status=True).count()
                })
            
            return results
            
        except Exception as e:
            # Manejo de errores generales
            if initial_audit:
                self._update_audit(initial_audit, 'ERROR', {'error': str(e)})
            
            results['success'] = False
            results['message'] = f"Error durante la quema masiva: {str(e)}"
            return results
          
class PurchaseTokenSerializer(BaseTokenOperationSerializer):
    """Serializer para comprar tokens existentes"""
    #token_id = serializers.IntegerField(required=True, help_text="ID del token a comprar")

    def _get_next_available_token(self, fund):
        """Obtiene el proximo token disponible automaticamente"""
        try:
            token = get_next_available_token(fund.id)
            return token.token_id
        except ValueError as e:
            raise serializers.ValidationError(f"No hay tokens disponibles para comprar: {str(e)}")

    def _reserve_token_for_user(self, fund, user):
        """Reserva el proximo token disponible para el usuario"""
        try:
            token = reserve_next_available_token(fund.id, user)
            return token
        except ValueError as e:
            raise serializers.ValidationError(f"No se pudo reservar token: {str(e)}")

    def _handle_purchase_error(self, results, init_audit, token_id, error):
        """Maneja los errores durante el proceso de compra."""
        results['failures'] += 1
        results['success'] = False
        results['details'].append({
            'token_id': token_id,
            'success': False,
            'error': error
        })
        
        if init_audit:
            self._update_audit(init_audit, 'ERROR', {'error': str(error)})
    
    def _handle_purchase_success(self, results, init_audit, fund, token_id, result_data, user):
        """Maneja el éxito durante el proceso de compra."""
        fund_token = FundToken.objects.get(fund=fund, token_id=token_id)
        previous_owner = fund_token.owner_user
        
        # Actualizar ownership en la base de datos
        FundToken.objects.filter(
            fund=fund,
            token_id=token_id
        ).update(owner_user=user)
        
        TokenTransaction.objects.create(
            fund=fund,
            token=fund_token,
            transaction_type=TokenTransaction.TransactionTypes.PURCHASE,
            from_user=previous_owner,
            amount=1,
            price_per_unit=fund.price_per_unit,
            to_user=user,
            kaleido_transaction_id=result_data.get('id'),
            description=f'Token {token_id} comprado por {user.email}',
            metadata={
                'previous_owner': previous_owner.email if previous_owner else 'Fund',
                'purchase_result': result_data
            }
        )
        
        results['bought'] += 1
        results['success'] = True
        results['details'].append({
            'token_id': token_id,
            'success': True,
            'transaction_id': result_data.get('id')
        })
        
        TransferReceipt.objects.create(
            fund=fund,
            user=user,
            transaction_id=result_data.get('id'),
            description='Transferencia exitosa, token #{} desde fondo: {}'.format(
                token_id, 
                fund.name
                )
            )        
        
        if init_audit:
            audit_details = {
                'transaction_id': result_data.get('id')
            }
            self._update_audit(init_audit, 'SUCCESS', audit_details, 
                              transaction_id=result_data.get('id') if 'id' in result_data else None)
            
    def _execute_token_operation(self, validated_data):
        """Implementación específica para comprar tokens"""
        #token_id = validated_data.get('token_id')
        fund_id = validated_data.get('fund_id')
        fund = self._get_fund(fund_id)
        
        # Datos para auditoría
        request = self.context.get('request')
        user = request.user if request else None
        
        if user:
            application, error = is_investor_valid(user, fund)
            if not application:
                raise serializers.ValidationError("El usuario no es un inversionista válido para este fondo")
        
        # Crear auditoría inicial
        init_audit = self._create_initial_audit(request, 'TOKEN_TRANSFER', fund, 'purchase_token')
        
        # Resultados para un solo token
        results = {
            'success': True,
            'total_to_buy': 1,
            'bought': 0,
            'failures': 0,
            'details': []
        }
        
        # Verificar si el fondo tiene un contrato de token
        self._validate_contract_address(fund, init_audit)
        
        token_id = None
        
        # Usar transacción atómica
        with transaction.atomic():
            fund = Fund.objects.select_for_update().get(id=fund_id)
            
            try:
                token_id = self._get_next_available_token(fund)
                # Ejecutar purchase
                result_data, error = safe_transfer_721(token_id, fund.id, fund.contract_address, user)
                
                if not error:
                    self._handle_purchase_success(results, init_audit, fund, token_id, result_data, user)
                else:
                    self._handle_purchase_error(results, init_audit, token_id, error)
                    
            except Exception as e:
                #tokend_id_for_error = tokend_id if 'token_id' in locals() else None
                self._handle_exception(results, init_audit, token_id, e)
            
            return results 

class PurchaseTokenBatchSerializer(BaseTokenOperationSerializer):
    """Serializer para comprar tokens masivamente en lotes"""
    quantity = serializers.IntegerField(
        required=True,
        min_value=1,
        max_value=1000,
        help_text="Cantidad total de tokens a comprar"
    )
    batch_size = serializers.IntegerField(
        default=40,
        min_value=1,
        max_value=50,
        help_text="Tamaño del lote (máximo 50 tokens por lote)"
    )
    
    def validate(self, data):
        """Validaciones adicionales"""
        if data['quantity'] > 1000:
            raise serializers.ValidationError("No se pueden comprar más de 1000 tokens en una sola operación")
        return data
    
    def _get_batch_available_tokens(self, fund, quantity, initial_audit):
        """Obtiene múltiples tokens disponibles para compra en lote"""
        try:
            # Obtener tokens disponibles para compra ordenados por token_id
            available_tokens = FundToken.objects.filter(
                fund=fund,
                status=True,
                owner_user=24
            ).order_by('created_at', 'token_id')[:quantity]
            
            if len(available_tokens) < quantity:
                available_count = len(available_tokens)
                raise serializers.ValidationError(
                    f"Solo hay {available_count} tokens disponibles para comprar, pero se solicitaron {quantity}"
                )
            
            token_ids = [token.token_id for token in available_tokens]
            
            if initial_audit:
                self._update_audit(initial_audit, 'PENDING', {
                    'batch_size': quantity,
                    'first_token_id': token_ids[0] if token_ids else None,
                    'last_token_id': token_ids[-1] if token_ids else None,
                    'available_tokens': len(available_tokens)
                })
            
            return token_ids
            
        except Exception as e:
            raise serializers.ValidationError(f"Error obteniendo tokens disponibles: {str(e)}")
        
    @staticmethod
    def _obtain_address_wallet(user, fund):
        from apps.kaleido.utils import get_wallet_index
        
        wallet_data, wallet_error = get_wallet_index(user, fund.id)
        if wallet_error:
            # Si hay error, devolver None y el error
            return None, wallet_error
        
        user_wallet_address = wallet_data.get('address')
        
        return user_wallet_address, None
    
    def _process_purchase_batch(self, fund, token_batch, user, results):
        """Procesa un lote de compras de tokens"""
        batch_results = []
        
        address_wallet, wallet_error = PurchaseTokenBatchSerializer._obtain_address_wallet(user, fund)
        
        if wallet_error:
            # Si no se puede obtener la wallet, fallar todo el lote
            for token_id in token_batch:
                batch_results.append({
                    'token_id': token_id,
                    'success': False,
                    'error': f'Error obteniendo wallet del usuario: {wallet_error}'
                })
                results['failures'] += 1
            return batch_results        
        
        for token_id in token_batch:
            try:
                # Ejecutar compra individual
                result_data, error = safe_transfer_721(token_id, fund.id, fund.contract_address, user, address_wallet)
                
                if not error:
                    # Actualizar ownership en la base de datos
                    fund_token = FundToken.objects.get(fund=fund, token_id=token_id)
                    previous_owner = fund_token.owner_user
                    
                    FundToken.objects.filter(
                        fund=fund,
                        token_id=token_id
                    ).update(owner_user=user)
                    
                    # Crear transacción de tracking
                    TokenTransaction.objects.create(
                        fund=fund,
                        token=fund_token,
                        transaction_type=TokenTransaction.TransactionTypes.PURCHASE,
                        from_user=previous_owner,
                        amount=1,
                        price_per_unit=fund.price_per_unit,
                        to_user=user,
                        kaleido_transaction_id=result_data.get('id'),
                        description=f'Token {token_id} comprado por {user.email} (batch operation)',
                        metadata={
                            'previous_owner': previous_owner.email if previous_owner else 'Fund',
                            'purchase_result': result_data,
                            'batch_operation': True
                        }
                    )
                    
                    # Crear recibo de transferencia
                    TransferReceipt.objects.create(
                        fund=fund,
                        user=user,
                        transaction_id=result_data.get('id'),
                        description='Transferencia exitosa (lote), token #{} desde fondo: {}'.format(
                            token_id, 
                            fund.name
                        )
                    )
                    
                    batch_results.append({
                        'token_id': token_id,
                        'success': True,
                        'transaction_id': result_data.get('id'),
                        'previous_owner': previous_owner.email if previous_owner else 'Fund'
                    })
                    
                    results['bought'] += 1
                    
                else:
                    batch_results.append({
                        'token_id': token_id,
                        'success': False,
                        'error': str(error)
                    })
                    
                    results['failures'] += 1
                    
            except Exception as e:
                batch_results.append({
                    'token_id': token_id,
                    'success': False,
                    'error': str(e)
                })
                
                results['failures'] += 1
        
        return batch_results
    
    def _analyze_errors(self, batch_details):
        """Analiza los errores para generar un resumen comprehensivo"""
        error_summary = {
            'total_errors': 0,
            'error_types': {},
            'common_errors': [],
            'sample_errors': []
        }
        
        all_errors = []
        
        for batch in batch_details:
            for detail in batch.get('details', []):
                if not detail.get('success', True):
                    error_msg = detail.get('error', 'Error desconocido')
                    error_type = detail.get('error_type', 'unknown')
                    
                    all_errors.append({
                        'token_id': detail.get('token_id'),
                        'error': error_msg,
                        'error_type': error_type,
                        'batch_number': batch.get('batch_number')
                    })
                    
                    error_summary['total_errors'] += 1
                    
                    # Contar tipos de errores
                    if error_type not in error_summary['error_types']:
                        error_summary['error_types'][error_type] = 0
                    error_summary['error_types'][error_type] += 1
        
        # Encontrar errores más comunes
        if all_errors:
            from collections import Counter
            error_messages = [err['error'] for err in all_errors]
            common_errors = Counter(error_messages).most_common(3)
            
            error_summary['common_errors'] = [
                {
                    'error_message': error,
                    'count': count,
                    'percentage': round((count / len(all_errors)) * 100, 2)
                }
                for error, count in common_errors
            ]
            
            # Tomar una muestra de errores únicos
            unique_errors = list({err['error']: err for err in all_errors}.values())[:5]
            error_summary['sample_errors'] = unique_errors
        
        return error_summary    
    
    def _execute_token_operation(self, validated_data):
        """Implementación específica para compra masiva en lotes"""
        fund_id = validated_data.get('fund_id')
        quantity = validated_data.get('quantity')
        batch_size = validated_data.get('batch_size', 40)
        
        fund = self._get_fund(fund_id)
        
        # Datos para auditoría
        request = self.context.get('request')
        user = request.user if request else None
        
        if user:
            application, error = is_investor_valid(user, fund)
            if not application:
                raise serializers.ValidationError("El usuario no es un inversionista válido para este fondo")
        
        # Crear auditoría inicial
        initial_audit = self._create_initial_audit(
            request, 
            'TOKEN_BATCH_PURCHASE', 
            fund, 
            'purchase_tokens_batch'
        )
        
        # Resultados generales
        results = {
            'success': True,
            'total_requested': quantity,
            'total_batches': 0,
            'bought': 0,
            'failures': 0,
            'batch_details': [],
            'summary': {
                'completed_batches': 0,
                'failed_batches': 0,
                'total_processing_time': 0
            }
        }
        
        # Verificar si el fondo tiene un contrato de token
        self._validate_contract_address(fund, initial_audit)
        
        start_time = time.time()
        
        try:
            # Obtener todos los token_ids disponibles para compra
            available_token_ids = self._get_batch_available_tokens(fund, quantity, initial_audit)
            
            # Dividir en lotes
            total_batches = (quantity + batch_size - 1) // batch_size  # Ceiling division
            results['total_batches'] = total_batches
            
            # Procesar lote por lote
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, quantity)
                
                # Obtener tokens del lote actual
                token_batch = available_token_ids[start_idx:end_idx]
                
                print(f"Procesando lote de compra {batch_num + 1}/{total_batches} - Tokens {start_idx + 1} a {end_idx}")
                
                # Usar transacción atómica para cada lote
                with transaction.atomic():
                    fund = Fund.objects.select_for_update().get(id=fund_id)
                    
                    batch_start_time = time.time()
                    
                    # Procesar el lote de compras
                    batch_results = self._process_purchase_batch(
                        fund, token_batch, user, results
                    )
                    
                    batch_processing_time = time.time() - batch_start_time
                    
                    # Registrar resultados del lote
                    successful_purchases = sum(1 for r in batch_results if r['success'])
                    batch_summary = {
                        'batch_number': batch_num + 1,
                        'tokens_in_batch': len(token_batch),
                        'successful': successful_purchases,
                        'failed': len(token_batch) - successful_purchases,
                        'processing_time': round(batch_processing_time, 2),
                        'details': batch_results
                    }
                    
                    results['batch_details'].append(batch_summary)
                    
                    if successful_purchases == len(token_batch):
                        results['summary']['completed_batches'] += 1
                        print(f"✅ Lote de compra {batch_num + 1} completado exitosamente")
                    else:
                        results['summary']['failed_batches'] += 1
                        print(f"❌ Lote de compra {batch_num + 1} completado con errores")
                
                # Pequeña pausa entre lotes para evitar saturar el sistema
                time.sleep(0.1)
            
            # Calcular tiempo total
            total_processing_time = time.time() - start_time
            results['summary']['total_processing_time'] = round(total_processing_time, 2)
            
            
            
            # Determinar si la operación fue exitosa
            if results['failures'] == 0:
                results['success'] = True
                status = 'SUCCESS'
            elif results['bought'] > 0:
                results['success'] = False  # Parcialmente exitoso
                status = 'PARTIAL_SUCCESS'
            else:
                results['success'] = False
                status = 'ERROR'
            
            # Actualizar auditoría final
            if initial_audit:
                self._update_audit(initial_audit, status, {
                    'total_requested': quantity,
                    'total_bought': results['bought'],
                    'total_failed': results['failures'],
                    'total_batches': total_batches,
                    'completed_batches': results['summary']['completed_batches'],
                    'processing_time': results['summary']['total_processing_time']
                })
            
            print(f"Operación de compra completada: {results['bought']}/{quantity} tokens comprados en {total_processing_time:.2f}s")
            
        except Exception as e:
            results['success'] = False
            results['error'] = str(e)
            
            if initial_audit:
                self._update_audit(initial_audit, 'ERROR', {'error': str(e)})
            
            print(f"Error en operación masiva de compra: {str(e)}")
        
        return results
    
class PurchaseTokenIndexToIndexSerializer(BaseTokenOperationSerializer):
    """Serializer para comprar tokens usando transferencia index-to-index"""
    token_id = serializers.IntegerField(required=True, help_text="ID del token a comprar")
    index_sender = serializers.CharField(required=True, help_text="Índice de destino del token")
    
    def _handle_purchase_error(self, results, init_audit, token_id, error):
        """Maneja los errores durante el proceso de compra index-to-index."""
        results['failures'] += 1
        results['success'] = False
        results['details'].append({
            'token_id': token_id,
            'success': False,
            'error': error
        })
        
        if init_audit:
            self._update_audit(init_audit, 'ERROR', {'error': str(error)})
    
    def _handle_purchase_success(self, results, init_audit, fund, token_id, result_data, user):
        """Maneja el éxito durante el proceso de compra index-to-index."""
        results['bought'] += 1
        results['success'] = True
        results['details'].append({
            'token_id': token_id,
            'success': True,
            'transaction_id': result_data.get('id')
        })
        
        TransferReceipt.objects.create(
            fund=fund,
            user=user,
            transaction_id=result_data.get('id'),
            description='Transferencia index-to-index exitosa, token #{} para usuario: {}'.format(
                token_id, 
                user.email
                )
            )
        
        if init_audit:
            audit_details = {
                'transaction_id': result_data.get('id')
            }
            self._update_audit(init_audit, 'SUCCESS', audit_details, 
                              transaction_id=result_data.get('id') if 'id' in result_data else None)
    
    def _execute_token_operation(self, validated_data):
        """Implementación específica para comprar tokens usando index-to-index"""
        fund_id = validated_data.get('fund_id')
        token_id = validated_data.get('token_id')
        index_sender = validated_data.get('index_sender')
        
        fund = self._get_fund(fund_id)
        
        # Datos para auditoría
        request = self.context.get('request')
        user = request.user if request else None
        
        # Crear auditoría inicial
        init_audit = self._create_initial_audit(request, 'TOKEN_TRANSFER', fund, 'purchase_token_index_to_index')
        
        # Resultados para un solo token
        results = {
            'success': True,
            'total_to_buy': 1,
            'bought': 0,
            'failures': 0,
            'details': []
        }
        
        # Verificar si el fondo tiene un contrato de token
        self._validate_contract_address(fund, init_audit)
        
        # Usar transacción atómica
        with transaction.atomic():
            fund = Fund.objects.select_for_update().get(id=fund_id)
            
            try:
                # Ejecutar purchase index-to-index
                result_data, error = st721i(token_id, fund.id, fund.contract_address, user, index_sender, fund.hd_wallet)
                
                if not error:
                    self._handle_purchase_success(results, init_audit, fund, token_id, result_data, user)
                else:
                    self._handle_purchase_error(results, init_audit, token_id, error)
                    
            except Exception as e:
                self._handle_exception(results, init_audit, token_id, e)
            
            return results
        