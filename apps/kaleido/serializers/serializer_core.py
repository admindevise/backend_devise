from rest_framework import serializers
from apps.kaleido.models import AppContract, CompileContract, PromoteContract

class AppContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppContract
        fields = ['user', 'name', 'app_contract_id']
        read_only_fields = ['user', 'id', 'app_contract_id']

class CompileContractSerializer(serializers.ModelSerializer):
    app_contract_id = serializers.CharField(write_only=True)
    
    class Meta:
        model = CompileContract
        fields = ['user', 'compiled_contract_id','description', 'contract_url', 'app_contract_id']
        read_only_fields = ['user', 'compiled_contract_id', 'app_contract_id']
        
    def validate_app_contract_id(self, value):
        try:
            AppContract.objects.get(app_contract_id=value)
        except AppContract.DoesNotExist:
            raise serializers.ValidationError("El AppContract especificado no existe.")
        return value

class PromoteContractSerializer(serializers.ModelSerializer):
    app_contract_id = serializers.CharField(write_only=True)
    compiled_contract_id = serializers.CharField(write_only=True)
    
    class Meta:
        model = PromoteContract
        fields = ['user', 'app_contract_id', 'compiled_contract_id', 'endpoint']
        read_only_fields = ['user', 'app_contract_id', 'compiled_contract_id']
        
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