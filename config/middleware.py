
from django.utils.cache import add_never_cache_headers
from django.shortcuts import redirect
from django.http import HttpResponseForbidden

class DisableCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated:
            add_never_cache_headers(response)

        return response





class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.path.startswith('/adminpanel/'):

            # allow login URLs
            if 'login' in request.path:
                return self.get_response(request)

            if not request.user.is_authenticated:
                return redirect('users:login')

            if not request.user.is_staff:
                return HttpResponseForbidden("You are not authorized")

        return self.get_response(request)
