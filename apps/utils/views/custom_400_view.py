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