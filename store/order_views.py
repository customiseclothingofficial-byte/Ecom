"""Order views: checkout, order detail, tracking, wallet, returns."""

import json
import logging

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.utils import timezone

from .models import (
    Order, OrderItem, OrderStatusHistory, Wallet, WalletTransaction,
    PersonalizationRequest, UserAddress, UPIPaymentMethod, ReturnRequest,
)
from .cart_utils import get_cart_items, get_cart_total, clear_cart, calculate_delivery_charges
from .razorpay_gateway import create_razorpay_order, verify_razorpay_payment
from accounts.email_utils import send_order_confirmation_email

import razorpay

logger = logging.getLogger(__name__)


@login_required
def checkout(request):
    """Unified checkout for standard and personalized items."""
    errors = []
    out_of_stock = []

    # Gather items from cart
    cart_items = get_cart_items(request)
    cart_total = get_cart_total(request)

    # Add personalized items to cart totals
    personalization_cart_total = Decimal('0.00')
    personalization_requests = []
    if request.user.is_authenticated:
        personalization_requests = PersonalizationRequest.objects.filter(
            user=request.user,
            status__in=['pending', 'admin_approved', 'order_accepted']
        ).select_related('product').order_by('-created_at')

        for req in personalization_requests:
            if req.is_in_cart:
                personalization_cart_total += req.cart_total_price

    combined_cart_total = {
        'total_price': cart_total['total_price'] + personalization_cart_total,
        'total_items': cart_total['total_items'] + sum(req.cart_quantity for req in personalization_requests if req.is_in_cart),
        'item_count': cart_total['item_count'] + sum(1 for req in personalization_requests if req.is_in_cart)
    }

    upi_payment_methods = UPIPaymentMethod.objects.filter(is_active=True).order_by('display_order')

    user_wallet = None
    if request.user.is_authenticated:
        user_wallet, created = Wallet.objects.get_or_create(user=request.user)

    saved_addresses = []
    default_address = None
    if request.user.is_authenticated:
        saved_addresses = UserAddress.objects.filter(user=request.user).order_by('-is_default', '-created_at')
        default_address = saved_addresses.filter(is_default=True).first()

    personalization_items = []
    personalization_total = Decimal('0.00')
    if request.user.is_authenticated:
        cart_product_ids = [item.product.id for item in cart_items]
        personalization_items = list(
            PersonalizationRequest.objects.filter(
                user=request.user,
                status='admin_approved'
            ).exclude(
                product_id__in=cart_product_ids
            ).select_related('product')
        )
        personalization_total = sum(item.product.price for item in personalization_items)

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        address_line1 = request.POST.get('address_line1', '').strip()
        address_line2 = request.POST.get('address_line2', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        postal_code = request.POST.get('postal_code', '').strip()
        phone = request.POST.get('phone', '').strip()
        payment_method = request.POST.get('payment_method', 'cod')
        upi_provider = request.POST.get('upi_provider', '')
        use_wallet = request.POST.get('use_wallet') == 'on'
        wallet_amount = Decimal(request.POST.get('wallet_amount', '0.00') or '0.00')

        required_fields = [full_name, address_line1, city, state, postal_code, phone]
        if not all(required_fields):
            errors.append('Please fill in all required fields.')

        total_amount = Decimal('0.00')
        for item in cart_items:
            product = item.product
            qty = item.quantity
            if product.stock < qty:
                out_of_stock.append(f"{product.name} (need {qty}, have {product.stock})")
            total_amount += item.total_price

        total_amount += personalization_cart_total

        delivery_info = calculate_delivery_charges(total_amount)
        total_amount += delivery_info['delivery_charge']

        if payment_method == 'cod':
            total_amount += Decimal('10.00')

        wallet_amount_to_use = Decimal('0.00')
        remaining_amount = total_amount
        final_payment_method = payment_method

        if use_wallet and request.user.is_authenticated and user_wallet:
            if wallet_amount > user_wallet.balance:
                errors.append(f'Insufficient wallet balance. Available: ₹{user_wallet.balance}')
            elif wallet_amount > total_amount:
                errors.append('Wallet amount cannot exceed total order amount.')
            else:
                wallet_amount_to_use = wallet_amount
                remaining_amount = total_amount - wallet_amount_to_use

                if remaining_amount == 0:
                    final_payment_method = 'wallet'
                else:
                    final_payment_method = 'wallet_partial'

        if out_of_stock:
            errors.append('Some items are out of stock. Please remove them or try later:')

        if errors:
            return render(request, 'store/checkout.html', {
                'cart_items': cart_items,
                'personalization_items': personalization_items,
                'personalization_total': personalization_total,
                'cart_total': combined_cart_total,
                'upi_payment_methods': upi_payment_methods,
                'user_wallet': user_wallet,
                'errors': errors,
                'out_of_stock': out_of_stock,
                'form': {
                    'full_name': full_name,
                    'address_line1': address_line1,
                    'address_line2': address_line2,
                    'city': city,
                    'state': state,
                    'postal_code': postal_code,
                    'phone': phone,
                    'payment_method': payment_method,
                }
            })

        initial_status = 'processing'
        if final_payment_method in ['online', 'wallet_partial']:
            initial_status = 'pending'

        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_key=None if request.user.is_authenticated else getattr(request, 'session', None) and request.session.session_key,
            full_name=full_name,
            address_line1=address_line1,
            address_line2=address_line2 or '',
            city=city,
            state=state,
            postal_code=postal_code,
            phone=phone,
            payment_method=final_payment_method,
            upi_provider=None,
            total_amount=total_amount,
            wallet_amount_used=wallet_amount_to_use,
            remaining_amount=remaining_amount,
            estimated_delivery_date=timezone.now().date() + timedelta(days=getattr(settings, 'ORDER_DELIVERY_DAYS', 5)),
            status=initial_status,
            razorpay_payment_status='pending',
        )

        # Save address for authenticated users
        if request.user.is_authenticated:
            existing_address = UserAddress.objects.filter(
                user=request.user,
                full_name=full_name,
                address_line1=address_line1,
                address_line2=address_line2 or '',
                city=city,
                state=state,
                postal_code=postal_code,
                phone=phone
            ).first()

            if not existing_address:
                UserAddress.objects.create(
                    user=request.user,
                    full_name=full_name,
                    address_line1=address_line1,
                    address_line2=address_line2 or '',
                    city=city,
                    state=state,
                    postal_code=postal_code,
                    phone=phone,
                    is_default=not UserAddress.objects.filter(user=request.user).exists()
                )

        # Create order items for cart items
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                product_name=item.product.name,
                unit_price=item.product.price,
                quantity=item.quantity,
                line_total=item.total_price,
                size=item.size,
                color=item.color,
            )

        # Create order items for personalized items in cart
        personalized_items_in_cart = []
        if request.user.is_authenticated:
            personalized_items_in_cart = PersonalizationRequest.objects.filter(
                user=request.user,
                status='order_accepted',
                cart_quantity__gt=0
            )
            for req in personalized_items_in_cart:
                OrderItem.objects.create(
                    order=order,
                    product=req.product,
                    product_name=req.product.name,
                    unit_price=req.product.price,
                    quantity=req.cart_quantity,
                    line_total=req.cart_total_price,
                    size=req.size,
                    color=req.color,
                    personalization=req,
                )

        is_online_payment = (
            final_payment_method in ['online', 'wallet_partial'] and remaining_amount > 0
        )

        if not is_online_payment:
            for item in cart_items:
                item.product.stock = max(0, item.product.stock - item.quantity)
                item.product.save(update_fields=['stock'])
            if request.user.is_authenticated:
                for req in personalized_items_in_cart:
                    req.product.stock = max(0, req.product.stock - req.cart_quantity)
                    req.product.save(update_fields=['stock'])
                    req.cart_quantity = 0
                    req.save(update_fields=['cart_quantity'])

        if wallet_amount_to_use > 0 and user_wallet:
            user_wallet.deduct_money(
                wallet_amount_to_use,
                f"Payment for Order #{order.id}"
            )

        if is_online_payment:
            try:
                razorpay_response = create_razorpay_order(
                    order_id=order.id,
                    amount=remaining_amount
                )

                if razorpay_response.get('success'):
                    order.razorpay_order_id = razorpay_response['razorpay_order_id']
                    order.save()

                    if not (request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true'):
                        return render(request, 'store/razorpay_payment.html', {
                            'order': order,
                            'razorpay_order_id': razorpay_response['razorpay_order_id'],
                            'razorpay_key_id': razorpay_response['key_id'],
                            'amount': razorpay_response['amount'],
                            'currency': razorpay_response['currency'],
                            'company_name': getattr(settings, 'RAZORPAY_COMPANY_NAME', 'Customise Clothing'),
                            'company_logo': getattr(settings, 'RAZORPAY_COMPANY_LOGO', ''),
                            'theme_color': getattr(settings, 'RAZORPAY_THEME_COLOR', '#6366f1'),
                        })

                    return JsonResponse({
                        'success': True,
                        'payment_required': True,
                        'razorpay_order_id': razorpay_response['razorpay_order_id'],
                        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                        'amount_paise': int(remaining_amount * 100),
                        'currency': 'INR',
                        'order_id': order.id,
                        'callback_url': request.build_absolute_uri(reverse('store:payment_callback')),
                        'prefill': {
                            'name': order.full_name,
                            'email': order.user.email if order.user else '',
                            'contact': order.phone
                        }
                    })
                else:
                    raise ValueError(razorpay_response.get('error', 'Failed to create Razorpay order.'))
            except Exception as e:
                messages.error(request, f'Payment gateway error: {str(e)}')
                order.status = 'cancelled'
                order.razorpay_payment_status = 'failed'
                order.save()
                return redirect('store:checkout')

        clear_cart(request)

        if order.user and order.user.email:
            send_order_confirmation_email(order)

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true':
            return JsonResponse({
                'success': True,
                'payment_required': False,
                'order_id': order.id,
            })

        return render(request, 'store/order_success.html', {'order': order})

    # GET: show checkout form
    regular_cart_items = cart_items
    personalized_cart_items = []

    if request.user.is_authenticated:
        personalized_cart_items = PersonalizationRequest.objects.filter(
            user=request.user,
            status='order_accepted',
            cart_quantity__gt=0
        ).select_related('product', 'size', 'color')

    delivery_info = calculate_delivery_charges(combined_cart_total['total_price'])

    return render(request, 'store/checkout.html', {
        'cart_items': cart_items,
        'regular_cart_items': regular_cart_items,
        'personalized_cart_items': personalized_cart_items,
        'personalization_items': personalization_items,
        'cart_total': combined_cart_total,
        'delivery_info': delivery_info,
        'user_wallet': user_wallet,
        'saved_addresses': saved_addresses,
        'default_address': default_address,
    })


@login_required
def order_detail(request, order_id):
    """Display detailed order information."""
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related('status_history__changed_by'),
        id=order_id,
        user=request.user
    )
    personalization_images = order.get_personalization_images()
    status_history = order.status_history.all().order_by('-created_at')

    return render(request, 'store/order_detail.html', {
        'order': order,
        'personalization_images': personalization_images,
        'status_history': status_history,
    })


@login_required
def track_order(request, order_id):
    """Display order tracking information."""
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related('status_history__changed_by', 'items__product'),
        id=order_id,
        user=request.user
    )
    status_history = order.status_history.all().order_by('created_at')

    return render(request, 'store/track_order.html', {
        'order': order,
        'status_history': status_history,
    })


@login_required
def wallet_view(request):
    """Display user's wallet balance and transaction history."""
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.all()[:20]

    return render(request, 'store/wallet.html', {
        'wallet': wallet,
        'transactions': transactions
    })


@login_required
def return_order(request, order_id):
    """Legacy return endpoint — redirects to the proper ReturnRequest flow."""
    return redirect('store:request_return', order_id=order_id)


@login_required
def request_return(request, order_id):
    """Submit a return request for an order."""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if not order.can_be_returned:
        messages.error(request, 'This order cannot be returned.')
        return redirect('store:order_detail', order_id=order.id)

    if request.method == 'POST':
        reason = request.POST.get('reason')
        description = request.POST.get('description', '')

        if not reason:
            messages.error(request, 'Please select a reason for return.')
            return redirect('store:order_detail', order_id=order.id)

        try:
            return_request = ReturnRequest.objects.create(
                order=order,
                user=request.user,
                reason=reason,
                description=description
            )

            messages.success(request, 'Return request submitted successfully. You will be notified once it is reviewed by our team.')
            return redirect('store:order_detail', order_id=order.id)

        except Exception as e:
            messages.error(request, f'Error submitting return request: {str(e)}')
            return redirect('store:order_detail', order_id=order.id)

    return render(request, 'store/return_request.html', {
        'order': order,
        'return_reasons': ReturnRequest.RETURN_REASON_CHOICES
    })


@login_required
def return_status(request, order_id):
    """View return request status."""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if not hasattr(order, 'return_request'):
        messages.error(request, 'No return request found for this order.')
        return redirect('store:order_detail', order_id=order.id)

    return render(request, 'store/return_status.html', {
        'order': order,
        'return_request': order.return_request
    })


# ─── Payment views ──────────────────────────────────────────────

@login_required
def razorpay_payment_callback(request):
    """Handle Razorpay payment callback."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            razorpay_order_id = data.get('razorpay_order_id', '')
            razorpay_payment_id = data.get('razorpay_payment_id', '')
            razorpay_signature = data.get('razorpay_signature', '')
            order_id = data.get('order_id', '')

            if not order_id:
                return JsonResponse({'success': False, 'error': 'Invalid order ID'})

            order = Order.objects.get(id=order_id, user=request.user)

            is_verified = verify_razorpay_payment(
                razorpay_order_id,
                razorpay_payment_id,
                razorpay_signature
            )

            if is_verified:
                order.razorpay_payment_id = razorpay_payment_id
                order.razorpay_signature = razorpay_signature
                order.razorpay_payment_status = 'success'
                order.status = 'processing'
                order.save()

                OrderStatusHistory.objects.create(
                    order=order,
                    old_status='pending',
                    new_status='processing',
                    note=f'Razorpay payment confirmed. Payment ID: {razorpay_payment_id}',
                    changed_by=order.user,
                )

                for oi in order.items.all():
                    if oi.product:
                        oi.product.stock = max(0, oi.product.stock - oi.quantity)
                        oi.product.save(update_fields=['stock'])
                    if oi.personalization:
                        oi.personalization.cart_quantity = 0
                        oi.personalization.save(update_fields=['cart_quantity'])

                clear_cart(request)

                if order.user and order.user.email:
                    send_order_confirmation_email(order)

                return JsonResponse({
                    'success': True,
                    'message': f'Payment successful! Your order #{order.id} has been confirmed.',
                    'redirect_url': f'/store/order-detail/{order.id}/'
                })
            else:
                order.razorpay_payment_id = razorpay_payment_id
                order.razorpay_payment_status = 'failed'
                order.status = 'cancelled'
                order.save()
                return JsonResponse({
                    'success': False,
                    'error': 'Payment verification failed. Please contact support if amount was deducted.'
                })

        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Order not found'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid request data'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    # GET request
    order_id = request.GET.get('order_id')
    status = request.GET.get('status', 'failed')

    if order_id:
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            if status == 'success' and order.razorpay_payment_status == 'success':
                messages.success(request, f'Payment successful! Your order #{order.id} has been confirmed.')
                return render(request, 'store/order_success.html', {'order': order})
            else:
                messages.error(request, 'Payment was cancelled or failed. Please try again.')
                return redirect('store:checkout')
        except Order.DoesNotExist:
            pass

    messages.error(request, 'Invalid payment request.')
    return redirect('store:checkout')


@login_required
def payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status != 'pending' and order.status != 'processing':
        messages.error(request, "This order is not pending payment.")
        return redirect('store:home')

    if order.status in ('processing', 'shipped', 'delivered'):
        return render(request, 'store/order_success.html', {'order': order})

    amount_to_pay = order.remaining_amount
    if amount_to_pay <= 0:
        return render(request, 'store/order_success.html', {'order': order})

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    payment_data = {
        'amount': int(amount_to_pay * 100),
        'currency': 'INR',
        'receipt': f'order_{order.id}',
        'payment_capture': 1
    }

    try:
        razorpay_order = client.order.create(data=payment_data)
        order.razorpay_order_id = razorpay_order['id']
        order.save()

        context = {
            'order': order,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'amount': amount_to_pay,
            'amount_paise': int(amount_to_pay * 100),
            'currency': 'INR',
            'callback_url': request.build_absolute_uri(reverse('store:payment_callback')),
        }
        return render(request, 'store/payment.html', context)
    except Exception as e:
        messages.error(request, f"Error creating payment: {str(e)}")
        return redirect('store:order_detail', order_id=order.id)


from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import user_passes_test


@csrf_exempt
def payment_callback(request):
    if request.method == "POST":
        try:
            payment_id = request.POST.get('razorpay_payment_id', '')
            razorpay_order_id = request.POST.get('razorpay_order_id', '')
            signature = request.POST.get('razorpay_signature', '')

            order = Order.objects.get(razorpay_order_id=razorpay_order_id)

            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }

            try:
                result = client.utility.verify_payment_signature(params_dict)

                order.razorpay_payment_id = payment_id
                order.razorpay_signature = signature
                order.razorpay_payment_status = 'success'
                order.status = 'processing'
                order.save()

                OrderStatusHistory.objects.create(
                    order=order,
                    old_status='pending',
                    new_status='processing',
                    note=f'Payment confirmed via Razorpay. Payment ID: {payment_id}',
                    changed_by=order.user,
                )

                for oi in order.items.all():
                    if oi.product:
                        oi.product.stock = max(0, oi.product.stock - oi.quantity)
                        oi.product.save(update_fields=['stock'])
                    if oi.personalization:
                        oi.personalization.cart_quantity = 0
                        oi.personalization.save(update_fields=['cart_quantity'])

                if order.user:
                    from .models import Cart
                    try:
                        cart = Cart.objects.get(user=order.user)
                        cart.items.all().delete()
                    except Cart.DoesNotExist:
                        pass

                if order.user and order.user.email:
                    send_order_confirmation_email(order)

                return render(request, 'store/order_success.html', {'order': order})
            except razorpay.errors.SignatureVerificationError:
                order.razorpay_payment_status = 'failed'
                order.status = 'cancelled'
                order.save()
                return render(request, 'store/payment_failed.html', {
                    'error': 'Payment signature verification failed. Please contact support if amount was deducted.',
                    'order': order,
                })

        except Order.DoesNotExist:
            return render(request, 'store/payment_failed.html', {'error': 'Order not found'})
        except Exception as e:
            return render(request, 'store/payment_failed.html', {'error': str(e)})

    return redirect('store:home')
