"""
Views re-export — all view functions are now in domain-specific modules.

This file exists for backward compatibility with any code that imports from
'store.views' directly (templates, existing URL patterns, etc.).

New code should import from the specific module:
    from store.product_views import home, category_page
    from store.order_views import checkout, order_detail
    from store.personalization_views import personalize_product
    from store.admin_views import shop_admin_dashboard
"""

# ── Product catalog views ──
from store.product_views import (
    home,
    category_page,
    plain_shirt, cap, bottle, mug, god_goddess, oversize,
    polo_shirt, regular_thin, regular_thick, combo, couple,
    women_specific, personal_customise, sports, regional_preference,
    product_detail, all_products,
    personal_customize_products,
    refund_cancellation_policy, shipping_policy,
    terms_conditions, privacy_policy,
)

# ── Personalization views ──
from store.personalization_views import (
    customize_product,
    personalize_products,
    personalize_category_products,
    PersonalizationRequestForm,
    personalize_product,
    personalize_status,
    submit_personalization,
    approve_personalization,
    reject_personalization,
    remove_personalization,
    update_personalization_cart_quantity,
    remove_personalization_from_cart,
    admin_accept_order,
    admin_approve_personalization,
    admin_reject_personalization,
    update_admin_notes,
)

# ── Order & payment views ──
from store.order_views import (
    checkout,
    order_detail,
    track_order,
    wallet_view,
    return_order,
    request_return,
    return_status,
    razorpay_payment_callback,
    payment,
    payment_callback,
)

# ── Admin views ──
from store.admin_views import (
    ProductForm,
    CategoryForm,
    shop_admin_dashboard,
    add_product,
    edit_product,
    delete_product,
    add_category,
    edit_category,
    delete_category,
    admin_orders_list,
    admin_order_detail,
    admin_update_order_status,
    admin_return_requests,
    admin_process_return,
)

# Legacy alias — the old views.py had a `cart` function that just rendered a template.
def cart(request):
    """Legacy cart page view (now handled by cart_views.cart_page)."""
    from django.shortcuts import render as _render
    return _render(request, 'store/cart.html')
