# Documentación: Nuevo Sistema de Permisos con Decorators

## 🎯 **Eliminación del Orquestador**

Se eliminó el orquestrador de permisos que causaba problemas de:
- Serialización JSON 
- Duplicación de código
- Complejidad de mantenimiento
- Acoplamiento entre servicios

## ✅ **Nueva Implementación: Decorator Pattern**

### **1. Uso en ViewSets con Mixin**

```python
from apps.user.decorators.permissions import TradingPermissionMixin

class SalesOrderViewSet(TradingPermissionMixin, CreateAPIView):
    permission_action_type = 'CREATE_SALES_ORDER'  # ✅ Automático
    serializer_class = SalesOrderSerializer
    
    def get_target_user(self, request):
        """Override para extraer usuario objetivo"""
        if 'seller_user' in request.data:
            return User.objects.get(id=request.data['seller_user'])
        return request.user
```

### **2. Uso con Decorators en Function Views**

```python
from apps.user.decorators.permissions import require_trading_permission

@api_view(['POST'])
@require_trading_permission('CREATE_SALES_ORDER')
def create_sales_order(request):
    serializer = SalesOrderSerializer(data=request.data)
    if serializer.is_valid():
        order = serializer.save()
        return Response(SalesOrderSerializer(order).data)
    return Response(serializer.errors, status=400)
```

### **3. Funciones Helper Personalizadas**

```python
from apps.user.decorators.permissions import require_trading_permission

def extract_seller_user(request, view, *args, **kwargs):
    """Extrae el seller_user del request"""
    if 'seller_user' in request.data:
        return User.objects.get(id=request.data['seller_user'])
    return request.user

@require_trading_permission(
    'CREATE_SALES_ORDER',
    extract_target_user=extract_seller_user
)
def create_custom_order(request):
    # Lógica personalizada
    pass
```

## 🏆 **Ventajas del Nuevo Sistema**

### **Separación Limpia**
- ✅ Permisos = Decorators/Mixins
- ✅ Lógica de negocio = Serializers/Services  
- ✅ No más orquestadores complejos

### **Mantenibilidad**
- ✅ Un decorator se reutiliza en múltiples vistas
- ✅ Cambios de permisos no afectan lógica core
- ✅ Fácil testing independiente

### **Performance**
- ✅ Solo valida permisos cuando es necesario
- ✅ No hay serialización/deserialización extra
- ✅ Menos capas = menos overhead

### **Transparencia**
- ✅ Los servicios funcionan igual con/sin permisos
- ✅ Los serializers no cambian su comportamiento
- ✅ Las respuestas son idénticas

## 📋 **Estados de Validación**

### **Flujo Simplificado**
1. **Request llega** → Decorator intercepta
2. **Valida permisos** → TradingPermissionService.check_permission()
3. **Si OK** → Ejecuta vista normal
4. **Si Error** → HTTP 403 + mensaje de error
5. **Después** → Log automático del uso del permiso

### **Respuestas de Error**
```json
{
    "error": "No tiene permisos válidos para esta acción",
    "requires_permission": true,
    "action_type": "CREATE_SALES_ORDER"
}
```

## 🔧 **Configuración de Permisos**

### **Tipos de Acción Soportados**
- `CREATE_PURCHASE_ORDER`
- `CREATE_SALES_ORDER` 
- `EXECUTE_PAYMENT`
- `CANCEL_ORDER`

### **Uso del TradingPermissionService**
```python
# Crear permiso
permission = TradingPermissionService.grant_trading_permission(
    user=target_user,
    admin_user=admin,
    permission_type='SALES_ORDERS',
    duration_hours=24,
    max_order_amount=Decimal('100000'),
    reason="Permiso para venta de tokens"
)

# El resto es automático con decorators
```

## 🎯 **Migración Completada**

- ❌ **Eliminado**: Orquestador complejo
- ❌ **Eliminado**: Serializers permission-aware
- ❌ **Eliminado**: execute_with_permission
- ✅ **Agregado**: Decorator pattern limpio
- ✅ **Agregado**: Mixin para class-based views
- ✅ **Mantenido**: Servicios core intactos
- ✅ **Mantenido**: Funcionalidad completa

**El sistema ahora es más simple, mantenible y sigue las mejores prácticas de la industria.**
