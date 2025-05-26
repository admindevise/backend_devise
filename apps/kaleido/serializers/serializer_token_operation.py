from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.core.validators import RegexValidator

from apps.fund.models import Fund, FundToken, TransferReceipt

from apps.audit.audit_service import AuditService
from apps.kaleido.utils import (
    get_owner_of,
    mint_721_token, burn_721_token, safe_transfer_721,
    safe_transfer_721_index_to_index as st721i,
    )

from django.db import transaction
from datetime import datetime
import time

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
        next_token_count = fund.amount_tokens + 1
        
        date_part = int(now.strftime('%Y%m%d%H%M%S'))
        fund_id_part = int(fund.id) % 1000  # Limitar a 4 dígitos
        
        token_id = (date_part * 1000000) + (fund_id_part * 1000) + next_token_count
        
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
        entry_nickname = f"{prefix}_{fund.amount_tokens}"
        
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
        
        FundToken.objects.create(
            fund=fund,
            token_id=token_id,
            nickname=generated_nickname,
            created_by=user,
            owner_user=user,
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
                
                # Crear el token
                result_data, error = mint_721_token(token_id, fund.id, fund.contract_address)
                
                if not error:
                    self._handle_mint_success(results, initial_audit, fund, next_token_count, token_id, result_data, user)
                else:
                    self._handle_mint_error(results, initial_audit, token_id, error)
                    
            except Exception as e:
                self._handle_exception(results, initial_audit, token_id if 'token_id' in locals() else None, e)
        
        # Determinar estado final
        if results['minted'] == 0:
            results['success'] = False
        
        return results
      
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
        # Eliminar el token de la base de datos
        FundToken.objects.filter(fund=fund, token_id=token_id).delete()
        
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
    
class PurchaseTokenSerializer(BaseTokenOperationSerializer):
    """Serializer para comprar tokens existentes"""
    token_id = serializers.IntegerField(required=True, help_text="ID del token a comprar")

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
        fund_id = validated_data.get('fund_id')
        token_id = validated_data.get('token_id')
        
        fund = self._get_fund(fund_id)
        
        # Datos para auditoría
        request = self.context.get('request')
        user = request.user if request else None
        
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
        
        # Usar transacción atómica
        with transaction.atomic():
            fund = Fund.objects.select_for_update().get(id=fund_id)
            
            try:
                # Ejecutar purchase
                result_data, error = safe_transfer_721(token_id, fund.id, fund.contract_address, user)
                
                if not error:
                    self._handle_purchase_success(results, init_audit, fund, token_id, result_data, user)
                else:
                    self._handle_purchase_error(results, init_audit, token_id, error)
                    
            except Exception as e:
                self._handle_exception(results, init_audit, token_id, e)
            
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
        