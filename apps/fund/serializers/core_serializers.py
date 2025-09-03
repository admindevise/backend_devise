from django.db import transaction
from rest_framework import serializers
from django.core.validators import RegexValidator
from rest_framework.exceptions import ValidationError

from apps.fund.models.core import (
    Fund,
    FundSemestralDocument
)
from apps.fund.models.tokens import FundToken
from apps.fund.models.receipts import TransferReceipt
from apps.kaleido.models import PromoteContract

# Serializers de Kaleido
from apps.kaleido.serializers.serializer_token_instance import InstanceOfTokenContract721Serializer
from apps.kaleido.serializers.serializer_wallet import WalletFundSerializer

# Servicios
from apps.fund.services.fund_service import FundCreationService, FundServiceError

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
        fields = '__all__'
        read_only_fields = [
            'id', 'user', 'terms_and_conditions', 'data_processing_policy',
            'semestral_documents', 'amount_total', 'current_price', 'total_investors'
        ]
        
        
    def validate_name(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("El nombre del fondo no puede estar vacío.")
        if len(value) < 3:
            raise serializers.ValidationError("El nombre del fondo debe tener al menos 3 caracteres.")
        if len(value) > 100:
            raise serializers.ValidationError("El nombre del fondo no puede exceder los 100 caracteres.")
        return value.strip()
    
    def validate_secret(self, value):
        if not value:
            raise serializers.ValidationError("El campo 'secret' es obligatorio.")
        if len(value.split()) < 12:
            raise serializers.ValidationError("El campo 'secret' debe contener al menos 12 palabras.")
        return value
    
    def validate_amount_units(self, value):
        if value <= 0:
            raise serializers.ValidationError("El monto total del fondo debe ser mayor que cero.")
        return value
    
    def validate_price_per_unit(self, value):
        if value <= 0:
            raise serializers.ValidationError("El precio por unidad debe ser mayor que cero.")
        return value
    
    def validate_promote_contract_id(self, value):
        try:
            PromoteContract.objects.get(id=value)
        except PromoteContract.DoesNotExist:
            raise serializers.ValidationError("El contrato de promoción con el ID proporcionado no existe.")
        except PromoteContract.MultipleObjectsReturned:
            raise serializers.ValidationError("El ID del contrato de promoción proporcionado es ambiguo.")
        
        return value
        
    def get_amount_total(self, obj):
        return obj.amount_total
    
    def get_current_price(self, obj):
        return obj.current_price
    
    def get_total_investors(self, obj):
        return obj.total_investors

    def create(self, validated_data):
        user = self.context['request'].user
        request = self.context.get('request')
        
        try:
            # Crear el fondo usando el servicio
            fund = FundCreationService.create_fund(
                user=user,
                fund_data= validated_data,
                request=request
            )
            return fund
        except FundServiceError as e:
            raise ValidationError({"detail": [str(e)]})
        except ValidationError as e:
            raise e
        except Exception as e:
            raise ValidationError({"detail": [f"Ha ocurrido un error inesperado: {str(e)}"]})


class TransferReceiptSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = TransferReceipt
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'user', 'fund', 'status']

class FundTokenSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    reserved_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    reservation_expires_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = FundToken
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'fund', 'owner_user', 'status', 'reserved_at', 'reservation_expires_at']
