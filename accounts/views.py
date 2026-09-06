import random
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import RegistrationForm, CustomLoginForm, OTPVerifyForm
from .models import UserProfile
from store.models import Order
from store.cart_utils import merge_carts
from .email_utils import send_welcome_email, send_login_notification_email, send_otp_email


def _auth_disabled(request):
    """Redirect helper while public auth is temporarily disabled."""
    messages.info(request, 'Login and registration are temporarily unavailable. Please check back soon.')
    return redirect('store:home')


def register(request):
    # TEMP: public registration disabled — remove this guard to re-enable
    if not settings.AUTH_ENABLED:
        return _auth_disabled(request)
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Send welcome email if email is provided
            if user.email:
                send_welcome_email(user)
                messages.success(request, f'Account created successfully! A welcome email has been sent to {user.email}. Now you can login with OTP.')
            else:
                messages.success(request, 'Account created successfully! Now you can login with OTP.')
            
            return redirect('accounts:login')
    else:
        form = RegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def profile(request):
    """User profile page"""
    return render(request, 'accounts/profile.html', {
        'user': request.user
    })

@login_required
def my_orders(request):
    """Display user's order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'accounts/my_orders.html', {
        'orders': orders
    })

def custom_login(request):
    """Step 1: Enter identifier and send OTP"""
    # TEMP: public login disabled — remove this guard to re-enable
    if not settings.AUTH_ENABLED:
        return _auth_disabled(request)
    if request.method == 'POST':
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            login_field = form.cleaned_data['login_field']
            user = None
            
            # Try to find user by email first
            if '@' in login_field:
                user = User.objects.filter(email__iexact=login_field).first()
            # Try to find user by phone (UserProfile)
            elif login_field.isdigit():
                profile = UserProfile.objects.filter(phone=login_field).first()
                if profile:
                    user = profile.user
            # Try username directly
            else:
                user = User.objects.filter(username__iexact=login_field).first()
            
            if user:
                # Generate 6-digit OTP
                otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                profile, created = UserProfile.objects.get_or_create(user=user)
                profile.otp = otp
                profile.otp_expiry = timezone.now() + timedelta(minutes=10)
                profile.save()
                
                # Send OTP via email if email exists
                if user.email:
                    send_otp_email(user, otp)
                    messages.success(request, f'A verification code has been sent to {user.email}')
                    request.session['otp_user_id'] = user.id
                    return redirect('accounts:otp_verify')
                else:
                    messages.error(request, 'User found but no email address is associated with this account. Please contact support.')
            else:
                messages.error(request, 'No account found with those credentials.')
    else:
        form = CustomLoginForm()
    
    return render(request, 'registration/login.html', {'form': form})

def otp_verify(request):
    """Step 2: Verify OTP and login"""
    # TEMP: public login disabled — remove this guard to re-enable
    if not settings.AUTH_ENABLED:
        return _auth_disabled(request)
    user_id = request.session.get('otp_user_id')
    if not user_id:
        messages.error(request, 'Session expired. Please login again.')
        return redirect('accounts:login')
        
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data['otp']
            profile = user.profile
            
            if profile.otp == otp and profile.otp_expiry > timezone.now():
                # Save guest session key before login (auth_login rotates it)
                guest_session_key = request.session.session_key
                
                # Success - Login user
                auth_login(request, user)
                
                # Merge guest cart items into user's cart
                if guest_session_key:
                    try:
                        merge_carts(user, guest_session_key)
                    except Exception:
                        pass  # Don't block login on cart merge failure
                
                # Clear OTP
                profile.otp = None
                profile.otp_expiry = None
                profile.save()
                
                # Notification
                if user.email:
                    send_login_notification_email(user, request)
                
                # Clean session
                del request.session['otp_user_id']
                
                next_url = request.GET.get('next', '/')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid or expired OTP code.')
    else:
        form = OTPVerifyForm()
        
    return render(request, 'registration/otp_verify.html', {'form': form, 'user_email': user.email})
