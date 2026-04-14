from django.shortcuts import redirect
from django.http import HttpResponseForbidden

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):

        # Not logged in
        if not request.user.is_authenticated:
            return redirect('users:login')

        # Not admin
        if not request.user.is_staff:
            return HttpResponseForbidden("You are not authorized")

        return view_func(request, *args, **kwargs)

    return wrapper