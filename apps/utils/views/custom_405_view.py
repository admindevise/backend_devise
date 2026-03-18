from django.http import JsonResponse

def custom_405_view(request, exception=None):
    return JsonResponse({
        "type": "method_not_allowed",
        "errors": [{
            "code": "method_not_allowed",
            "detail": "El método HTTP utilizado no está permitido para esta ruta.",
            "attr": None
        }]
    }, status=405)
