from django.shortcuts import render
from apps.products.models import Category



# Create your views here.



def landing_page(request):
    categories = Category.objects.filter(
        is_active=True
    ).order_by("name")

    context = {
        "categories": categories,
    }

    return render(
        request,
        "users/dashboard.html",
        context
    )                            #  this is the landing page 