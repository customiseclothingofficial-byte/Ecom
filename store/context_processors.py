"""
Global context processors — ensures base.html always has
the variables it needs (categories nav, cart badge, contact info, etc.)
"""
import logging

from django.conf import settings

from store.models import Category
from store.cart_utils import get_cart_total

logger = logging.getLogger(__name__)


def global_context(request):
    """Inject all_categories, cart_total, and site settings into every template context."""
    try:
        all_categories = (
            Category.objects
            .filter(parent__isnull=True)
            .select_related()
            .order_by('name')
        )
    except Exception:
        all_categories = []

    try:
        cart_total = get_cart_total(request)
    except Exception:
        cart_total = {'total_items': 0, 'total_price': 0, 'item_count': 0}

    return {
        'all_categories': all_categories,
        'cart_total': cart_total,
        # Feature flag: public login/registration temporarily disabled
        'auth_enabled': getattr(settings, 'AUTH_ENABLED', True),
        # Company / contact info (replaces hardcoded values in templates)
        'site_company_name': getattr(settings, 'COMPANY_NAME', 'Customise Clothing'),
        'site_contact_phone': getattr(settings, 'CONTACT_PHONE', '+91 9114960778'),
        'site_contact_email': getattr(settings, 'CONTACT_EMAIL', 'customiseclothingofficial@gmail.com'),
        'site_support_email': getattr(settings, 'CONTACT_SUPPORT_EMAIL', 'help@customiseclothing.in'),
        'site_company_logo': getattr(settings, 'RAZORPAY_COMPANY_LOGO', ''),
        'site_theme_color': getattr(settings, 'RAZORPAY_THEME_COLOR', '#6366f1'),
        # Delivery config
        'site_free_delivery_threshold': getattr(settings, 'FREE_DELIVERY_THRESHOLD', '349.00'),
        'site_delivery_charge': getattr(settings, 'DELIVERY_CHARGE', '25.00'),
        # Fallback images
        'site_product_fallback_image': getattr(settings, 'DEFAULT_PRODUCT_FALLBACK_IMAGE', ''),
        'site_category_fallback_image': getattr(settings, 'DEFAULT_CATEGORY_FALLBACK_IMAGE', ''),
    }
