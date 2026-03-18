from django.http import JsonResponse

def custom_500_view(request):
    return JsonResponse({
        "type": "server_error",
        "errors": [{
            "code": "internal_error",
            "detail": "Ocurrió un error interno en el servidor.",
            "attr": None
        }]
    }, status=500)


