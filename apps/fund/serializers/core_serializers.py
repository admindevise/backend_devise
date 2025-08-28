from django.db import transaction
from rest_framework import serializers
from django.core.validators import RegexValidator
from rest_framework.exceptions import ValidationError

from apps.fund.models import(
    Fund,
    FundToken,
    TransferReceipt,
    FundSemestralDocument,
)
from apps.kaleido.models import PromoteContract

from apps.kaleido.serializers.serializer_token_instance import InstanceOfTokenContract721Serializer
from apps.kaleido.serializers.serializer_wallet import WalletFundSerializer

from apps.kaleido.utils import create_wallet_for_fund, create_instance_token_contract_721


class FundSemestralDocumentSerializer(serializers.ModelSerializer):
    uploaded_date = serializers.DateField(format="%Y-%m-%d", read_only=True)
    period_start_date = serializers.DateField(read_only=False)
    period_end_date = serializers.DateField(read_only=False)
    document_type = serializers.ChoiceField(
        choices=FundSemestralDocument.DocumentType.choices,
        required=True
    )
    semester = serializers.ChoiceField(
        choices=[
            (1, 'Primer Semestre'),
            (2, 'Segundo Semestre')
            ],
        required=True
    )
    year = serializers.IntegerField(required=True)
    
    class Meta:
        model = FundSemestralDocument
        fields = '__all__'
        read_only_fields = ['id', 'fund', 'uploaded_date', 'uploaded_by']
    
    def validate(self, attrs):
        user = self.context['request'].user
        
        try:
            fund = Fund.objects.get(user=user)
        except Fund.DoesNotExist:
            raise ValidationError({
                "fund": "El usuario no tiene un fondo asociado."
            }
            )
        except Fund.MultipleObjectsReturned:
            raise ValidationError({
                "fund": "El usuario está asociado a múltiples fondos."
            })
        
        # Validar que no exista ya un documento para el mismo semestre y tipo
        existing_doc = FundSemestralDocument.objects.select_related('fund').filter(
            fund=fund,
            document_type=attrs['document_type'],
            year=attrs['year'],
            semester=attrs['semester'],
        ).exists()
        
        if existing_doc:
            raise ValidationError({
                "document": "Ya existe un documento para el mismo semestre y tipo."
                })
        
        attrs['_fund'] = fund
        
        return attrs
    
    def create(self, validated_data):
        """
        Crear un nuevo documento semestral y actualizar los campos de periodo automáticamente.
        """
        user = self.context['request'].user
        fund = validated_data.pop('_fund')
        
        # Crear el documento semestral con el fondo automático
        document = FundSemestralDocument.objects.create(
            fund=fund,
            document_type=validated_data['document_type'],
            year=validated_data['year'],
            semester=validated_data['semester'],
            title=validated_data.get('title', ''),
            description=validated_data.get('description', ''),
            document=validated_data['document'],
            period_start_date=validated_data['period_start_date'],
            period_end_date=validated_data['period_end_date'],
            uploaded_by=user
        )
        
        return document

class FundSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    hd_wallet = WalletFundSerializer(read_only=True)
    token_contract_721 = InstanceOfTokenContract721Serializer(read_only=True)
    promote_contract_id = serializers.IntegerField(write_only=True)
    semestral_documents = FundSemestralDocumentSerializer(many=True, read_only=True)
    
    # Validacion para nickname solo numeros y letas
    nickname_tokens = RegexValidator(r'^[a-zA-Z0-9_]+$', 'El nickname solo puede contener letras, números y guiones bajos')
    
    amount_total = serializers.SerializerMethodField()
    current_price = serializers.SerializerMethodField()
    total_investors = serializers.SerializerMethodField()
    
    class Meta:
        model = Fund
        fields = [
            # Campos comunes existentes
            'id', 'user', 'hd_wallet', 'name', 'description',
            'amount_units', 'amount_tokens', 'nickname_tokens',
            'token_contract_721', 'secret', 'price_per_unit', 'status', 
            'promote_contract_id', 'image', 'description_admin',
            'image_admin', 'created_at',
            
            # Información Regulatoria
            'superintendency_registry', 'tax_id', 'fund_type', 'management_company',
            
            # Parámetros Financieros existentes
            'initial_unit_value', 'total_assets',
            'management_fee', 'success_fee', 'risk_rating',
            'current_annual_yield', 'current_return_rate', 'expected_return', 'tir',
            
            # Políticas de Inversión existentes
            'risk_profile', 'investment_horizon', 'asset_composition',
            'dividend_distribution', 'performance_payment_frequency', 'suggested_trend',
            
            # Operaciones existentes
            'minimum_investment', 'permanence_period', 'early_withdrawal_penalty',
            'trading_hours', 'operations_closing_date',
            
            # Otros Campos Relevantes
            'main_manager', 'operations_start_date', 'semestral_documents',
            
            # Documentos y politicas
            'terms_and_conditions', 'data_processing_policy',
            
            # Funciones
            'amount_total', 'current_price', 'total_investors'
        ]
        read_only_fields = [
            'hd_wallet', 'token_contract_721', 'created_at', 'user',
            'terms_and_conditions', 'data_processing_policy', 'semestral_documents'
        ]
        
    def get_amount_total(self, obj):
        return obj.amount_total
    
    def get_current_price(self, obj):
        return obj.current_price
    
    def get_total_investors(self, obj):
        return obj.total_investors

    def create(self, validated_data):
        user = self.context['request'].user
        secret = validated_data.get('secret')
        
        if not user.is_staff:
            raise ValidationError({"user": "Solo los administradores pueden crear fondos."})
        
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
            wallet, error = create_wallet_for_fund(user, secret)
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


class TransferReceiptSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = TransferReceipt
        fields = ['id','user', 'transaction_id', 'fund', 'description', 'created_at']
        read_only_fields = ['created_at']

class FundTokenSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    reserved_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    reservation_expires_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = FundToken
        fields = ['id', 'fund', 'token_id', 'nickname', 'status', 'created_by', 'owner_user', 'reserved_for_sale', 'reserved_for_purchase', 'reserved_at', 'reservation_expires_at' , 'created_at']
        read_only_fields = ['id', 'created_at']
