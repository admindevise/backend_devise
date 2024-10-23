from django import forms
# import User from models.py
from apps.info_workplace.models import Workplace
  
# create a ModelForm
class WorkplaceForm(forms.ModelForm):
    # specify the name of model to use
    class Meta:
        model = Workplace
        fields = [
            'user',
            'occupation', 'company_name', 'company_position', 'company_country',
            'company_region', 'company_city', 'company_phone', 
            'company_address', 'company_zip', 
        ]

class UpdateWorkplaceForm(forms.ModelForm):
    # specify the name of model to use
    class Meta:
        model = Workplace
        fields = [
            'occupation', 'company_name', 'company_position', 'company_country',
            'company_region', 'company_city', 'company_phone', 
            'company_address', 'company_zip', 
        ]