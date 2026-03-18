from django.http import JsonResponse

def custom_400_view(request, exception=None):
    return JsonResponse({
        "type": "bad_request",
        "errors": [{
            "code": "bad_request",
            "detail": "La solicitud no se pudo procesar debido a un error de sintaxis.",
            "attr": None
        }]
    }, status=400)

def custom_401_view(request, exception=None):
    return JsonResponse({
        "type": "authentication_error",
        "errors": [{
            "code": "unauthorized",
            "detail": "No estás autenticado para acceder a este recurso.",
            "attr": None
        }]
    }, status=401)
def custom_403_view(request, exception=None):
    return JsonResponse({
        "type": "permission_error",
        "errors": [{
            "code": "forbidden",
            "detail": "No tienes permiso para acceder a este recurso.",
            "attr": None
        }]
    }, status=403)
def custom_404_view(request, exception=None):
    return JsonResponse({
        "type": "url_error",
        "errors": [{
            "code": "not_found",
            "detail": "La ruta solicitada no existe o el formato del ID es incorrecto.",
            "attr": None
        }]
    }, status=404)
def custom_405_view(request, exception=None):
    return JsonResponse({
        "type": "method_not_allowed",
        "errors": [{
            "code": "method_not_allowed",
            "detail": "El método HTTP utilizado no está permitido para esta ruta.",
            "attr": None
        }]
    }, status=405)
def custom_500_view(request):
    return JsonResponse({
        "type": "server_error",
        "errors": [{
            "code": "internal_error",
            "detail": "Ocurrió un error interno en el servidor.",
            "attr": None
        }]
    }, status=500)


