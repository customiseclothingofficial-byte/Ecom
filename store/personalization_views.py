"""Personalization views — simple flow:
User uploads design → Admin reviews & uploads final → User approves or rejects.
"""

import json
import logging

from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from .models import (
    Product, PersonalizationRequest,
    Size, Color, Cart, CartItem,
)
from accounts.email_utils import send_personalization_update_email

logger = logging.getLogger(__name__)


# ─── Forms ──────────────────────────────────────────────────────

class PersonalizationRequestForm(forms.ModelForm):
    class Meta:
        model = PersonalizationRequest
        fields = ['uploaded_image']


# ─── User Views ─────────────────────────────────────────────────

@login_required
def customize_product(request, product_id):
    """Customize a product — delegates to the full personalization flow."""
    return personalize_product(request, product_id)


def personalize_products(request):
    """Show personalization product categories."""
    customizable_products = Product.objects.filter(can_customize=True).select_related('category')

    categories_with_products = {}
    for product in customizable_products:
        category_name = product.category.name if product.category else 'General'
        if category_name not in categories_with_products:
            categories_with_products[category_name] = []
        categories_with_products[category_name].append(product)

    category_cards = []
    for category_name, products in categories_with_products.items():
        if products:
            sample_product = products[0]
            category_cards.append({
                'name': category_name,
                'image': sample_product.image.url if sample_product.image else getattr(settings, 'DEFAULT_PRODUCT_FALLBACK_IMAGE', ''),
                'product_count': len(products),
                'min_price': min(p.price for p in products),
                'max_price': max(p.price for p in products),
                'products': products
            })

    return render(request, 'store/personalize_products.html', {
        'category_cards': category_cards,
        'categories_with_products': categories_with_products
    })


def personalize_category_products(request, category_name):
    """Show all customizable products within a specific category."""
    products = Product.objects.filter(
        can_customize=True,
        category__name=category_name
    ).select_related('category')

    if not products.exists():
        products = Product.objects.filter(
            can_customize=True,
            category__name__iexact=category_name
        ).select_related('category')

    return render(request, 'store/personalize_category_products.html', {
        'category_name': category_name,
        'products': products
    })


@login_required
def personalize_product(request, product_id):
    """Simple personalization: select size/color + upload design image."""
    product = get_object_or_404(Product, id=product_id)
    available_sizes = list(product.sizes.all())

    if request.method == 'POST':
        form = PersonalizationRequestForm(request.POST, request.FILES)
        if form.is_valid():
            personalization = form.save(commit=False)
            personalization.user = request.user
            personalization.product = product

            # Save selected size
            selected_size_code = request.POST.get('selected_size')
            if selected_size_code:
                try:
                    personalization.size = Size.objects.get(code=selected_size_code)
                except Size.DoesNotExist:
                    pass

            # Save selected color
            selected_color_id = request.POST.get('selected_color')
            if selected_color_id:
                try:
                    personalization.color = Color.objects.get(id=selected_color_id)
                except Color.DoesNotExist:
                    pass

            personalization.save()
            return redirect('store:personalize_status', personalization_id=personalization.id)
    else:
        form = PersonalizationRequestForm()

    return render(request, 'store/personalize_product.html', {
        'product': product,
        'form': form,
        'available_sizes': available_sizes,
    })


@login_required
def personalize_status(request, personalization_id):
    """Show personalization request status and admin's design (if approved)."""
    personalization = get_object_or_404(
        PersonalizationRequest,
        id=personalization_id,
        user=request.user,
    )
    return render(request, 'store/personalize_status.html', {
        'personalization': personalization,
    })


# ─── AJAX Endpoints ─────────────────────────────────────────────

@login_required
def submit_personalization(request):
    """Submit personalization request via AJAX."""
    if request.method == 'POST':
        form = PersonalizationRequestForm(request.POST, request.FILES)
        if form.is_valid():
            personalization = form.save(commit=False)
            personalization.user = request.user
            product_id = request.POST.get('product_id')
            if not product_id or not Product.objects.filter(id=product_id).exists():
                return JsonResponse({'success': False, 'error': 'Invalid or missing product.'})
            personalization.product_id = product_id

            # Save size
            selected_size_code = request.POST.get('selected_size')
            if selected_size_code:
                try:
                    personalization.size = Size.objects.get(code=selected_size_code)
                except Size.DoesNotExist:
                    pass

            # Save color
            selected_color_id = request.POST.get('selected_color')
            if selected_color_id:
                try:
                    personalization.color = Color.objects.get(id=selected_color_id)
                except Color.DoesNotExist:
                    pass

            personalization.save()
            return JsonResponse({
                'success': True,
                'message': 'Design submitted! Our team will review it shortly.',
                'personalization_id': personalization.id,
            })
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def approve_personalization(request):
    """User approves admin-approved design → moves to cart."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            request_id = data.get('request_id')

            personalization = get_object_or_404(PersonalizationRequest, id=request_id, user=request.user)

            if personalization.status == 'admin_approved' and personalization.admin_final_image:
                personalization.status = 'order_accepted'
                personalization.cart_quantity = 1
                personalization.save()

                if personalization.user.email:
                    send_personalization_update_email(personalization, 'order_accepted')

                return JsonResponse({
                    'success': True,
                    'message': 'Design approved! Added to your cart.',
                    'personalization_id': personalization.id,
                    'product_price': float(personalization.product.price),
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Design not yet ready or not approved by admin.',
                })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def reject_personalization(request):
    """User rejects admin-approved design."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            request_id = data.get('request_id')

            personalization = get_object_or_404(PersonalizationRequest, id=request_id, user=request.user)

            if personalization.status == 'admin_approved':
                personalization.status = 'rejected'
                personalization.save()
                return JsonResponse({'success': True, 'message': 'Design rejected. You can upload a new one.'})
            else:
                return JsonResponse({'success': False, 'error': 'Cannot reject: design not in approved state.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def remove_personalization(request):
    """User removes a personalization request (only if pending)."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            request_id = data.get('request_id')
            personalization = get_object_or_404(PersonalizationRequest, id=request_id, user=request.user)

            if personalization.status == 'order_accepted':
                return JsonResponse({'success': False, 'error': 'Cannot remove: already in cart.'})

            personalization.delete()
            return JsonResponse({'success': True, 'message': 'Request removed.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def update_personalization_cart_quantity(request):
    """Update quantity of personalized item in cart."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            request_id = data.get('request_id')
            quantity = int(data.get('quantity', 0))

            personalization = get_object_or_404(PersonalizationRequest, id=request_id, user=request.user)

            if personalization.status != 'order_accepted':
                return JsonResponse({'success': False, 'error': 'Item not in cart'})

            if quantity < 0:
                return JsonResponse({'success': False, 'error': 'Quantity must be non-negative'})

            if quantity > personalization.product.stock:
                return JsonResponse({'success': False, 'error': f'Insufficient stock. Available: {personalization.product.stock}'})

            personalization.cart_quantity = quantity
            personalization.save()

            from .cart_utils import get_cart_total
            from decimal import Decimal
            cart_total = get_cart_total(request)

            personalized_total = Decimal('0.00')
            personalized_count = 0
            if request.user.is_authenticated:
                for req in PersonalizationRequest.objects.filter(user=request.user, status='order_accepted', cart_quantity__gt=0):
                    personalized_total += req.cart_total_price
                    personalized_count += req.cart_quantity

            combined_cart_total = {
                'total_price': float(cart_total['total_price'] + personalized_total),
                'total_items': cart_total['total_items'] + personalized_count,
                'item_count': cart_total['item_count'] + len(list(PersonalizationRequest.objects.filter(user=request.user, status='order_accepted', cart_quantity__gt=0)))
            }

            return JsonResponse({'success': True, 'message': 'Quantity updated', 'quantity': quantity, 'total_price': float(personalization.cart_total_price), 'combined_cart_total': combined_cart_total})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def remove_personalization_from_cart(request):
    """Remove personalized item from cart."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            request_id = data.get('request_id')
            personalization = get_object_or_404(PersonalizationRequest, id=request_id, user=request.user)

            if personalization.status != 'order_accepted':
                return JsonResponse({'success': False, 'error': 'Item not in cart'})

            personalization.cart_quantity = 0
            personalization.save()

            from .cart_utils import get_cart_total
            from decimal import Decimal
            cart_total = get_cart_total(request)

            personalized_total = Decimal('0.00')
            personalized_count = 0
            for req in PersonalizationRequest.objects.filter(user=request.user, status='order_accepted', cart_quantity__gt=0):
                personalized_total += req.cart_total_price
                personalized_count += req.cart_quantity

            combined_cart_total = {
                'total_price': float(cart_total['total_price'] + personalized_total),
                'total_items': cart_total['total_items'] + personalized_count,
                'item_count': cart_total['item_count'] + len(list(PersonalizationRequest.objects.filter(user=request.user, status='order_accepted', cart_quantity__gt=0)))
            }

            return JsonResponse({'success': True, 'message': 'Item removed', 'combined_cart_total': combined_cart_total})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


# ─── Admin Views ────────────────────────────────────────────────

@user_passes_test(lambda u: u.is_staff)
def admin_accept_order(request):
    """Admin accepts user order for a personalization."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            request_id = data.get('request_id')
            personalization = get_object_or_404(PersonalizationRequest, id=request_id)

            if personalization.status != 'admin_approved':
                return JsonResponse({'success': False, 'error': 'Not in admin_approved state.'})

            cart, _ = Cart.objects.get_or_create(user=personalization.user)
            item, created = CartItem.objects.get_or_create(cart=cart, product=personalization.product, defaults={'quantity': 1})
            if not created:
                item.quantity += 1
                item.save()

            personalization.status = 'order_accepted'
            personalization.save()

            return JsonResponse({'success': True, 'message': "Order accepted and added to user's cart."})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@user_passes_test(lambda u: u.is_staff)
def admin_approve_personalization(request):
    """Admin approves personalization: uploads final design + notes."""
    if request.method == 'POST':
        try:
            request_id = request.POST.get('request_id')
            final_image = request.FILES.get('final_image')
            notes = request.POST.get('notes', '')

            personalization = get_object_or_404(PersonalizationRequest, id=request_id)

            if final_image:
                personalization.admin_final_image = final_image
                personalization.admin_notes = notes
                personalization.status = 'admin_approved'
                personalization.save()

                if personalization.user.email:
                    send_personalization_update_email(personalization, 'admin_approved')

                return JsonResponse({'success': True, 'message': 'Design approved! Customer will be notified.'})
            else:
                return JsonResponse({'success': False, 'error': 'Please upload a final design image.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@user_passes_test(lambda u: u.is_staff)
def admin_reject_personalization(request):
    """Admin rejects personalization request."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            request_id = data.get('request_id')

            personalization = get_object_or_404(PersonalizationRequest, id=request_id)
            personalization.status = 'rejected'
            personalization.save()

            if personalization.user.email:
                send_personalization_update_email(personalization, 'rejected')

            return JsonResponse({'success': True, 'message': 'Request rejected.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@user_passes_test(lambda u: u.is_staff)
def update_admin_notes(request):
    """Update admin notes for personalization request."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            request_id = data.get('request_id')
            notes = data.get('notes', '')

            personalization = get_object_or_404(PersonalizationRequest, id=request_id)
            personalization.admin_notes = notes
            personalization.save()

            return JsonResponse({'success': True, 'message': 'Notes updated.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})
