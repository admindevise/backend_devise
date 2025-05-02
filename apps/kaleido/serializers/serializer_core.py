from rest_framework import serializers
from apps.kaleido.models import AppContract, CompileContract, PromoteContract

class AppContractSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    class Meta:
        model = AppContract
        fields = ['id', 'user', 'name', 'app_contract_id', 'created_at']
        read_only_fields = ['user', 'id', 'app_contract_id', 'created_at']

class CompileContractSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    app_contract_id = serializers.CharField(write_only=True)
    
    class Meta:
        model = CompileContract
        fields = ['id', 'user', 'compiled_contract_id','description', 'contract_url', 'app_contract_id', 'created_at']
        read_only_fields = ['id', 'user', 'compiled_contract_id', 'app_contract_id', 'created_at']
        
    def validate_app_contract_id(self, value):
        try:
            AppContract.objects.get(app_contract_id=value)
        except AppContract.DoesNotExist:
            raise serializers.ValidationError("El AppContract especificado no existe.")
        return value

class PromoteContractSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    app_contract_id = serializers.CharField(write_only=True)
    compiled_contract_id = serializers.CharField(write_only=True)
    
    class Meta:
        model = PromoteContract
        fields = ['id', 'user', 'app_contract_id', 'compiled_contract_id', 'endpoint', 'created_at']
        read_only_fields = ['id', 'user', 'app_contract_id', 'compiled_contract_id', 'created_at']
        
    def validate_app_contract_id(self, value):
        try:
            AppContract.objects.get(app_contract_id=value)
        except AppContract.DoesNotExist:
            raise serializers.ValidationError("El AppContract especificado no existe.")
        return value
    
    def validate_compiled_contract_id(self, value):
        try:
            CompileContract.objects.get(compiled_contract_id=value)
        except CompileContract.DoesNotExist:
            raise serializers.ValidationError("El CompileContract especificado no existe.")
        return value