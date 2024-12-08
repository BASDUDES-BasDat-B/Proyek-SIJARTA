# utils/decorators.py

from django.http import JsonResponse
from functools import wraps

def custom_login_required(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        user = request.session.get('user')
        if user:
            return function(request, *args, **kwargs)
        else:
            return JsonResponse({'success': False, 'error': 'User not authenticated.'}, status=401)
    return wrap