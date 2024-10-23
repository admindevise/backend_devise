from rest_framework import serializers

from apps.academia.serializers.serializer_categoria import CategoriaSerializer
from ..models import Articulo

#Tipos de Ctaegoria
class ArticuloSerializer(serializers.ModelSerializer):
    categoria = CategoriaSerializer(read_only=True)
    class Meta:
        model=Articulo
        fields = ['id', 'categoria', 'titulo', 'fecha', 'contenido', 'imagen']
