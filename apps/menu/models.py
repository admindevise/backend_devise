from django.db import models

# Create your models here.

from django.db import models

# Create your models here.
class MenuPermissions(models.Model):
    name = models.CharField(max_length=128)
    
    class Meta:
        permissions =[
            ("menu_config_document_type", "Configurar Tipo Documento"),
            ("menu_config_bank_type_subtype_account", "Configurar Banco Tipos y Subtipo Cuenta"),
            ("menu_view_referred_list", "Menu ver referidos")
            
        ]

        