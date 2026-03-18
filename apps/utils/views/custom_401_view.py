from django.http import JsonResponse

def custom_401_view(request, exception=None):
    return JsonResponse({
        "type": "authentication_error",
        "errors": [{
            "code": "unauthorized",
            "detail": "No estás autenticado para acceder a este recurso.",
            "attr": None
        }]
    }, status=401)