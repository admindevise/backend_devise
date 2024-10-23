from ..models import Socioeconomic
from rest_framework import serializers

class SocioeconomicUserInfoSerializer(serializers.ModelSerializer):
      
    class Meta:
        model = Socioeconomic
        fields = [
            'monthly_income', 'other_income', 'value_other_income',
            'monthly_expenses', 'total_assets', 'total_liabilities',
            'origin_of_funds', 'income_explanation', 'manage_public_resources',
            'links_with_pep', 'foreign_currency_operations', 'foreign_operations_country',
            'foreign_operations_value', 'outside_tax_obligation', 'country_of_tax_residence',
            'tin_number_or_equivalent', 'is_declarant', 'last_year_income_statement',
            'economic_dependency_letter', 'certified_public_accountant', 'profesional_accountant_card',
            'pension_payment_receipt', 'source_funds_support',
            ]
