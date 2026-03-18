from django.http import JsonResponse

def custom_403_view(request, exception=None):
    return JsonResponse({
        "type": "permission_error",
        "errors": [{
            "code": "forbidden",
            "detail": "No tienes permiso para acceder a este recurso.",
            "attr": None
        }]
    }, status=403)
