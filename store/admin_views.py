"""Admin views: dashboard, product/category CRUD, order management, return processing."""

import json
import logging

from datetime import datetime

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string

from .models import (
    Product, ProductImage, Category,
    Order, OrderStatusHistory, ReturnRequest, Size, Color,
    PersonalizationRequest,
)

logger = logging.getLogger(__name__)


# ─── Forms ──────────────────────────────────────────────────────

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'image', 'price', 'description', 'can_customize', 'sizes', 'external_buy_url', 'external_platform_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all().order_by('parent__name', 'name')

        def make_label(cat: Category):
            return f"{cat.parent.name} › {cat.name}" if cat.parent else cat.name

        self.fields['category'].label_from_instance = make_label
        if 'sizes' in self.fields:
            self.fields['sizes'].queryset = Size.objects.all().order_by('display_order', 'code')


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'parent', 'image', 'display_style']


# ─── Dashboard ──────────────────────────────────────────────────

@user_passes_test(lambda u: u.is_staff)
def shop_admin_dashboard(request):
    products = Product.objects.all()
    personalization_requests = PersonalizationRequest.objects.select_related('user', 'product').order_by('-created_at')
    categories = Category.objects.all()
    product_form = ProductForm()
    category_form = CategoryForm()
    return render(request, 'store/shop_admin_dashboard.html', {
        'products': products,
        'personalization_requests': personalization_requests,
        'categories': categories,
        'product_form': product_form,
        'category_form': category_form,
    })


# ─── Product CRUD ───────────────────────────────────────────────

@user_passes_test(lambda u: u.is_staff)
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
    return redirect('store:shop_admin_dashboard')


@user_passes_test(lambda u: u.is_staff)
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('store:shop_admin_dashboard')
    else:
        form = ProductForm(instance=product)
    return render(request, 'store/edit_product.html', {'form': form, 'product': product})


@user_passes_test(lambda u: u.is_staff)
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        product.delete()
        return redirect('store:shop_admin_dashboard')
    return render(request, 'store/delete_product.html', {'product': product})


# ─── Category CRUD ──────────────────────────────────────────────

@user_passes_test(lambda u: u.is_staff)
def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
    return redirect('store:shop_admin_dashboard')


@user_passes_test(lambda u: u.is_staff)
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            return redirect('store:shop_admin_dashboard')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'store/edit_category.html', {'form': form, 'category': category})


@user_passes_test(lambda u: u.is_staff)
def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        category.delete()
        return redirect('store:shop_admin_dashboard')
    return render(request, 'store/delete_category.html', {'category': category})


# ─── Admin Order Management ─────────────────────────────────────

@user_passes_test(lambda u: u.is_staff)
def admin_orders_list(request):
    """Admin view: List all orders with filters."""
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_query = request.GET.get('q', '')

    orders = Order.objects.all().select_related('user').prefetch_related('items__product', 'status_history').order_by('-created_at')

    if status_filter:
        orders = orders.filter(status=status_filter)

    if date_from:
        try:
            orders = orders.filter(created_at__date__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass

    if date_to:
        try:
            orders = orders.filter(created_at__date__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass

    if search_query:
        orders = orders.filter(
            Q(id__icontains=search_query) |
            Q(full_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(tracking_number__icontains=search_query)
        )

    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    processing_orders = Order.objects.filter(status='processing').count()
    shipped_orders = Order.objects.filter(status='shipped').count()
    delivered_orders = Order.objects.filter(status='delivered').count()
    cancelled_orders = Order.objects.filter(status='cancelled').count()

    total_revenue = Order.objects.exclude(status='cancelled').aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    return render(request, 'store/admin_orders.html', {
        'orders': orders,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
        'status_choices': Order.ORDER_STATUS_CHOICES,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'processing_orders': processing_orders,
        'shipped_orders': shipped_orders,
        'delivered_orders': delivered_orders,
        'cancelled_orders': cancelled_orders,
        'total_revenue': total_revenue,
    })


@user_passes_test(lambda u: u.is_staff)
def admin_order_detail(request, order_id):
    """Admin view: Detailed order view."""
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related(
            'items__product', 'items__size', 'items__color', 'items__personalization', 'status_history__changed_by'
        ),
        id=order_id
    )
    status_history = order.status_history.all().order_by('-created_at')

    return render(request, 'store/admin_order_detail.html', {
        'order': order,
        'status_history': status_history,
        'status_choices': Order.ORDER_STATUS_CHOICES,
        'personalization_images': order.get_personalization_images(),
    })


@user_passes_test(lambda u: u.is_staff)
def admin_update_order_status(request, order_id):
    """Admin view: Update order status with tracking info."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})

    order = get_object_or_404(Order, id=order_id)

    new_status = request.POST.get('status', '').strip()
    note = request.POST.get('note', '').strip()
    tracking_number = request.POST.get('tracking_number', '').strip()
    tracking_url = request.POST.get('tracking_url', '').strip()
    carrier_name = request.POST.get('carrier_name', '').strip()

    if not new_status:
        return JsonResponse({'success': False, 'error': 'Status is required'})

    valid_statuses = [s[0] for s in Order.ORDER_STATUS_CHOICES]
    if new_status not in valid_statuses:
        return JsonResponse({'success': False, 'error': f'Invalid status: {new_status}'})

    try:
        updated = order.update_status(
            new_status=new_status,
            user=request.user,
            note=note,
            tracking_number=tracking_number or None,
            tracking_url=tracking_url or None,
            carrier_name=carrier_name or None,
            send_email=True,
        )

        if updated:
            messages.success(request, f'Order #{order.id} updated to "{order.get_status_display()}".')
            return JsonResponse({
                'success': True,
                'message': f'Order #{order.id} status updated to {order.get_status_display()}',
                'new_status': new_status,
                'new_status_display': order.get_status_display(),
            })
        else:
            return JsonResponse({'success': False, 'error': 'Status unchanged (same as current).'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@user_passes_test(lambda u: u.is_staff)
def admin_return_requests(request):
    """Admin view: List and manage return requests."""
    returns = ReturnRequest.objects.select_related('order', 'user', 'order__user').order_by('-requested_at')
    status_filter = request.GET.get('status', '')
    if status_filter:
        returns = returns.filter(status=status_filter)

    return render(request, 'store/admin_return_requests.html', {
        'returns': returns,
        'status_filter': status_filter,
        'return_status_choices': ReturnRequest.RETURN_STATUS_CHOICES,
    })


@user_passes_test(lambda u: u.is_staff)
def admin_process_return(request, return_id):
    """Admin view: Approve or reject a return request."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})

    return_request = get_object_or_404(ReturnRequest, id=return_id)
    action = request.POST.get('action', '')
    admin_notes = request.POST.get('admin_notes', '')

    try:
        if action == 'approve':
            return_request.approve_return(admin_notes=admin_notes)
            messages.success(request, f'Return request #{return_request.id} approved. Refund added to wallet.')
        elif action == 'reject':
            return_request.reject_return(admin_notes=admin_notes)
            messages.warning(request, f'Return request #{return_request.id} rejected.')
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action'})

        return JsonResponse({'success': True, 'message': f'Return {action}ed successfully'})
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)})
