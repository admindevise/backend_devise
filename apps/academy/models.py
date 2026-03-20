from django.db import models
from apps.utils.models import base_model

from apps.financial_institution.models.core import FinancialInstitution
from apps.utils.models.file_helpers import academy_category_image_path, academy_article_image_path

class Category(base_model.BaseModel): 
    name = models.CharField(max_length=126)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(
        upload_to=academy_category_image_path,
        blank=True,
        null=True,
        )
    color = models.CharField(max_length=16) #value on Hexadecimal
    
    def __str__(self):
        return str(self.name)
    
    
class Articles(base_model.BaseModel):
    financial_institution = models.ForeignKey(FinancialInstitution, on_delete=models.CASCADE, related_name='articles')
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
    )
    title = models.CharField(max_length=126)
    date = models.DateField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    image = models.ImageField(
        upload_to=academy_article_image_path,
        blank=True,
        null=True,
        )
    
    def __str__(self):
        return str(self.title)