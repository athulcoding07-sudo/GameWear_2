from django.shortcuts import render

from django.db.models import Prefetch
from django.utils import timezone

from apps.products.models import Category
from apps.offers.models import CategoryOffer



# Create your views here.



def landing_page(request):
    now = timezone.now()

    active_offers = CategoryOffer.objects.filter(
        is_active=True,
        start_date__lte=timezone.now(),
        end_date__gte=timezone.now(),
    )

    categories = (
        Category.objects.filter(is_active=True)
        .prefetch_related(
            Prefetch(
                "offers",   # <-- related_name
                queryset=active_offers,
                to_attr="active_offers",
            )
        )
        .order_by("name")
    )

    context = {
        "categories": categories,
    }

    return render(
        request,
        "users/dashboard.html",
        context,
    )