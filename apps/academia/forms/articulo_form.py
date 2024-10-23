from django import forms
from ..models import Articulo

class ArticuloForm(forms.ModelForm):
    class Meta:
        model = Articulo
        fields = ['categoria', 'titulo',
                'fecha', 'contenido',
                'imagen',
                ]
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color'}),
        }
