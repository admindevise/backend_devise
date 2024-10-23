from django import forms
from ..models import Categoria

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion',
                'imagen', 'color'
                ]
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color'}),
        }
