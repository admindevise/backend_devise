from rest_framework import serializers
from apps.academy.models import Articles, Category

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class Articleserializer(serializers.ModelSerializer):
    class Meta:
        model = Articles
        fields = '__all__'