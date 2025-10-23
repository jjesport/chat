# ===============================================================
#  MÓDULO DE VISTAS - API CHAT DISTRIBUIDO
#  ---------------------------------------------------------------
#  Autor: [Tu nombre]
#  Descripción:
#      Este módulo define los endpoints REST de la API construida
#      en Django para el chat distribuido. Permite consultar mensajes
#      almacenados y estadísticas generales del sistema.
# ===============================================================
import json
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
# ===============================================================
#  FUNCIÓN: get_messages
# ===============================================================
# Descripción:
#   Endpoint GET para obtener todos los mensajes almacenados
#   en el archivo JSON de registros.  
#   - Permite filtrar por usuario mediante el parámetro `user`.  
#   - Requiere autenticación mediante un token de cabecera.  
#
# URL de ejemplo:
#   GET /api/messages
#   GET /api/messages?user=juan
#
# Cabecera requerida:
#   Authorization: Token <API_TOKEN>
# ===============================================================
@csrf_exempt            # Desactiva la protección CSRF (solo para llamadas API)
@require_GET            # Solo acepta solicitudes HTTP GET
def get_messages(request):
    # 1 Validación del token de seguridad
    if not check_token(request):
        return JsonResponse({"error": "Unauthorized"}, status=401)
    # 2️ Obtiene el filtro opcional de usuario (parámetro GET)
    user_filter = request.GET.get('user')
    # 3️ Carga los mensajes almacenados desde el archivo JSON
    with open('../messages.json', 'r', encoding='utf-8') as f:
        messages = [json.loads(line) for line in f if line.strip()]
    # 4️ Si se solicitó filtro por usuario, se aplica
    if user_filter:
        messages = [m for m in messages if m['user'] == user_filter]
    # 5️ Devuelve la lista de mensajes como respuesta JSON
    return JsonResponse(messages, safe=False)

""" 
===============================================================
  FUNCIÓN: check_token
===============================================================
 Descripción:
   Verifica si el token de autorización enviado en la cabecera HTTP
   coincide con el token configurado en settings.py.

 Parámetros:
   request : objeto HttpRequest

 Retorna:
   True  -> Token válido  
   False -> Token inválido o ausente
 ==============================================================="""
def check_token(request):
    # Token esperado (definido en settings.py, ej: API_TOKEN = "mi-token-seguro")
    expected_token = getattr(settings, "API_TOKEN", None)
    # Token proporcionado por el cliente en la cabecera Authorization
    provided_token = request.headers.get("Authorization", "")
    # Comparación exacta del formato "Token <valor>"
    return provided_token == f"Token {expected_token}"

# ===============================================================
#  FUNCIÓN: get_stats
# ===============================================================
# Descripción:
#   Endpoint GET que calcula estadísticas generales del chat,
#   como el número total de mensajes y la cantidad de usuarios únicos.
#
# URL de ejemplo:
#   GET /api/stats
#
# Respuesta JSON:
#   {
#     "total_messages": 120,
#     "unique_users": 8
#   }
# ===============================================================
@csrf_exempt
@require_GET
def get_stats(request):
    # 1️ Carga todos los mensajes del archivo de registros
    with open('../messages.json', 'r', encoding='utf-8') as f:
    # 2️ Calcula estadísticas:
    #     - total: número total de mensajes
    #     - users: cantidad de usuarios únicos
    
        messages = [json.loads(line) for line in f if line.strip()]

    total = len(messages)
    users = len(set(m['user'] for m in messages))
    stats = {'total_messages': total, 'unique_users': users}
    # 3️ Devuelve las estadísticas en formato JSON
    return JsonResponse(stats)
