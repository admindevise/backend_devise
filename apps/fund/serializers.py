from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from rest_framework.exceptions import ValidationError

from apps.fund.models import Fund, FundInvestment, TransferReceipt, FundToken
from apps.kaleido.models import InstanceOfTokenContract721, PromoteContract
from apps.kaleido.serializers.serializer_token_instance import InstanceOfTokenContract721Serializer
from apps.kaleido.serializers.serializer_wallet import WalletFundSerializer

from apps.audit.audit_service import AuditService
from apps.kaleido.views.kaleido_fund import mint_721_token 
from apps.kaleido.utils import create_wallet_for_user, create_instance_token_contract_721
from datetime import datetime


class FundSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    hd_wallet = WalletFundSerializer(read_only=True)
    token_contract_721 = InstanceOfTokenContract721Serializer(read_only=True)
    promote_contract_id = serializers.IntegerField(write_only=True)
    
    #amount_total = serializers.SerializerMethodField()
    #current_price = serializers.SerializerMethodField()
    #total_investors = serializers.SerializerMethodField()
    
    class Meta:
        model = Fund
        fields = [
            # Campos comunes
            'id', 'user', 'hd_wallet', 'name', 'description',
            'amount_units', 'amount_tokens',
            'token_contract_721', 'secret', 'price_per_unit', 'status', 
            'promote_contract_id', 'image', 'created_at',
            
            # Información Regulatoria
            'superintendency_registry', 'tax_id', 'fund_type', 'management_company',
            
            # Parámetros Financieros
            'annual_return', 'initial_unit_value', 'total_assets',
            'management_fee', 'success_fee', 'risk_rating',
            
            # Políticas de Inversión
            'risk_profile', 'investment_horizon', 'asset_composition',
            'dividend_distribution',
            
            # Operaciones
            'minimum_investment', 'permanence_period', 'early_withdrawal_penalty',
            'trading_hours', 'operations_closing_date',
            
            # Otros Campos Relevantes
            'main_manager', 'operations_start_date', 'number_of_investors',
            
            # Funciones
            #'amount_total', 'current_price', 'total_investors'
        ]
        read_only_fields = ['hd_wallet', 'token_contract_721', 'created_at', 'user']
        
    #def get_amount_total(self, obj):
        #return obj.amount_total
    
    #def get_current_price(self, obj):
        #return obj.current_price
    
    #def get_total_investors(self, obj):
        #return obj.total_investors

    def create(self, validated_data):
        user = self.context['request'].user
        secret = validated_data.get('secret')
        
        promote_contract_id = validated_data.pop('promote_contract_id', None)
        
        if not secret:
            raise ValidationError({"secret": "Secret is required."})
        if not promote_contract_id:
            raise ValidationError({"promote_contract_id": "Promote contract id is required."})
        
        # Validar que el promote_contract_id exista
        try:
            promote_contract = PromoteContract.objects.get(id=promote_contract_id)
        except PromoteContract.DoesNotExist:
            raise ValidationError({"promote_contract_id": "Promote contract id is not found."})
        
        # Eliminar "user" de validated_data para evitar que se pase dos veces
        validated_data.pop('user', None)
        
        with transaction.atomic():
            # Crear el Fund
            fund = Fund.objects.create(user=user, **validated_data)
            
            # Crear la wallet
            wallet, error = create_wallet_for_user(user, secret)
            if not wallet:
                raise ValidationError({"hd_wallet": f"Error creating wallet: {error}"})
            fund.hd_wallet = wallet
            fund.save()
            
            # Crear la instancia del contrato token
            token_instance, error = create_instance_token_contract_721(
                user,
                fund.name,
                fund.name[:3].upper(),
                promote_contract=promote_contract
                )
            if not token_instance:
                raise ValidationError({"token_contract": f"Error creating token contract instance: {error}"})
            # Asignar el token_instance al fund
            fund.token_contract_721 = token_instance
            fund.save(update_fields=['token_contract_721'])
            return fund

class FundInvestmentSerializer(serializers.ModelSerializer):
    investor = serializers.PrimaryKeyRelatedField(
        read_only=True, 
        default=serializers.CurrentUserDefault()
    )
    
    joined_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = FundInvestment
        fields = ['fund', 'investor', 'invested_amount', 'joined_at']
        read_only_fields = ['joined_at', 'investor']
        validators = [
            UniqueTogetherValidator(
                queryset=FundInvestment.objects.all(),
                fields=['fund', 'investor'],
                message="You have already invested in this fund."
            )
        ]
        
    def create(self, validated_data):
        # Asignar el usuario actual como inversor
        validated_data['investor'] = self.context['request'].user
        return super().create(validated_data)

class TransferReceiptSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = TransferReceipt
        fields = ['id','user', 'transfer_id', 'fund', 'created_at']
        read_only_fields = ['created_at']

class FundTokenSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = FundToken
        fields = ['id', 'fund', 'token_id', 'created_by', 'created_at']
        read_only_fields = ['created_at']
        
class TokenMintSerializer(serializers.Serializer):
    fund_id = serializers.IntegerField(required=True, help_text="ID del fondo para el cual crear un token")

    def validate_fund_id(self, value):
        """Valida que el fondo exista"""
        try:
            fund = Fund.objects.get(id=value)
            return value
        except Fund.DoesNotExist:
            raise serializers.ValidationError("No existe un fondo con este ID")

    def create(self, validated_data):
        """
        Ejecuta el proceso de mint de un solo token con ID generado como datetime + fund_id + counter.
        """
        fund_id = validated_data.get('fund_id')
        fund = Fund.objects.get(id=fund_id)
        
        # Datos para auditoria
        request = self.context.get('request')
        user = request.user if request else None
        
        # Crear auditoría inicial
        initial_audit = None
        if request:
            initial_audit = AuditService.log_action(
                request=request,
                action_code='TOKEN_CREATE',
                obj=fund,
                details={
                    'fund_id': fund.id,
                    'operation': 'mint_token'
                },
                status='PENDING'
            )
        
        # Resultados para un solo token
        results = {
            'success': True,
            'total_to_mint': 1,
            'minted': 0,
            'failures': 0,
            'details': []
        }
        
        # Usar transacción atómica para todo el proceso
        with transaction.atomic():
            # Usar select_for_update para bloquear la fila durante la transacción
            fund = Fund.objects.select_for_update().get(id=fund_id)
            
            # Verificar que el fondo tenga una dirección de contrato
            if not fund.contract_address:
                
                if initial_audit:
                    initial_audit.status = 'ERROR'
                    initial_audit.details = {
                        'error': "El fondo no tiene una dirección de contrato asociada"
                    }
                    initial_audit.save()
                    
                results['success'] = False
                results['failures'] = 1
                results['details'].append({
                    'error': "El fondo no tiene una dirección de contrato asociada"
                })
                
                return results
            
            try:       
                token_id, next_token_count = self._generate_token_id(fund, initial_audit)
                
                # Ejecutar mint
                result_data, error = mint_721_token(token_id, fund.id)
                
                if error:
                    self._handle_mint_error(results, initial_audit, token_id, error)
                else:
                    self._handle_mint_success(results, initial_audit, fund, next_token_count, token_id, result_data, user)
                    
            except Exception as e:
                self._handle_exception(results, initial_audit, token_id, e)
            
            return results
        
    def _generate_token_id(self, fund, initial_audit):
        """ Manejar la creación de token_id """
        now = datetime.now()
        next_token_count = fund.amount_tokens + 1
        
        date_part = int(now.strftime('%Y%m%d%H%M'))
        fund_id_part = int(fund.id) % 1000  # Limitar a 4 dígitos
        
        # Combinar: YYYYMMDDHHMMSS + XXXXX + XXXX (fecha + id_fondo + contador)
        token_id = (date_part * 1000000) + (fund_id_part * 1000) + next_token_count
        
        if initial_audit:
            self._update_audit(initial_audit, 'PENDING', {'token_id': token_id})
        
        return token_id, next_token_count
    
    def _handle_mint_error(self, results, initial_audit, token_id, error):
        """
        Maneja los errores durante el proceso de mint.
        """
        results['failures'] += 1
        results['success'] = False
        results['details'].append({
            'token_id': token_id,
            'success': False,
            'error': error
        })
        
        if initial_audit:
            self._update_audit(initial_audit, 'ERROR', {'error': str(exception)})

    def _handle_mint_success(self, results, initial_audit, fund, next_token_count, token_id, result_data, user):
        """ Maneja el éxito durante el proceso de mint. """
        fund.amount_tokens = next_token_count
        fund.save(update_fields=['amount_tokens'])
        
        FundToken.objects.create(
            fund=fund,
            token_id=token_id,
            created_by=user
            )
        
        results['minted'] += 1
        results['details'].append({
            'token_id': token_id,
            'success': True,
            'transaction_id': result_data.get('id'),
            'new_token_count': fund.amount_tokens
        })
        
        if initial_audit:
            audit_details = {
                'transaction_id': result_data.get('id'),
                'new_token_count': fund.amount_tokens
                }
            self._update_audit(initial_audit, 'SUCCESS', audit_details, transaction_id=result_data.get('id') if 'id' in result_data else None)
    
    def _handle_exception(self, results, initial_audit, token_id, exception):
        """ Maneja las excepciones durante el proceso de mint. """
        results['failures'] += 1
        results['success'] = False
        results['details'].append({
            'token_id': token_id if 'token_id' in locals() else None,
            'success': False,
            'error': str(exception)
        })
        
        if initial_audit:
            self._update_audit(initial_audit, 'ERROR', {'error': str(exception)})
    
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