
from django import forms
from apps.user.models import User
from ..models import Fideicomiso

class FideicomisoUploadForm(forms.ModelForm):
    class Meta: 
        model = Fideicomiso
        fields = [
            'activo', 'fideicomiso', 'gerente_negocio'
        ] 
    
    def __init__(self, activo=None, *args, **kwargs):
        super(FideicomisoUploadForm, self).__init__(*args, **kwargs)
        self.fields['gerente_negocio'].queryset = User.objects.filter(fiducia=activo.fiducia)

class FideicomisoForm(forms.ModelForm):
    class Meta: 
        model = Fideicomiso
        fields = [
            'fideicomiso',
            'email_fiducia', 'name_fiducia', 'aprobado_fiducia',
            'email_devise', 'name_devise', 'aprobado_devise',
            'email_sponsor', 'name_sponsor', 'aprobado_sponsor',
            'email_propietario', 'name_propietario', 'aprobado_propietario',
            'id_weetrust_document', 'fideicomiso_firmado',
        ] 