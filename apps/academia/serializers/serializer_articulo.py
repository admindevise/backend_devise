from rest_framework import serializers

from apps.academia.serializers.serializer_categoria import CategoriaSerializer
from ..models import Articulo, Categoria

#Tipos de Ctaegoria
class ArticuloSerializer(serializers.ModelSerializer):
    categoria = CategoriaSerializer(read_only=True)
    categoria_id = serializers.PrimaryKeyRelatedField(queryset=Categoria.objects.all(), source='categoria', write_only=True)
    class Meta:
        model=Articulo
        fields = ['id', 'categoria', 'categoria_id', 'titulo', 'fecha', 'contenido', 'imagen']
        read_only_fields = ['id', 'categoria']
