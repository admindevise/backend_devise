from apps.security.models import SecurityConfig

parametros_y_valores = [
    {'name':'AUTH_PASSWORD_HISTORY', 'value': '5'}, #Ultimos passwords a recordar
    # Configura el número máximo de intentos fallidos permitidos antes de bloquear la cuenta
    {'name':'AUTH_FAILURES_ALLOWED_ATTEMPTS', 'value': '5'}, 
    {'name':'AUTH_FAILURES_COOLOFF_TIME', 'value': '1800'}, # Tiempo para reiniciar el contador de intentos fallidos (30min)
    # Establece el tiempo durante el cual la cuenta del usuario estará bloqueada (en segundos)
    {'name':'AUTH_FAILURES_LOCKOUT_TIME', 'value': '300'}, #300 segundos (5 minutos)
    #VALIDA SECUENCIA LOGICA DE NUMEROS O LETRAS
    {'name':'VALIDATE_LOGIC_SEQUENCE', 'value': 'TRUE'},
    #valida si las contraseñas de vencen por tiempo
    {'name':'VALIDATE_LOGIC_SEQUENCE', 'value': 'TRUE'},

]