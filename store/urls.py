from django.urls import path
from . import cart_views
from . import product_views
from . import personalization_views
from . import order_views
from . import admin_views

app_name = 'store'

urlpatterns = [
    # ── Product catalog ──
    path('', product_views.home, name='home'),
    path('plain-shirt/', product_views.plain_shirt, name='plain_shirt'),
    path('cap/', product_views.cap, name='cap'),
    path('bottle/', product_views.bottle, name='bottle'),
    path('mug/', product_views.mug, name='mug'),
    path('god-goddess/', product_views.god_goddess, name='god_goddess'),
    path('oversize/', product_views.oversize, name='oversize'),
    path('polo-shirt/', product_views.polo_shirt, name='polo_shirt'),
    path('regular-thin/', product_views.regular_thin, name='regular_thin'),
    path('regular-thick/', product_views.regular_thick, name='regular_thick'),
    path('combo/', product_views.combo, name='combo'),
    path('couple/', product_views.couple, name='couple'),
    path('women-specific/', product_views.women_specific, name='women_specific'),
    path('personal-customise/', product_views.personal_customize_products, name='personal_customize_products'),
    path('sports/', product_views.sports, name='sports'),
    path('regional-preference/', product_views.regional_preference, name='regional_preference'),
    path('category/<int:category_id>/', product_views.category_page, name='category_page'),
    path('product/<int:product_id>/', product_views.product_detail, name='product_detail'),
    path('all-products/', product_views.all_products, name='all_products'),

    # ── Personalization ──
    path('personal-customise/<int:product_id>/', personalization_views.customize_product, name='customize_product'),
    path('personalize/', personalization_views.personalize_products, name='personalize_products'),
    path('personalize/category/<str:category_name>/', personalization_views.personalize_category_products, name='personalize_category_products'),
    path('personalize/<int:product_id>/', personalization_views.personalize_product, name='personalize_product'),
    path('personalize/status/<int:personalization_id>/', personalization_views.personalize_status, name='personalize_status'),
    path('personalize/submit/', personalization_views.submit_personalization, name='submit_personalization'),
    path('personalize/approve/', personalization_views.approve_personalization, name='approve_personalization'),
    path('personalize/reject/', personalization_views.reject_personalization, name='reject_personalization'),
    path('personalize/update-cart-quantity/', personalization_views.update_personalization_cart_quantity, name='update_personalization_cart_quantity'),
    path('personalize/remove-from-cart/', personalization_views.remove_personalization_from_cart, name='remove_personalization_from_cart'),
    path('personalize/remove/', personalization_views.remove_personalization, name='remove_personalization'),
    path('shopadmin/approve-personalization/', personalization_views.admin_approve_personalization, name='admin_approve_personalization'),
    path('shopadmin/reject-personalization/', personalization_views.admin_reject_personalization, name='admin_reject_personalization'),
    path('shopadmin/accept-order/', personalization_views.admin_accept_order, name='admin_accept_order'),
    path('shopadmin/update-notes/', personalization_views.update_admin_notes, name='update_admin_notes'),

    # ── Cart ──
    path('cart/', cart_views.cart_page, name='cart'),
    path('cart/add/', cart_views.add_to_cart_ajax, name='add_to_cart_ajax'),
    path('cart/update/', cart_views.update_cart_ajax, name='update_cart_ajax'),
    path('cart/remove/', cart_views.remove_from_cart_ajax, name='remove_from_cart_ajax'),
    path('cart/data/', cart_views.get_cart_data_ajax, name='get_cart_data_ajax'),
    path('cart/clear/', cart_views.clear_cart_ajax, name='clear_cart_ajax'),
    path('cart/count/', cart_views.cart_count, name='cart_count'),
    path('cart/validate-stock/', cart_views.validate_cart_stock, name='validate_cart_stock'),

    # ── Checkout & Payment ──
    path('checkout/', order_views.checkout, name='checkout'),
    path('payment/<int:order_id>/', order_views.payment, name='payment'),
    path('payment/callback/', order_views.payment_callback, name='payment_callback'),
    path('payment/razorpay-callback/', order_views.payment_callback, name='razorpay_callback'),

    # ── Orders ──
    path('wallet/', order_views.wallet_view, name='wallet'),
    path('return-order/<int:order_id>/', order_views.return_order, name='return_order'),
    path('track-order/<int:order_id>/', order_views.track_order, name='track_order'),
    path('order-detail/<int:order_id>/', order_views.order_detail, name='order_detail'),
    path('return-request/<int:order_id>/', order_views.request_return, name='request_return'),
    path('return-status/<int:order_id>/', order_views.return_status, name='return_status'),

    # ── Admin Dashboard ──
    path('shopadmin/', admin_views.shop_admin_dashboard, name='shop_admin_dashboard'),
    path('shopadmin/add-product/', admin_views.add_product, name='add_product'),
    path('shopadmin/edit-product/<int:product_id>/', admin_views.edit_product, name='edit_product'),
    path('shopadmin/delete-product/<int:product_id>/', admin_views.delete_product, name='delete_product'),
    path('shopadmin/add-category/', admin_views.add_category, name='add_category'),
    path('shopadmin/edit-category/<int:category_id>/', admin_views.edit_category, name='edit_category'),
    path('shopadmin/delete-category/<int:category_id>/', admin_views.delete_category, name='delete_category'),

    # ── Admin Orders ──
    path('shopadmin/orders/', admin_views.admin_orders_list, name='admin_orders_list'),
    path('shopadmin/orders/<int:order_id>/', admin_views.admin_order_detail, name='admin_order_detail'),
    path('shopadmin/orders/<int:order_id>/update-status/', admin_views.admin_update_order_status, name='admin_update_order_status'),
    path('shopadmin/returns/', admin_views.admin_return_requests, name='admin_return_requests'),
    path('shopadmin/returns/<int:return_id>/process/', admin_views.admin_process_return, name='admin_process_return'),

    # ── Policy pages ──
    path('refund-cancellation-policy/', product_views.refund_cancellation_policy, name='refund_cancellation_policy'),
    path('shipping-policy/', product_views.shipping_policy, name='shipping_policy'),
    path('terms-conditions/', product_views.terms_conditions, name='terms_conditions'),
    path('privacy-policy/', product_views.privacy_policy, name='privacy_policy'),
]
