from decimal import Decimal
from rest_framework import serializers
from apps.fund.models.commissions import Transfers
from apps.fund.models.core import Fund
from apps.fund.services.transfers import TransferService, TransferServiceError


class TransferCreateSerializer(serializers.Serializer):
    """Serializer para crear una cesión"""
    
    # Datos principales
    fund = serializers.PrimaryKeyRelatedField(
        queryset=Fund.objects.all()
    )
    effective_date = serializers.DateField()
    class_transfer = serializers.CharField(max_length=40)
    
    # Actores principales
    settlor = serializers.CharField(max_length=40)
    assignee = serializers.CharField(max_length=40)
    assigned_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01')
    )
    
    # Datos del cedente (settlor)
    actor_settlor = serializers.CharField(max_length=50)
    nit_settlor = serializers.IntegerField(
        min_value=10000000,
        max_value=9999999999
    )
    type_doc_settlor = serializers.ChoiceField(
        choices=Transfers.TypeIdActor.choices
    )
    id_doc_settlor = serializers.IntegerField(
        min_value=1000000,
        max_value=9999999999
    )
    
    # Datos del cesionario (assignee)
    actor_assignee = serializers.CharField(max_length=50)
    nit_assignee = serializers.IntegerField(
        min_value=10000000,
        max_value=9999999999
    )
    type_doc_assignee = serializers.ChoiceField(
        choices=Transfers.TypeIdActor.choices
    )
    id_doc_assignee = serializers.IntegerField(
        min_value=1000000,
        max_value=9999999999
    )
    
    # Documento opcional
    doc_transfer = serializers.FileField(
        required=False,
        allow_null=True
    )
    
    def validate_settlor(self, value):
        """Validar que el cedente no este vacio"""
        if not value or not value.strip():
            raise serializers.ValidationError("El cedente es requerido")
        return value.strip()
    
    def validate_assignee(self, value):
        """Validar que el cesionario no este vacio"""
        if not value or not value.strip():
            raise serializers.ValidationError("El cesionario es requerido")
        return value.strip()
    
    def validate(self, attrs):
        """Validaciones cruzadas"""
        # Validar que el cedente y el cesionario sean diferentes
        settlor = attrs.get('settlor', '').lower().strip()
        assignee = attrs.get('assignee', '').lower().strip()
        
        if settlor == assignee:
            raise serializers.ValidationError({
                'assignee': "El cesionario debe ser diferente al cedente"
            })
        
        # Validar que los NITS sean diferentes
        if attrs.get('nit_settlor') == attrs.get('nit_assignee'):
            raise serializers.ValidationError({
                'nit_assignee': "El NIT del cesionario debe ser diferente al del cedente"
            })
            
        # Validar documento si se proporciona
        doc = attrs.get('doc_transfer')
        if doc:
            allowed_extensions = ['.pdf', '.doc', '.docx']
            file_name = doc.name.lower()
            if not any(file_name.endswith(ext) for ext in allowed_extensions):
                raise serializers.ValidationError({
                    'doc_transfer': f"Extension no permitida. Use: {', '.join(allowed_extensions)}"
                })
                
            # Validar tamaño (maximo 10MB)
            max_size = 10 * 1024 * 1024
            if doc.size > max_size:
                raise serializers.ValidationError({
                    'doc_transfer': "El archivo no puede superar los 10MB"
                })
        
        return attrs
    
    def create(self, validated_data):
        """Crear cesion usando el servicio"""
        service = TransferService()
        
        try:
            transfer = service.create_transfer(
                fund=validated_data['fund'],
                effective_date=validated_data['effective_date'],
                class_transfer=validated_data['class_transfer'],
                settlor=validated_data['settlor'],
                assignee=validated_data['assignee'],
                assigned_amount=validated_data['assigned_amount'],
                actor_settlor=validated_data['actor_settlor'],
                nit_settlor=validated_data['nit_settlor'],
                type_doc_settlor=validated_data['type_doc_settlor'],
                id_doc_settlor=validated_data['id_doc_settlor'],
                actor_assignee=validated_data['actor_assignee'],
                nit_assignee=validated_data['nit_assignee'],
                type_doc_assignee=validated_data['type_doc_assignee'],
                id_doc_assignee=validated_data['id_doc_assignee'],
                doc_transfer=validated_data.get('doc_transfer'),
            )
            return transfer
        except TransferServiceError as e:
            raise serializers.ValidationError(str(e))
        
class TransferResponseSerializer(serializers.ModelSerializer):
    """Serializer para respuesta despues de crear una cesion"""
    
    fund_name = serializers.CharField(source='fund.name', read_only=True)
    type_doc_settlor_display = serializers.CharField(source='get_type_doc_settlor_display', read_only=True)
    type_doc_assignee_display = serializers.CharField(source='get_type_doc_assignee_display', read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    class Meta:
        model = Transfers
        fields = [
            'id',
            'fund',
            'fund_name',
            'effective_date',
            'class_transfer',
            # Actores
            'settlor',
            'assignee',
            'assigned_amount',
            # Datos cedente
            'actor_settlor',
            'nit_settlor',
            'type_doc_settlor',
            'type_doc_settlor_display',
            'id_doc_settlor',
            # Datos cesionario
            'actor_assignee',
            'nit_assignee',
            'type_doc_assignee',
            'type_doc_assignee_display',    
            'id_doc_assignee',
            # Documento
            'doc_transfer',
            'created_at',
        ]