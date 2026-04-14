from django.shortcuts import render

# Create your views here.



def landing_page(request):
    return render(request, "home/landing.html")                               #  this is the landing page 