from django import forms
from apps.asset.models import ActivoInversion


class NuevaEscrituraActivoForm(forms.ModelForm):
    class Meta: 
        model = ActivoInversion
        fields = [
            'nueva_escritura',
        ] 