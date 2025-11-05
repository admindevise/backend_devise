from rest_framework import permissions
import copy


class CustomDjangoModelPermission(permissions.DjangoModelPermissions):
    """Extensión de DjangoModelPermissions con permisos GET"""
    
    def __init__(self):
        self.perms_map = copy.deepcopy(self.perms_map)
        self.perms_map['GET'] = ['%(app_label)s.view_%(model_name)s']