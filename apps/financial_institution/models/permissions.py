from django.db import models
from django.contrib.contenttypes.models import ContentType

"""
Sistema de permisos multi-tenant para instituciones financieras
Cada FI define sus propios grupos y permisos
"""

class FIPermission(models.Model):
    """
    Permisos disponibles para instituciones financieras
    Define qué acciones puede realizar un grupo
    """
    
    codename = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Código de permiso",
        help_text="Identificador único del permiso (ej: 'view_applications')"
    )
    
    name = models.CharField(
        max_length=255,
        verbose_name="Nombre"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="Descripción"
    )
    
    category = models.CharField(
        max_length=50,
        default='general',
        verbose_name="Categoría"
    )
    
    module = models.CharField(
        max_length=100,
        verbose_name="Módulo",
        help_text="Módulo al que petenece (fi, fund, trading, etc)",
        db_index= True
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['module', 'category', 'name']
        verbose_name = "Permiso FI"
        verbose_name_plural = "Permisos FI"
        indexes = [
            models.Index(fields=['module', 'category']),
            models.Index(fields=['codename', 'is_active']),
        ]
    
    def __str__(self):
        return f"[{self.module}] {self.name} ({self.codename})"


class FICustomGroup(models.Model):
    """
    Grupos personalizados por Institución Financiera
    Reemplazan a los grupos de Django para contexto FI
    """
    
    financial_institution = models.ForeignKey(
        'financial_institution.FinancialInstitution',
        on_delete=models.CASCADE,
        related_name='custom_groups',
        verbose_name="Institución Financiera"
    )
    
    name = models.CharField(
        max_length=150,
        verbose_name="Nombre del grupo"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="Descripción"
    )
    
    # Permisos asignados a este grupo
    permissions = models.ManyToManyField(
        'FIPermission',
        blank=True,
        related_name='groups',
        verbose_name="Permisos"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [('financial_institution', 'name')]
        ordering = ['financial_institution', 'name']
        verbose_name = "Grupo Personalizado FI"
        verbose_name_plural = "Grupos Personalizados FI"
    
    def __str__(self):
        return f"{self.financial_institution.short_name} - {self.name}"


class FIUserGroupMembership(models.Model):
    """
    Membresía de usuarios en grupos de instituciones financieras
    Un usuario puede pertenecer a diferentes grupos en diferentes FI
    """
    
    user = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        related_name='fi_group_memberships',
        verbose_name="Usuario"
    )
    
    group = models.ForeignKey(
        'FICustomGroup',
        on_delete=models.CASCADE,
        related_name='user_memberships',
        verbose_name="Grupo"
    )
    
    # Fecha de asignación y vigencia
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fi_group_assignments_made',
        verbose_name="Asignado por"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name="Notas"
    )
    
    class Meta:
        unique_together = [('user', 'group')]
        ordering = ['-assigned_at']
        verbose_name = "Membresía de Usuario en Grupo FI"
        verbose_name_plural = "Membresías de Usuarios en Grupos FI"
        indexes = [
            models.Index(fields=['user', 'group', 'is_active']),
            models.Index(fields=['group', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.email} → {self.group.name} ({self.group.financial_institution.short_name})"
    
    