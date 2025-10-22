import json
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@require_GET
def get_messages(request):
    if not check_token(request):
        return JsonResponse({"error": "Unauthorized"}, status=401)
    
    user_filter = request.GET.get('user')
    with open('../messages.json', 'r', encoding='utf-8') as f:
        messages = [json.loads(line) for line in f if line.strip()]

    if user_filter:
        messages = [m for m in messages if m['user'] == user_filter]
    return JsonResponse(messages, safe=False)

def check_token(request):
    expected_token = getattr(settings, "API_TOKEN", None)
    provided_token = request.headers.get("Authorization", "")
    return provided_token == f"Token {expected_token}"

@csrf_exempt
@require_GET
def get_stats(request):
    with open('../messages.json', 'r', encoding='utf-8') as f:
        messages = [json.loads(line) for line in f if line.strip()]

    total = len(messages)
    users = len(set(m['user'] for m in messages))
    stats = {'total_messages': total, 'unique_users': users}
    return JsonResponse(stats)
