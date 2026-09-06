from django.contrib import admin
from django import forms
from .models import Product, ProductImage, Category, Cart, CartItem, PersonalizationRequest, Order, OrderItem, Wallet, WalletTransaction, UPIPaymentMethod, ReturnRequest, Size, Color, UserAddress, OrderStatusHistory

class CategoryInline(admin.TabularInline):
    model = Category
    fk_name = 'parent'
    extra = 1
    fields = ('name', 'image', 'display_style')
    show_change_link = True

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'display_style')
    list_filter = ('parent', 'display_style')
    list_editable = ('display_style',)
    ordering = ('parent__name', 'name')
    fieldsets = (
        (None, {
            'fields': ('name', 'parent', 'image', 'display_style')
        }),
    )
    inlines = [CategoryInline]


class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order categories and display hierarchical labels
        self.fields['category'].queryset = Category.objects.all().order_by('parent__name', 'name')

        def make_label(cat: Category):
            return f"{cat.parent.name} > {cat.name}" if cat.parent else cat.name

        self.fields['category'].label_from_instance = make_label

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ('image', 'color', 'alt_text', 'display_order')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ('name', 'category', 'price', 'stock', 'can_customize')
    list_filter = ('category', 'can_customize')
    search_fields = ('name', 'description')
    fieldsets = (
        (None, {
            'fields': ('name', 'category', 'price', 'original_price', 'stock', 'description', 'can_customize')
        }),
        ('Main Card Image', {
            'fields': ('image',),
            'description': 'This is the main image shown on home and category pages.'
        }),
        ('Variants & Attributes', {
            'fields': ('sizes', 'colors'),
            'description': 'Select available sizes and colors for this product.'
        }),
        ('External Buy Link', {
            'fields': ('external_buy_url', 'external_platform_name'),
            'description': 'If set, the "Buy Now" button redirects to this external URL instead of adding to cart.',
            'classes': ('collapse',),
        }),
    )
    filter_horizontal = ('sizes', 'colors')
    inlines = [ProductImageInline]

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'color', 'image_preview', 'display_order')
    list_filter = ('product', 'color')
    
    def image_preview(self, obj):
        if obj.image:
            from django.utils.html import format_html
            return format_html('<img src="{}" style="width: 50px; height: auto;" />', obj.image.url)
        return "-"

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('total_price',)

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user', 'session_key', 'total_items', 'total_price', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'session_key')
    readonly_fields = ('total_items', 'total_price', 'created_at', 'updated_at')
    inlines = [CartItemInline]
    
    fieldsets = (
        ('Cart Information', {
            'fields': ('user', 'session_key')
        }),
        ('Summary', {
            'fields': ('total_items', 'total_price')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'size', 'color', 'quantity', 'total_price', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('cart__user__username', 'product__name')
    readonly_fields = ('total_price', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Item Information', {
            'fields': ('cart', 'product', 'size', 'color', 'quantity')
        }),
        ('Pricing', {
            'fields': ('total_price',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('code', 'display_order')
    ordering = ('display_order', 'code')

@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'hex_code', 'display_order')
    ordering = ('display_order', 'name')

@admin.register(PersonalizationRequest)
class PersonalizationRequestAdmin(admin.ModelAdmin):
    list_display = (
        'user_display', 'product', 'size', 'color', 'status', 'created_at', 'updated_at'
    )
    list_filter = ('status', 'product', 'created_at')
    search_fields = ('user__username', 'product__name')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Request Info', {
            'fields': ('user', 'product', 'size', 'color', 'uploaded_image', 'status')
        }),
        ('Admin Response', {
            'fields': ('admin_final_image', 'admin_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_display(self, obj):
        return obj.user.username if obj.user else '-'
    user_display.short_description = 'User'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('line_total',)


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ('old_status', 'new_status', 'note', 'changed_by', 'tracking_number', 'carrier_name', 'created_at')
    can_delete = False


class WalletTransactionInline(admin.TabularInline):
    model = WalletTransaction
    extra = 0
    readonly_fields = ('transaction_type', 'amount', 'description', 'balance_after', 'created_at')
    can_delete = False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [WalletTransactionInline]


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet_user', 'transaction_type', 'amount', 'balance_after', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('wallet__user__username', 'description')
    readonly_fields = ('created_at',)
    
    def wallet_user(self, obj):
        return obj.wallet.user.username
    wallet_user.short_description = 'User'


def approve_return_requests(modeladmin, request, queryset):
    """Admin action to approve return requests and process refunds"""
    from accounts.email_utils import send_email
    
    approved = 0
    for return_request in queryset:
        if return_request.status == 'pending':
            try:
                return_request.approve_return("Approved by admin")
                approved += 1
                
                # Send notification email to customer
                if return_request.user.email:
                    subject = f"Return Request Approved - Order #{return_request.order.id}"
                    message = f"""Dear {return_request.user.username},

Your return request for Order #{return_request.order.id} has been approved.

Refund Amount: ₹{return_request.refund_amount}
The refund has been added to your wallet.

Thank you for shopping with us!

Best regards,
Customize Clothing Team"""
                    
                    send_email(return_request.user.email, subject, message)
                    
            except Exception as e:
                modeladmin.message_user(request, f"Error processing return request #{return_request.id}: {str(e)}", level='ERROR')
    
    if approved > 0:
        modeladmin.message_user(request, f"Successfully approved {approved} return request(s) and processed refunds to wallets.")
    else:
        modeladmin.message_user(request, "No return requests were approved. Only pending requests can be approved.", level='WARNING')

approve_return_requests.short_description = "Approve selected return requests and process refunds"


def reject_return_requests(modeladmin, request, queryset):
    """Admin action to reject return requests"""
    from accounts.email_utils import send_email
    
    rejected = 0
    for return_request in queryset:
        if return_request.status == 'pending':
            try:
                return_request.reject_return("Rejected by admin - does not meet return policy criteria")
                rejected += 1
                
                # Send notification email to customer
                if return_request.user.email:
                    subject = f"Return Request Update - Order #{return_request.order.id}"
                    message = f"""Dear {return_request.user.username},

We have reviewed your return request for Order #{return_request.order.id}.

Unfortunately, we cannot approve this return request as it does not meet our return policy criteria.

If you have any questions, please contact our customer support.

Best regards,
Customize Clothing Team"""
                    
                    send_email(return_request.user.email, subject, message)
                    
            except Exception as e:
                modeladmin.message_user(request, f"Error rejecting return request #{return_request.id}: {str(e)}", level='ERROR')
    
    if rejected > 0:
        modeladmin.message_user(request, f"Successfully rejected {rejected} return request(s).")
    else:
        modeladmin.message_user(request, "No return requests were rejected. Only pending requests can be rejected.", level='WARNING')

reject_return_requests.short_description = "Reject selected return requests"


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ('order', 'user', 'reason', 'status', 'refund_amount', 'requested_at', 'completed_at')
    list_filter = ('status', 'reason', 'requested_at')
    search_fields = ('order__id', 'user__username', 'description')
    readonly_fields = ('requested_at', 'approved_at', 'completed_at')
    actions = [approve_return_requests, reject_return_requests]
    
    fieldsets = (
        ('Return Request Information', {
            'fields': ('order', 'user', 'reason', 'description', 'status')
        }),
        ('Refund Details', {
            'fields': ('refund_amount', 'admin_notes')
        }),
        ('Timestamps', {
            'fields': ('requested_at', 'approved_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )



def confirm_pending_orders(modeladmin, request, queryset):
    """Admin action to confirm pending orders and move them to processing"""
    updated = 0
    for order in queryset:
        if order.status == 'pending':
            order.update_status('processing', user=request.user, note='Payment confirmed by admin')
            updated += 1
    
    if updated > 0:
        modeladmin.message_user(request, f"Successfully confirmed {updated} order(s). They are now in processing status.")
    else:
        modeladmin.message_user(request, "No pending orders were found to confirm.", level='WARNING')

confirm_pending_orders.short_description = "Confirm selected pending orders (pending → processing)"


def mark_orders_as_shipped(modeladmin, request, queryset):
    """Admin action to mark orders as shipped with audit trail"""
    updated = 0
    for order in queryset:
        if order.status == 'processing':
            order.update_status('shipped', user=request.user, note='Marked as shipped by admin')
            updated += 1
    
    if updated > 0:
        modeladmin.message_user(request, f"Successfully marked {updated} order(s) as shipped.")
    else:
        modeladmin.message_user(request, "No orders were updated. Only processing orders can be marked as shipped.", level='WARNING')

mark_orders_as_shipped.short_description = "Mark selected orders as shipped"


def mark_orders_as_delivered(modeladmin, request, queryset):
    """Admin action to mark orders as delivered with audit trail"""
    updated = 0
    for order in queryset:
        if order.status == 'shipped':
            order.update_status('delivered', user=request.user, note='Marked as delivered by admin')
            updated += 1
    
    if updated > 0:
        modeladmin.message_user(request, f"Successfully marked {updated} order(s) as delivered.")
    else:
        modeladmin.message_user(request, "No orders were updated. Only shipped orders can be marked as delivered.", level='WARNING')

mark_orders_as_delivered.short_description = "Mark selected orders as delivered"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'full_name', 'status', 'total_amount', 'wallet_amount_used', 'remaining_amount', 'is_returned', 'estimated_delivery_date', 'created_at')
    list_filter = ('status', 'estimated_delivery_date', 'created_at', 'payment_method', 'is_returned')
    search_fields = ('id', 'user__username', 'full_name', 'phone', 'tracking_number')
    readonly_fields = ('created_at', 'updated_at', 'shipped_at', 'delivered_at')
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    actions = [confirm_pending_orders, mark_orders_as_shipped, mark_orders_as_delivered]

    fieldsets = (
        ('Customer', {
            'fields': ('user', 'session_key', 'full_name', 'phone')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'postal_code')
        }),
        ('Payment & Delivery', {
            'fields': ('payment_method', 'upi_provider', 'total_amount', 'wallet_amount_used', 'remaining_amount', 'estimated_delivery_date')
        }),
        ('Razorpay Details', {
            'fields': ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_payment_status', 'razorpay_signature'),
            'classes': ('collapse',),
        }),
        ('Order Status & Tracking', {
            'fields': ('status', 'tracking_number', 'tracking_url', 'shipped_at', 'delivered_at')
        }),
        ('Return Information', {
            'fields': ('is_returned', 'return_reason', 'returned_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_name', 'size', 'color', 'unit_price', 'quantity', 'line_total')
    search_fields = ('order__id', 'product_name')


@admin.register(UPIPaymentMethod)
class UPIPaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'upi_id', 'is_active', 'display_order')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code', 'upi_id')
    list_editable = ('is_active', 'display_order')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'upi_id')
        }),
        ('Media', {
            'fields': ('logo', 'qr_code')
        }),
        ('Settings', {
            'fields': ('is_active', 'display_order')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'city', 'state', 'postal_code', 'is_default', 'created_at')
    list_filter = ('is_default', 'state', 'created_at')
    search_fields = ('user__username', 'full_name', 'phone', 'city')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Customer', {
            'fields': ('user', 'full_name', 'phone')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'postal_code')
        }),
        ('Settings', {
            'fields': ('is_default',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('order', 'old_status', 'new_status', 'changed_by', 'carrier_name', 'tracking_number', 'created_at')
    list_filter = ('new_status', 'created_at')
    search_fields = ('order__id', 'note', 'tracking_number')
    readonly_fields = ('order', 'old_status', 'new_status', 'note', 'changed_by', 'tracking_number', 'tracking_url', 'carrier_name', 'created_at')
