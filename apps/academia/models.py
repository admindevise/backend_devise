from django.db import models
from apps.utils.models import base_model

class Categoria(base_model.BaseModel): 
    nombre = models.CharField(max_length=126)
    descripcion = models.TextField(blank=True, null=True)
    imagen = models.ImageField(
        upload_to='academia/categoria/',
        blank=True,
        null=True,
        )
    color = models.CharField(max_length=16) #value on Hexadecimal
    
    def __str__(self):
        return str(self.nombre)
    
    
class Articulo(base_model.BaseModel):
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
    )
    titulo = models.CharField(max_length=126)
    fecha = models.DateField(blank=True, null=True)
    contenido = models.TextField(blank=True, null=True)
    imagen = models.ImageField(
        upload_to='academia/articulo/',
        blank=True,
        null=True,
        )
    
    def __str__(self):
        return str(self.titulo)