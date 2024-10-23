# import form class from django
from django import forms
# import User from models.py
from ..models import User
  
# create a ModelForm
class UserBasicInfoForm(forms.ModelForm):
    # specify the name of model to use
    class Meta:
        model = User
        fields = [
        'email', 'is_active',
        'indicative', 'phone', 'username',
        'is_natural_person', 'juridic_xlsx',
        'first_name', 'last_name',
        'birth_date', 'birth_country', 'birth_region', 'birth_city',
        'mail_delivery',
        'role',
        ]

class UserDocumentInfoForm(forms.ModelForm):
    # specify the name of model to use
    class Meta:
        model = User
        fields = [
        'local_id_type','document_number',
        'document_front_image','document_back_image',
        'selfie','doc_country_expedition','doc_region_expedition',
        'doc_city_expedition','expedition_date',
        'kyc_validated',
        ]