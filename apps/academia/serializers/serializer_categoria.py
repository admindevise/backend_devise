from rest_framework import serializers
from ..models import Categoria

#Tipos de Ctaegoria
class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model=Categoria
        fields = ['id', 'nombre', 'descripcion', 'imagen', 'color']
