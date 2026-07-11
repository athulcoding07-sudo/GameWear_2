from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import logout
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.contrib import messages
from apps.products.models import Category
from django.http import JsonResponse
from .forms import UserForm
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
import calendar

from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone


from apps.products.models import Product, Category,Order, OrderItem
from apps.users.models import User

#from apps.products.forms import CategoryForm


User = get_user_model()


# Create your views here.
@staff_member_required
def admin_dashboard(request):
    filter_type = request.GET.get("filter", "monthly")

    today = timezone.now()

    # Only completed orders are considered sales
    orders = Order.objects.filter(status="DELIVERED")

    # -----------------------
    # FILTERS
    # -----------------------

    if filter_type == "daily":
        orders = orders.filter(created_at__date=today.date())

    elif filter_type == "weekly":
        start_date = today - timedelta(days=6)
        orders = orders.filter(created_at__date__gte=start_date.date())

    elif filter_type == "monthly":
        orders = orders.filter(created_at__year=today.year)

    elif filter_type == "yearly":
        pass

    # -----------------------
    # VALID ORDER ITEMS
    # -----------------------

    order_items = OrderItem.objects.filter(
        order__in=orders
    ).exclude(
        status__in=[
            "CANCELLED",
            "RETURNED",
            "PARTIAL_CANCELLED",
            "PARTIAL_RETURNED",
        ]
    )

    # -----------------------
    # SUMMARY
    # -----------------------

    total_sales = (
        orders.aggregate(total=Sum("final_amount"))["total"] or 0
    )

    total_orders = orders.count()

    total_users = User.objects.count()

    delivered_orders = Order.objects.filter(
        status="DELIVERED"
    ).count()

    total_products = Product.objects.count()

    total_categories = Category.objects.count()

    # -----------------------
    # TOP PRODUCTS
    # -----------------------

    top_products = (
        order_items.values(
            "product__name"
        )
        .annotate(
            total_sold=Sum("quantity")
        )
        .order_by("-total_sold")[:10]
    )

    # -----------------------
    # TOP CATEGORIES
    # -----------------------

    top_categories = (
        order_items.values(
            "product__category__name"
        )
        .annotate(
            total_sold=Sum("quantity")
        )
        .order_by("-total_sold")[:10]
    )

    # -----------------------
    # SALES CHART
    # -----------------------

    sales_data = []

    if filter_type == "daily":

        for i in range(6, -1, -1):

            day = today - timedelta(days=i)

            revenue = (
                Order.objects.filter(
                    status="DELIVERED",
                    created_at__date=day.date(),
                ).aggregate(
                    total=Sum("final_amount")
                )["total"]
                or 0
            )

            sales_data.append(
                {
                    "label": day.strftime("%d %b"),
                    "total": float(revenue),
                }
            )

    elif filter_type == "weekly":

        for i in range(3, -1, -1):

            end = today - timedelta(days=i * 7)
            start = end - timedelta(days=6)

            revenue = (
                Order.objects.filter(
                    status="DELIVERED",
                    created_at__date__range=[
                        start.date(),
                        end.date(),
                    ],
                ).aggregate(
                    total=Sum("final_amount")
                )["total"]
                or 0
            )

            sales_data.append(
                {
                    "label": f"Week {4-i}",
                    "total": float(revenue),
                }
            )

    elif filter_type == "monthly":

        for month in range(1, 13):

            revenue = (
                Order.objects.filter(
                    status="DELIVERED",
                    created_at__year=today.year,
                    created_at__month=month,
                ).aggregate(
                    total=Sum("final_amount")
                )["total"]
                or 0
            )

            sales_data.append(
                {
                    "label": calendar.month_abbr[month],
                    "total": float(revenue),
                }
            )

    elif filter_type == "yearly":

        current_year = today.year

        for year in range(current_year - 4, current_year + 1):

            revenue = (
                Order.objects.filter(
                    status="DELIVERED",
                    created_at__year=year,
                ).aggregate(
                    total=Sum("final_amount")
                )["total"]
                or 0
            )

            sales_data.append(
                {
                    "label": str(year),
                    "total": float(revenue),
                }
            )

    context = {
        "filter_type": filter_type,

        "total_sales": total_sales,
        "total_orders": total_orders,
        "total_users": total_users,
        "delivered_orders": delivered_orders,
        "total_products": total_products,
        "total_categories": total_categories,

        "top_products": top_products,
        "top_categories": top_categories,

        "sales_data": sales_data,
    }

    return render(
        request,
        "adminpanel/dashboard.html",
        context,
    )

@staff_member_required
def customers_view(request, customer_id):
    customer = get_object_or_404(
        User,
        id=customer_id,
        is_staff=False,
        is_superuser=False
    )

    # calculate SAME number as list view
    customer_index = (
        User.objects
        .filter(is_staff=False, is_superuser=False, id__lt=customer.id)
        .count()
    ) + 1

    return render(
        request,
        "adminpanel/customers/customers_view.html",
        {
            "customer": customer,
            "customer_index": customer_index,
        }
    )


@staff_member_required
def customers_list(request):
    search_query = request.GET.get("q", "").strip()

    customers = User.objects.filter(
        is_staff=False,
        is_superuser=False
    )

    #  BACKEND SEARCH
    if search_query:
        customers = customers.filter(
            Q(full_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )

    # ⬇ Latest first
    customers = customers.order_by("-created_at")

    #  Pagination
    paginator = Paginator(customers, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "adminpanel/customers/customers_list.html",
        {
            "page_obj": page_obj,
            "search_query": search_query
        }
    )

@staff_member_required
def block_user(request, user_id):
    user = get_object_or_404(
        User,
        id=user_id,
        is_staff=False,
        is_superuser=False
    )

    if request.method == "POST":
        user.is_blocked = True
        user.is_active = False   # IMPORTANT
        user.save()
        messages.success(request, f"{user.get_full_name()} has been blocked.")
        return redirect("adminpanel:customers_list")

    return redirect("adminpanel:customers_list")

@staff_member_required
def unblock_user(request, user_id):
    user = get_object_or_404(
        User,
        id=user_id,
        is_staff=False,
        is_superuser=False
    )

    if request.method == "POST":
        user.is_blocked = False
        user.is_active = True
        user.save()
        messages.success(request, f"{user.get_full_name()} has been unblocked.")
        return redirect("adminpanel:customers_list")

    return redirect("adminpanel:customers_list")


def logout_view(request):
    logout(request)
    return redirect("home:landing")


def add_user_page(request):
    form = UserForm()
    return render(request, 'adminpanel/customers/add_user.html', {'form': form})



@csrf_exempt
@require_POST
def add_user_api(request):
    try:
        form = UserForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return JsonResponse({"success": True, "message": "User created successfully"}, status=201)
        return JsonResponse({"success": False, "errors": form.errors}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "message": "Internal server error"}, status=500)


def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    return redirect('adminpanel:customers_list')  


def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        form = UserForm(request.POST, request.FILES, instance=user)

        if form.is_valid():
            form.save()
            messages.success(request, "User updated successfully")
            return redirect('adminpanel:customers_list')  # change to your listing page name

    else:
        form = UserForm(instance=user)

    return render(request, 'adminpanel/customers/edit_user.html', {
        'form': form,
        'user': user
    })









