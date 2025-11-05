# 🏗️ Sistema de Permisos Multi-Tenant

**Versión:** 1.0.0  
**Fecha:** Octubre 2025  
**Autor:** Devise Team

---

## 📋 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Componentes Principales](#componentes-principales)
4. [Flujo de Verificación](#flujo-de-verificación)
5. [Casos de Uso](#casos-de-uso)
6. [Configuración](#configuración)
7. [Extensión del Sistema](#extensión-del-sistema)
8. [Mejores Prácticas](#mejores-prácticas)

---

## 🎯 Introducción

El **Sistema de Permisos Multi-Tenant** es una arquitectura centralizada que permite gestionar permisos granulares a nivel de:

- **Módulos** (Financial Institution, Fund, Trading, etc.)
- **Acciones** (list, create, update, approve, etc.)
- **Contextos** (Instituciones Financieras específicas, Fondos, etc.)
- **Roles** (Staff Global, Grupos Personalizados por FI, Clientes)

### ✨ Características Principales

- ✅ **Multi-tenant:** Cada FI gestiona sus propios grupos y permisos
- ✅ **Sin hardcoding:** Toda configuración es dinámica y centralizada
- ✅ **Escalable:** Agregar módulos no requiere cambios en el código base
- ✅ **Granular:** Permisos a nivel de acción (ViewSet methods)
- ✅ **Auditable:** Registro completo de asignaciones y cambios

---

## 🏛️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE PRESENTACIÓN                      │
│                    (ViewSets / API REST)                     │
└───────────────────────┬─────────────────────────────────────┘
                        │ permission_classes = [RegistryPermission]
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              CAPA DE CONTROL DE ACCESO                       │
│         api_permissions.py (RegistryPermission)              │
│  • Intercepta requests                                       │
│  • Identifica ViewSet y acción                              │
│  • Consulta configuración                                    │
└───────────────────────┬─────────────────────────────────────┘
                        │
         ┌──────────────┴──────────────┐
         │                             │
         ▼                             ▼
┌──────────────────────┐    ┌─────────────────────────────────┐
│   CONFIGURACIÓN      │    │   SERVICIOS DE VERIFICACIÓN     │
│ permissions_config.py│    │   permission_service.py         │
│  • Permisos          │    │  • Consultas a BD               │
│  • Mapeos            │    │  • Lógica de negocio            │
│  • Reglas            │    │  • Gestión de grupos            │
└──────────────────────┘    └─────────────────────────────────┘
                                        │
                                        ▼
                        ┌─────────────────────────────────┐
                        │      CAPA DE DATOS              │
                        │  • FIPermission                 │
                        │  • FICustomGroup                │
                        │  • FIUserGroupMembership        │
                        └─────────────────────────────────┘
```

---

## 📦 Componentes Principales

### 1️⃣ `permissions_config.py` - **CEREBRO DEL SISTEMA**

**Propósito:** Configuración centralizada de todos los permisos del sistema.

**Responsabilidades:**
- Define catálogo de permisos por módulo
- Mapea ViewSets a permisos requeridos
- Establece reglas por módulo (staff_groups, client_groups, etc.)

**Estructura:**

```python
# Catálogo de permisos por módulo
FINANCIAL_INSTITUTION_PERMISSIONS = {
    'view_applications': 'view_applications',
    'create_applications': 'create_applications',
    'approve_applications': 'approve_applications',
    # ...
}

# Mapeo: ViewSet → Permiso requerido
VIEWSET_PERMISSION_MAP = {
    'financial_institution.FIApplicationViewSet': {
        'list': ('fi', 'view_applications'),
        'create': ('fi', 'create_applications'),
    },
}

# Reglas por módulo
PERMISSION_RULES = {
    'fi': {
        'context_field': 'financial_institution',
        'staff_groups': ['ADMINISTRADOR', 'STAFF'],
        'client_groups': ['INVERSIONISTA'],
        'client_allowed_actions': ['view_applications'],
    },
}
```

**Alcance:**
- ✅ Modificar **SOLO** este archivo para agregar permisos
- ✅ Agregar nuevos módulos sin tocar código base
- ✅ Cambiar grupos permitidos de forma centralizada

---

### 2️⃣ `api_permissions.py` - **VERIFICADOR**

**Propósito:** Clase de permisos que intercepta todas las peticiones.

**Responsabilidades:**
- Interceptar requests a ViewSets
- Identificar ViewSet, acción y contexto
- Consultar configuración y aplicar reglas
- Delegar verificaciones específicas a servicios

**Flujo de Verificación:**

```python
class RegistryPermission(BasePermission):
    def has_permission(self, request, view):
        # 1. Identificar ViewSet y acción
        viewset_name = self._get_viewset_name(view)
        action = getattr(view, 'action', 'list')
        
        # 2. Obtener permiso requerido desde config
        module, permission = self._get_permission_info(viewset_name, action)
        
        # 3. Verificar según reglas del módulo
        return self._check_permission(user, module, permission, request, view)
```

**Niveles de Verificación:**

1. **Staff Global:** Usuarios con grupos de Django (`ADMINISTRADOR`, `STAFF`)
2. **Clientes Globales:** Usuarios con grupos de cliente (`INVERSIONISTA`)
3. **Usuarios con Roles en Contexto:** Usuarios con grupos específicos de FI

**Alcance:**
- ❌ **NO modificar** este archivo (es genérico)
- ✅ Funciona automáticamente con cualquier configuración
- ✅ Soporta múltiples módulos sin cambios

---

### 3️⃣ `permission_service.py` - **CONSULTOR DE BASE DE DATOS**

**Propósito:** Servicio para verificar permisos específicos de cada FI.

**Responsabilidades:**
- Consultar base de datos de permisos
- Verificar membresías de usuarios en grupos de FI
- Obtener permisos de un usuario en contexto específico
- Gestionar asignación/remoción de usuarios a grupos

**Métodos Principales:**

```python
class FIPermissionService:
    
    @staticmethod
    def user_has_permission(user, permission_codename, financial_institution):
        """Verifica si un usuario tiene un permiso en una FI específica"""
        # 1. Verifica super admins
        # 2. Verifica staff global
        # 3. Consulta grupos del usuario en esta FI
        # 4. Verifica permisos de esos grupos
    
    @staticmethod
    def get_user_permissions_in_fi(user, financial_institution):
        """Obtiene TODOS los permisos del usuario en una FI"""
    
    @staticmethod
    def assign_user_to_group(user, group, assigned_by, notes=""):
        """Asigna un usuario a un grupo de FI"""
```

**Alcance:**
- ✅ Modificar para agregar lógica de negocio específica
- ✅ Agregar métodos de utilidad
- ✅ Personalizar mensajes de error

---

### 4️⃣ Modelos de Base de Datos

**Propósito:** Almacenamiento de permisos y grupos personalizados.

**Modelos:**

#### `FIPermission`
```python
# Catálogo global de permisos disponibles
FIPermission
├── codename (unique)        # 'view_applications'
├── name                     # 'Ver Solicitudes'
├── description              # Descripción detallada
└── category                 # 'applications', 'members', 'reports'
```

#### `FICustomGroup`
```python
# Grupos personalizados por cada FI
FICustomGroup
├── financial_institution (FK)  # A qué FI pertenece
├── name                        # 'MANAGERS', 'ANALYSTS'
├── description                 # Descripción del grupo
├── permissions (M2M)           # Permisos asignados
└── is_active                   # Estado del grupo
```

#### `FIUserGroupMembership`
```python
# Membresías de usuarios en grupos
FIUserGroupMembership
├── user (FK)                   # Usuario asignado
├── group (FK)                  # Grupo de FI
├── assigned_by (FK)            # Quién lo asignó
├── assigned_at                 # Cuándo fue asignado
├── is_active                   # Estado de la membresía
└── notes                       # Notas adicionales
```

**Alcance:**
- ✅ Agregar campos personalizados
- ✅ Agregar índices para optimización
- ✅ Agregar constraints de validación

---

## 🔄 Flujo de Verificación de Permisos

### Escenario: Usuario intenta listar solicitudes de FI

```
┌─────────────────────────────────────────────────────────────┐
│ 1. REQUEST                                                   │
│ GET /financial-institution/api/list-applications/           │
│     ?financial_institution=1                                 │
│ Headers: Authorization: Bearer <token>                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. VISTA (ViewSet)                                           │
│ class FinancialInstitutionApplicationViewSet:               │
│     permission_classes = [RegistryPermission]  ◄─────┐      │
└───────────────────────┬─────────────────────────────┼───────┘
                        │                             │
                        ▼                             │
┌─────────────────────────────────────────────────────┼───────┐
│ 3. RegistryPermission.has_permission()             │       │
│                                                      │       │
│ Paso 1: Identificar ViewSet y acción               │       │
│   → viewset_name = 'financial_institution.         │       │
│                     FIApplicationViewSet'           │       │
│   → action = 'list'                                 │       │
│                                                      │       │
│ Paso 2: Consultar permissions_config.py ───────────┘       │
│   → VIEWSET_PERMISSION_MAP[viewset_name]['list']           │
│   → Resultado: ('fi', 'view_applications')                 │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Aplicar Reglas del Módulo 'fi'                           │
│                                                               │
│ rules = PERMISSION_RULES['fi']                              │
│   → staff_groups = ['ADMINISTRADOR', 'STAFF']               │
│   → client_groups = ['INVERSIONISTA']                       │
│   → client_allowed_actions = ['view_applications']          │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌──────────────────┐          ┌────────────────────────┐
│ 5A. ¿Es Staff?   │          │ 5B. ¿Es Cliente?       │
│                  │          │                        │
│ user.groups in   │          │ user.groups in         │
│ ['ADMINISTRADOR']│          │ ['INVERSIONISTA']      │
│                  │          │                        │
│ → SÍ ✅          │          │ → SÍ ✅                │
│ → PERMITIR       │          │ → Verificar acción     │
└──────────────────┘          │   'view_applications'  │
                              │   en allowed_actions   │
                              │ → SÍ ✅                │
                              │ → PERMITIR             │
                              └────────────────────────┘
                                        │
                                        ▼
                        ┌──────────────────────────────┐
                        │ 5C. ¿Tiene rol en FI?        │
                        │                              │
                        │ FIPermissionService          │
                        │   .user_has_permission()     │
                        │                              │
                        │ → Consulta DB:               │
                        │   FIUserGroupMembership      │
                        │   • user = john@example.com  │
                        │   • FI = FI_A                │
                        │   • is_active = True         │
                        │                              │
                        │ → Resultado: Pertenece a     │
                        │   grupo 'MANAGERS' de FI_A   │
                        │                              │
                        │ → Grupo tiene permiso        │
                        │   'view_applications' ✅     │
                        │                              │
                        │ → PERMITIR                   │
                        └──────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. RESPUESTA                                                 │
│ HTTP 200 OK                                                  │
│ [                                                            │
│   {                                                          │
│     "id": 1,                                                 │
│     "user": "cliente1@example.com",                         │
│     "financial_institution": "FI Alpha",                    │
│     "status": "pending"                                     │
│   }                                                          │
│ ]                                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Casos de Uso

### Caso 1: Staff Global ve todas las solicitudes

**Usuario:** `admin@devise.com` (Grupo: `ADMINISTRADOR`)

```python
# Request
GET /financial-institution/api/list-applications/

# Verificación
1. RegistryPermission verifica
2. user.is_staff = True
3. user.groups = ['ADMINISTRADOR']
4. 'ADMINISTRADOR' in PERMISSION_RULES['fi']['staff_groups'] ✅
5. ACCESO PERMITIDO

# Respuesta
✅ Ve TODAS las solicitudes de TODAS las FI
```

---

### Caso 2: Cliente solo ve sus solicitudes

**Usuario:** `cliente@example.com` (Grupo: `INVERSIONISTA`)

```python
# Request
GET /financial-institution/api/list-applications/

# Verificación
1. RegistryPermission verifica
2. user.groups = ['INVERSIONISTA']
3. 'INVERSIONISTA' in PERMISSION_RULES['fi']['client_groups'] ✅
4. 'view_applications' in client_allowed_actions ✅
5. ACCESO PERMITIDO

# Respuesta
✅ Ve SOLO sus propias solicitudes (filtrado en get_queryset)
```

---

### Caso 3: Manager de FI_A gestiona solicitudes

**Usuario:** `manager@example.com` (Sin grupo Django, tiene rol en FI_A)

```python
# Request
GET /financial-institution/api/list-applications/?financial_institution=1

# Verificación
1. RegistryPermission verifica
2. No es staff global ❌
3. No es cliente ❌
4. Busca contexto: financial_institution = FI_A
5. FIPermissionService.user_has_permission(user, 'view_applications', FI_A)
   a. Busca FIUserGroupMembership
      → user = manager@example.com
      → FI = FI_A
      → Resultado: Pertenece a grupo 'MANAGERS'
   b. Verifica permisos del grupo 'MANAGERS'
      → Tiene permiso 'view_applications' ✅
6. ACCESO PERMITIDO

# Respuesta
✅ Ve solicitudes de FI_A
```

---

### Caso 4: Usuario sin permisos intenta aprobar

**Usuario:** `analyst@example.com` (Grupo: `ANALYST` en FI_A, solo lectura)

```python
# Request
POST /financial-institution/api/list-applications/123/approve/

# Verificación
1. RegistryPermission verifica
2. action = 'approve'
3. Requiere permiso: 'approve_applications'
4. FIPermissionService.user_has_permission(user, 'approve_applications', FI_A)
   a. Busca grupos del usuario en FI_A
      → Grupo: 'ANALYST'
   b. Verifica permisos del grupo 'ANALYST'
      → Tiene: ['view_applications', 'view_members']
      → NO tiene: 'approve_applications' ❌
5. ACCESO DENEGADO

# Respuesta
❌ 403 Forbidden
"Tu rol en FI Alpha (ANALYST) no tiene permiso para: approve_applications"
```

---

## ⚙️ Configuración

### Instalación Inicial

```bash
# 1. Aplicar migraciones
python manage.py migrate financial_institution

# 2. Crear permisos iniciales
python manage.py setup_fi_permissions

# 3. Verificar creación
python manage.py shell
>>> from apps.financial_institution.models.permissions import FIPermission
>>> FIPermission.objects.count()
15  # ✅ Permisos creados
```

### Agregar un Nuevo Módulo

**Ejemplo: Agregar módulo de Assets**

1. **Actualizar `permissions_config.py`:**

```python
# Agregar permisos del módulo
ASSET_PERMISSIONS = {
    'view_assets': 'view_assets',
    'manage_assets': 'manage_assets',
    'approve_assets': 'approve_assets',
}

# Mapear ViewSets
VIEWSET_PERMISSION_MAP = {
    # ... existentes ...
    'asset.AssetViewSet': {
        'list': ('asset', 'view_assets'),
        'create': ('asset', 'manage_assets'),
        'approve': ('asset', 'approve_assets'),
    },
}

# Agregar reglas
PERMISSION_RULES = {
    # ... existentes ...
    'asset': {
        'context_field': 'asset',
        'staff_groups': ['ADMINISTRADOR', 'ASSET_MANAGER'],
        'client_groups': ['PROPIETARIO'],
        'client_allowed_actions': ['view_assets'],
    },
}
```

2. **Crear servicio de permisos (opcional):**

```python
# apps/asset/services/permission_service.py
class AssetPermissionService:
    @staticmethod
    def user_has_permission(user, permission_codename, asset):
        # Lógica específica de assets
        pass
```

3. **Actualizar `api_permissions.py` (si es necesario):**

```python
# En _check_permission, agregar verificación para 'asset'
if context_obj and module == 'asset':
    from apps.asset.services.permission_service import AssetPermissionService
    return AssetPermissionService.user_has_permission(user, permission, context_obj)
```

---

## 🚀 Extensión del Sistema

### Agregar Nuevo Permiso a FI

```python
# 1. Agregar en permissions_config.py
FINANCIAL_INSTITUTION_PERMISSIONS = {
    # ... existentes ...
    'export_reports': 'export_reports',  # ✅ Nuevo
}

# 2. Crear el permiso en DB
python manage.py shell
>>> from apps.financial_institution.models.permissions import FIPermission
>>> FIPermission.objects.create(
...     codename='export_reports',
...     name='Exportar Reportes',
...     category='reports'
... )

# 3. Asignar a grupos existentes
>>> from apps.financial_institution.models.permissions import FICustomGroup
>>> group = FICustomGroup.objects.get(name='MANAGERS')
>>> permission = FIPermission.objects.get(codename='export_reports')
>>> group.permissions.add(permission)
```

### Crear Grupo Personalizado para una FI

```python
# Via API REST
POST /financial-institution/api/groups/
{
  "financial_institution": 1,
  "name": "COORDINATORS",
  "description": "Coordinadores de operaciones",
  "permission_ids": [1, 2, 5, 7],
  "is_active": true
}

# Respuesta
{
  "id": 10,
  "name": "COORDINATORS",
  "financial_institution": 1,
  "permissions": [
    {"id": 1, "name": "Ver Solicitudes"},
    {"id": 2, "name": "Crear Solicitudes"},
    ...
  ]
}
```

### Asignar Usuario a Grupo

```python
# Via API REST
POST /financial-institution/api/assign-user-to-group/
{
  "user_id": 52,
  "group_id": 10,
  "notes": "Asignado como coordinador principal"
}

# Respuesta
{
  "success": true,
  "message": "Usuario asignado exitosamente al grupo",
  "membership": {
    "id": 45,
    "user": {"id": 52, "email": "coordinator@example.com"},
    "group": "COORDINATORS"
  }
}
```

---

## 📚 Mejores Prácticas

### ✅ DO (Hacer)

1. **Usar `permissions_config.py` para toda configuración**
   ```python
   # ✅ Correcto
   VIEWSET_PERMISSION_MAP = {
       'new_module.NewViewSet': {
           'list': ('new_module', 'view_items'),
       }
   }
   ```

2. **Documentar permisos nuevos**
   ```python
   # ✅ Correcto
   NEW_MODULE_PERMISSIONS = {
       'view_items': 'view_items',  # Permite ver items del módulo
       'create_items': 'create_items',  # Permite crear nuevos items
   }
   ```

3. **Usar servicios para lógica compleja**
   ```python
   # ✅ Correcto
   class NewModulePermissionService:
       @staticmethod
       def user_has_permission(user, permission, context):
           # Lógica específica del módulo
           pass
   ```

4. **Nombrar grupos de forma consistente**
   ```python
   # ✅ Correcto
   'MANAGERS'     # Plural, mayúsculas
   'ANALYSTS'     # Descriptivo
   'COORDINATORS' # Claro
   ```

### ❌ DON'T (No Hacer)

1. **NO hardcodear permisos en vistas**
   ```python
   # ❌ Incorrecto
   def has_permission(self, request, view):
       if request.user.groups.filter(name='MANAGER').exists():
           return True
   ```

2. **NO duplicar lógica de permisos**
   ```python
   # ❌ Incorrecto
   # En vista A
   if user.is_staff:
       return True
   
   # En vista B
   if user.is_staff:
       return True
   
   # ✅ Correcto: usar RegistryPermission en ambas
   ```

3. **NO modificar `api_permissions.py` para casos específicos**
   ```python
   # ❌ Incorrecto: agregar lógica específica en api_permissions.py
   
   # ✅ Correcto: crear servicio específico
   ```

4. **NO ignorar el contexto en permisos multi-tenant**
   ```python
   # ❌ Incorrecto
   def get_queryset(self):
       return Model.objects.all()  # Retorna de todas las FI
   
   # ✅ Correcto
   def get_queryset(self):
       if not user.is_staff:
           return Model.objects.filter(fi=user_fi)
   ```

---

## 🔍 Troubleshooting

### Problema: Usuario no puede acceder aunque tiene el grupo correcto

**Diagnóstico:**

```python
# 1. Verificar que el grupo está en la configuración
>>> from apps.utils.core_permissions.permissions_config import PERMISSION_RULES
>>> PERMISSION_RULES['fi']['staff_groups']
['ADMINISTRADOR', 'STAFF']  # ¿Está el grupo aquí?

# 2. Verificar grupos del usuario
>>> user.groups.values_list('name', flat=True)
['MANAGER']  # ❌ NO está en staff_groups

# Solución: Agregar 'MANAGER' a staff_groups en permissions_config.py
```

### Problema: Usuario con rol en FI no puede realizar acción

**Diagnóstico:**

```python
# 1. Verificar membresía
>>> from apps.financial_institution.models.permissions import FIUserGroupMembership
>>> FIUserGroupMembership.objects.filter(user=user, is_active=True)
<QuerySet [<Membership: user@example.com → ANALYST>]>

# 2. Verificar permisos del grupo
>>> membership = FIUserGroupMembership.objects.get(user=user, is_active=True)
>>> membership.group.permissions.values_list('codename', flat=True)
['view_applications', 'view_members']  # ❌ NO tiene 'approve_applications'

# Solución: Agregar permiso al grupo o asignar usuario a grupo con más permisos
```

### Problema: Error "No hay configuración de permisos para ViewSet"

**Diagnóstico:**

```python
# Error: "No hay configuración de permisos para: my_app.MyViewSet.list"

# Verificar mapeo en permissions_config.py
>>> from apps.utils.core_permissions.permissions_config import VIEWSET_PERMISSION_MAP
>>> 'my_app.MyViewSet' in VIEWSET_PERMISSION_MAP
False  # ❌ NO está configurado

# Solución: Agregar en VIEWSET_PERMISSION_MAP
VIEWSET_PERMISSION_MAP = {
    'my_app.MyViewSet': {
        'list': ('my_module', 'view_items'),
    }
}
```

---

## 📊 Métricas y Monitoreo

### Auditoría de Permisos

```python
# Obtener todos los usuarios con permisos en una FI
from apps.financial_institution.models.permissions import FIUserGroupMembership

memberships = FIUserGroupMembership.objects.filter(
    group__financial_institution_id=1,
    is_active=True
).select_related('user', 'group', 'assigned_by')

for m in memberships:
    print(f"{m.user.email} → {m.group.name} (asignado por {m.assigned_by.email})")
```

### Permisos por Usuario

```python
# Ver todos los permisos de un usuario en una FI
from apps.financial_institution.services.permission_service import FIPermissionService

perms = FIPermissionService.get_user_permissions_in_fi(user, fi)
print(f"Permisos: {perms}")
# Salida: {'view_applications', 'approve_applications', 'view_members'}
```

### Grupos sin Miembros

```python
# Encontrar grupos sin usuarios asignados
from apps.financial_institution.models.permissions import FICustomGroup

empty_groups = FICustomGroup.objects.annotate(
    member_count=Count('user_memberships', filter=Q(user_memberships__is_active=True))
).filter(member_count=0, is_active=True)

for group in empty_groups:
    print(f"⚠️ {group.financial_institution.short_name}: {group.name} no tiene miembros")
```

---

## 📝 Changelog

### Versión 1.0.0 (Octubre 2025)
- ✅ Implementación inicial del sistema multi-tenant
- ✅ Soporte para Financial Institution
- ✅ API REST completa para gestión de grupos y permisos
- ✅ Documentación completa

### Próximas Versiones
- 🔜 Soporte para módulo Fund
- 🔜 Soporte para módulo Trading
- 🔜 Dashboard de administración de permisos
- 🔜 Exportación de configuraciones

---

## 🤝 Contribución

Para agregar nuevos módulos o permisos:

1. Actualizar `permissions_config.py`
2. Crear modelos de permisos si es necesario
3. Crear servicio de permisos específico
4. Agregar tests
5. Actualizar esta documentación

---

## 📞 Soporte

Para dudas o problemas:
- **Email:** dev@devise.com
- **Slack:** #permissions-support
- **Documentación:** [Confluence](https://devise.atlassian.net)

---

**Última actualización:** Octubre 24, 2025  
**Versión del documento:** 1.0.0
