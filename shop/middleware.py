from django.shortcuts import redirect


# Страницы куда сотруднику можно заходить всегда
ALLOWED_PREFIXES = [
    '/admin/',
    '/admin-panel/',
    '/moderator/',
    '/courier/',
    '/notifications/',
    '/ai-assistant/',
    '/profile/',
    '/password-change-settings/',
    '/support/',
    '/login/',
    '/logout/',
    '/accounts/',
    '/static/',
    '/media/',
]

ROLE_HOME = {
    'admin':     '/admin-panel/',
    'moderator': '/moderator/reviews/',
    'courier':   '/courier/',
}


class EmployeeRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            employee = getattr(request.user, 'employee', None)
            if employee:
                path = request.path
                # Проверяем — путь разрешён для сотрудника?
                allowed = any(path.startswith(p) for p in ALLOWED_PREFIXES)
                if not allowed:
                    return redirect(ROLE_HOME.get(employee.role, '/admin-panel/'))
        return self.get_response(request)
