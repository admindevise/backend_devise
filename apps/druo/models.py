from apps.utils.models import base_model
from apps.user.models import User, IdType
from django.db import models


#Tipos de id  https://developer.druo.com/enums-and-list/id-type/

class UserDruo(models.Model):
    user_devise = models.ForeignKey(User, on_delete = models.PROTECT)
    #Fields filled by response
    created = models.BooleanField(default=True)
    uuid = models.CharField(max_length=128, blank= True, null= True)
    code = models.CharField(max_length=128, blank= True, null= True)
    current_status = models.CharField(max_length=128, blank= True, null= True)
    metadata = models.JSONField(blank= True, null= True)
    created_at = models.DateTimeField(auto_now_add=True)



class Bank(base_model.BaseModel):
    institution_name = models.CharField(max_length=128)
    uuid = models.CharField(max_length=128)
    country = models.CharField(max_length=16)
    network = models.CharField(max_length=16)
    class Meta:
        ordering = ['institution_name']
    def __str__(self):
        return str(self.institution_name)

class AccountType(base_model.BaseModel):
    value = models.CharField(max_length=128)
    name = models.CharField(max_length=128)
    description = models.CharField(max_length=128)

    def __str__(self):
        return str(self.value)
    
class AccountSubtype(base_model.BaseModel):
    value = models.CharField(max_length=128)
    name = models.CharField(max_length=128)
    description = models.CharField(max_length=128)

    def __str__(self):
        return str(self.value)
    
class ConnectAccount(base_model.BaseModel):
    institution_uuid = models.CharField(max_length=128)
    account_number = models.CharField(max_length=128)
    routing_number = models.CharField(max_length=128)
    type = models.CharField(max_length=128)
    subtype = models.CharField(max_length=128)
    user_authorization = models.BooleanField(default=True)
    existing_end_user_id = models.CharField(max_length=128, blank= True, null= True)
    primary_reference = models.CharField(max_length=64) #id of devise
    secondary_reference = models.CharField(max_length=64) #id of devise
    metadata = models.JSONField(blank=True, null=True)
    #Fields filled by response
    uuid = models.CharField(max_length=128, blank= True, null= True)
    code = models.CharField(max_length=128, blank= True, null= True)
    source_connect_link = models.CharField(max_length=128, blank= True, null= True)
    current_status = models.CharField(max_length=64, blank= True, null= True)
    remarks = models.CharField(max_length=64, blank= True, null= True)
    institution = models.CharField(max_length=128, blank= True, null= True)
    name = models.CharField(max_length=128, blank= True, null= True)
    official_name = models.CharField(max_length=128, blank= True, null= True)
    last_4 = models.CharField(max_length=62, blank= True, null= True)
    capabilities = models.CharField(max_length=128, blank= True, null= True)
    end_user = models.JSONField(blank=True, null=True)
    primary_reference = models.CharField(max_length=128, blank=True, null=True)
    secondary_reference = models.CharField(max_length=128, blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)
    date_created_gmt = models.DateTimeField(blank=True, null=True)
    date_updated_gmt = models.DateTimeField(blank=True, null=True)

class Token(base_model.BaseModel):
    token_type = models.CharField(max_length=126)
    expires_in = models.IntegerField()
    access_token =  models.TextField()

    class Meta:
        ordering = ['-created_at']
        get_latest_by = 'created_at'





    
