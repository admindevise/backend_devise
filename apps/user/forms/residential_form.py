from django import forms
from apps.info_residential.models import Residentialplace
  
# create a ModelForm
class ResidentialForm(forms.ModelForm):
    # specify the name of model to use
    class Meta:
        model = Residentialplace
        fields = [
            'user',
            'resident_country', 'resident_region', 'resident_city',
            'resident_address', 'resident_phone', 'resident_zip',
          ]

# update a residential infoModelForm
class UpdateResidentialForm(forms.ModelForm):
    # specify the name of model to use
    class Meta:
        model = Residentialplace
        fields = [
            'resident_country', 'resident_region', 'resident_city',
            'resident_address', 'resident_phone', 'resident_zip',
          ]