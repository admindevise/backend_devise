# 🎯 **Sistema de Permisos Simplificado - Guía de Pruebas**

## ✅ **Sistema Migrado Exitosamente**

Se eliminó completamente el orquestador complejo y se implementó un sistema limpio basado en **decorators** siguiendo las mejores prácticas de la industria.

## 🧪 **Cómo Probar el Nuevo Sistema**

### **1. Crear Permisos (Como Admin)**

```python
from apps.user.services.permission_service import TradingPermissionService
from decimal import Decimal

# Otorgar permiso de ventas
permission = TradingPermissionService.grant_trading_permission(
    user=cliente_user,          # Usuario que recibirá el permiso
    admin_user=admin_user,      # Admin que otorga el permiso
    permission_type='SALES_ORDERS',
    duration_hours=24,
    max_order_amount=Decimal('100000'),
    max_daily_amount=Decimal('500000'),
    reason="Permiso para venta de tokens Q4"
)
```

### **2. Probar Endpoint con Permisos (Caso Exitoso)**

```bash
# Login como admin
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"admin123"}'

# Crear orden para otro usuario (requiere permisos)
curl -X POST http://localhost:8000/api/sales-orders/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "seller_user": 123,
    "fund": 29,
    "units": 3,
    "price_per_unit": "26000.00",
    "margin": "2.45",
    "expiration_date": "2025-12-14"
  }'

# ✅ Respuesta esperada:
{
    "id": "8e0a126d-4dd1-4390-bc55-52b4c1aaa42c",
    "order_number": "SO-00000013",
    "units": 3,
    "status": "PENDING",
    "fund_name": "vehiculo_inversion",
    "total_amount": "78000.00",
    ...
}
```

### **3. Probar Sin Permisos (Caso de Error)**

```bash
# Intentar crear orden sin permisos otorgados
curl -X POST http://localhost:8000/api/sales-orders/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "seller_user": 456,  # Usuario diferente sin permisos
    "fund": 29,
    "units": 5,
    "price_per_unit": "30000.00",
    "margin": "3.0",
    "expiration_date": "2025-12-14"
  }'

# ❌ Respuesta esperada:
{
    "error": "No tiene permisos válidos para esta acción",
    "requires_permission": true,
    "action_type": "CREATE_SALES_ORDER"
}
```

### **4. Usuario Normal (Sin Problemas)**

```bash
# Login como usuario normal
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"user123"}'

# Crear orden para sí mismo (no requiere permisos especiales)
curl -X POST http://localhost:8000/api/sales-orders/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "fund": 29,
    "units": 2,
    "price_per_unit": "25000.00",
    "margin": "2.0",
    "expiration_date": "2025-12-14"
  }'

# ✅ Funciona normal (seller_user se asigna automáticamente)
```

## 🔍 **Validar Funcionamiento**

### **A. Verificar Logs de Permisos**

```python
from apps.user.models_permission import PermissionExecution

# Ver ejecuciones recientes
executions = PermissionExecution.objects.filter(
    executed_at__date=timezone.now().date()
).order_by('-executed_at')

for execution in executions:
    print(f"Acción: {execution.action_type}")
    print(f"Usuario: {execution.permission.user.email}")
    print(f"Admin: {execution.permission.admin_user.email}")
    print(f"Éxito: {execution.success}")
    print(f"Datos: {execution.action_data}")
    print("---")
```

### **B. Verificar Contadores de Uso**

```python
from apps.user.models_permission import UserAdminPermission

permission = UserAdminPermission.objects.get(id=permission_id)
print(f"Usos: {permission.usage_count}")
print(f"Último uso: {permission.last_used_at}")
print(f"Total usado: {permission.total_amount_used}")
```

## 🎯 **Casos de Prueba Específicos**

### **Caso 1: Límite de Monto**
```python
# Crear permiso con límite bajo
permission = TradingPermissionService.grant_trading_permission(
    user=cliente,
    admin_user=admin,
    permission_type='SALES_ORDERS',
    max_order_amount=Decimal('10000')  # Límite bajo
)

# Intentar orden por monto mayor
# Resultado: HTTP 403 - "Monto excede el límite por orden"
```

### **Caso 2: Límite Diario**
```python
# Crear permiso con límite diario
permission = TradingPermissionService.grant_trading_permission(
    user=cliente,
    admin_user=admin,
    permission_type='SALES_ORDERS',
    max_daily_amount=Decimal('50000')
)

# Crear múltiples órdenes hasta exceder límite diario
# Resultado: Las primeras pasan, luego HTTP 403 - "Límite diario excedido"
```

### **Caso 3: Permiso Expirado**
```python
# Crear permiso que expira pronto
permission = TradingPermissionService.grant_trading_permission(
    user=cliente,
    admin_user=admin,
    permission_type='SALES_ORDERS',
    duration_hours=0.1  # 6 minutos
)

# Esperar 10 minutos y probar
# Resultado: HTTP 403 - "No tiene permisos válidos"
```

## ✅ **Diferencias Clave vs Sistema Anterior**

| Aspecto | Orquestador Anterior | Nuevo Sistema con Decorators |
|---------|---------------------|------------------------------|
| **Complejidad** | ❌ Alta - muchas capas | ✅ Baja - decorators simples |
| **Mantenimiento** | ❌ Difícil - código duplicado | ✅ Fácil - lógica centralizada |
| **Performance** | ❌ Serialización extra | ✅ Directo - sin overhead |
| **Debugging** | ❌ Difícil rastrear errores | ✅ Claro - stack traces limpios |
| **Consistencia** | ❌ Respuestas diferentes | ✅ Respuestas idénticas |
| **Testing** | ❌ Complejo - muchos mocks | ✅ Simple - decorators aislados |

## 🚀 **Sistema Listo para Producción**

El nuevo sistema es más:
- **Confiable**: Menos capas = menos puntos de fallo
- **Mantenible**: Cambios de permisos no afectan lógica core  
- **Escalable**: Patrón estándar de la industria
- **Transparente**: Los servicios core no cambian

**¡La migración fue exitosa y el sistema está listo para uso!** 🎉
