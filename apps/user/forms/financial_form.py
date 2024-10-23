from django import forms
from apps.info_financial.models import Financial
  
class FinancialForm(forms.ModelForm):
    class Meta:
        model = Financial
        fields = [
                'user',
                'bank', 'account_number', 'account_type',
                'account_subtype', 'certification_file',
                'aba_code', 'swift_code',
               ]
        
class UpdateFinancialForm(forms.ModelForm):
    class Meta:
        model = Financial
        fields = [
                'bank', 'account_number', 'account_type',
                'account_subtype', 'certification_file',
                'aba_code', 'swift_code',
               ]