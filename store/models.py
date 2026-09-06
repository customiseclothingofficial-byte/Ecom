from django.db import models, transaction
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone

# Create your models here.

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Category(TimeStampedModel):
    DISPLAY_STYLE_CHOICES = [
        ('circle', 'Circle'),
        ('box', 'Box'),
    ]
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    display_style = models.CharField(
        max_length=10,
        choices=DISPLAY_STYLE_CHOICES,
        default='box',
        help_text='Choose how this category is displayed on the home page.'
    )

    def __str__(self):
        return self.name

    @property
    def has_children(self):
        return self.children.exists()


class Size(models.Model):
    CODE_CHOICES = [
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL'),
    ]
    code = models.CharField(max_length=4, choices=CODE_CHOICES, unique=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'code']

    def __str__(self):
        return self.code

class Color(models.Model):
    name = models.CharField(max_length=50, unique=True, help_text="e.g., Mystic Black, Royal Blue")
    hex_code = models.CharField(max_length=7, help_text="Hex code, e.g., #000000")
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

class Product(TimeStampedModel):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True, help_text='Main product image')
    price = models.DecimalField(max_digits=8, decimal_places=2)
    original_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text='Original MRP for discount display')
    stock = models.PositiveIntegerField(default=0, help_text='Available inventory')
    description = models.TextField(blank=True, help_text='Detailed product description')
    can_customize = models.BooleanField(default=False, help_text='Can this product be personalized?')
    # If a product has one or more sizes assigned via the Size model, size selection will be shown on PDP
    # Keep empty to indicate no size selection required
    # Admin can configure which products have sizes

    # defined after Size class (string reference)
    # ManyToMany allows selecting any subset of standard sizes
    sizes = models.ManyToManyField('Size', blank=True, related_name='products')
    colors = models.ManyToManyField('Color', blank=True, related_name='products')

    # External platform redirect — when set, "Buy Now" redirects here instead of cart
    external_buy_url = models.URLField(blank=True, null=True, help_text='External platform URL to redirect for purchase')
    external_platform_name = models.CharField(max_length=100, blank=True, null=True, help_text='Platform name shown on button, e.g. Amazon, Flipkart')

    class Meta:
        indexes = [
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return self.name

class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    color = models.ForeignKey('Color', on_delete=models.SET_NULL, null=True, blank=True, related_name='color_images')
    image = models.ImageField(upload_to='products/gallery/')
    alt_text = models.CharField(max_length=150, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order']
        indexes = [
            models.Index(fields=['product', 'color']),
        ]

    def __str__(self):
        return f"Image for {self.product.name}"

class PersonalizationRequest(TimeStampedModel):
    """
    Simple personalization flow:
    User uploads design → status='pending'
    Admin reviews & uploads final image → status='admin_approved'
    User approves → status='order_accepted' (goes to cart)
    User rejects → status='rejected'
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('admin_approved', 'Admin Approved'),
        ('order_accepted', 'Order Accepted'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    uploaded_image = models.ImageField(upload_to='personalization_designs/', blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    admin_final_image = models.ImageField(upload_to='admin_final_designs/', blank=True, null=True)
    admin_notes = models.TextField(blank=True, null=True)
    cart_quantity = models.PositiveIntegerField(default=0, help_text='Quantity in cart for order_accepted items')
    size = models.ForeignKey('Size', on_delete=models.SET_NULL, null=True, blank=True, related_name='personalizations')
    color = models.ForeignKey('Color', on_delete=models.SET_NULL, null=True, blank=True, related_name='personalizations')

    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.status})"
    
    @property
    def is_in_cart(self):
        """Check if this personalization is in cart"""
        return self.status == 'order_accepted' and self.cart_quantity > 0
    
    @property
    def cart_total_price(self):
        """Get total price for cart quantity"""
        if self.is_in_cart:
            return self.product.price * self.cart_quantity
        return 0


class UserAddress(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=120)
    address_line1 = models.CharField(max_length=500)
    address_line2 = models.CharField(max_length=500, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    phone = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False, help_text='Default address for checkout')
    
    class Meta:
        verbose_name = 'User Address'
        verbose_name_plural = 'User Addresses'
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_default']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.full_name} ({self.city})"
    
    def save(self, *args, **kwargs):
        # Ensure only one default address per user
        if self.is_default:
            UserAddress.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class Cart(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    
    class Meta:
        # user and session_key are indexed automatically (FK / db_index via lookups)
        pass

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        return f"Guest Cart {self.session_key}"
    
    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())
    
    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())
    
    def get_or_create_item(self, product):
        """Get existing cart item or create new one with stock validation"""
        try:
            item = self.items.get(product=product)
            return item, False
        except CartItem.DoesNotExist:
            if product.stock <= 0:
                raise ValueError(f"Product '{product.name}' is out of stock")
            
            item = self.items.create(
                product=product,
                quantity=1
            )
            return item, True
    
    def add_item(self, product, quantity=1):
        """Add item to cart with stock validation"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        item, created = self.get_or_create_item(product)
        if not created:
            # Check if adding quantity exceeds stock
            new_quantity = item.quantity + quantity
            if new_quantity > product.stock:
                raise ValueError(f"Insufficient stock. Available: {product.stock}, Requested: {new_quantity}")
            item.quantity = new_quantity
            item.save()
        else:
            # New item, set the requested quantity
            if quantity > product.stock:
                raise ValueError(f"Insufficient stock. Available: {product.stock}, Requested: {quantity}")
            item.quantity = quantity
            item.save()
        
        return item
    
    @property
    def is_empty(self):
        """Check if cart is empty"""
        return self.items.count() == 0
    
    def clear(self):
        """Clear all items from cart"""
        self.items.all().delete()
    
    def get_item_count(self):
        """Get distinct item count (not total quantity)"""
        return self.items.count()


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    size = models.ForeignKey('Size', on_delete=models.SET_NULL, null=True, blank=True)
    color = models.ForeignKey('Color', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        # The unique constraint below already creates a covering index.
        unique_together = ('cart', 'product', 'size', 'color')
    
    def __str__(self):
        size_label = f" ({self.size.code})" if getattr(self, 'size', None) else ''
        color_label = f" - {self.color.name}" if getattr(self, 'color', None) else ''
        return f"{self.quantity}x {self.product.name}{size_label}{color_label}"
    
    @property
    def total_price(self):
        return self.quantity * self.product.price
    
    def increase_quantity(self, amount=1):
        """Increase item quantity safely"""
        with transaction.atomic():
            # Refresh from database and lock the row
            self.refresh_from_db()
            
            # Check stock availability
            new_quantity = self.quantity + amount
            if new_quantity > self.product.stock:
                raise ValueError(f"Insufficient stock. Available: {self.product.stock}, Current in cart: {self.quantity}")
            
            self.quantity = new_quantity
            self.save(update_fields=['quantity'])
    
    def decrease_quantity(self, amount=1):
        """Decrease item quantity, delete if reaches 0"""
        with transaction.atomic():
            # Refresh from database and lock the row
            self.refresh_from_db()
            
            new_quantity = self.quantity - amount
            
            if new_quantity <= 0:
                self.delete()
            else:
                self.quantity = new_quantity
                self.save(update_fields=['quantity'])
    
    def set_quantity(self, quantity):
        """Set specific quantity with stock validation"""
        if quantity <= 0:
            self.delete()
            return
        
        if quantity > self.product.stock:
            raise ValueError(f"Insufficient stock. Available: {self.product.stock}, Requested: {quantity}")
        
        self.quantity = quantity
        self.save(update_fields=['quantity'])


class Wallet(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"{self.user.username}'s Wallet (₹{self.balance})"

    def add_money(self, amount, description=""):
        """Add money to wallet with transaction record"""
        with transaction.atomic():
            # Lock the wallet row to prevent race conditions
            wallet = Wallet.objects.select_for_update().get(pk=self.pk)
            wallet.balance += Decimal(str(amount))
            wallet.save()
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='credit',
                amount=Decimal(str(amount)),
                description=description,
                balance_after=wallet.balance
            )
            self.balance = wallet.balance  # Sync caller's reference
    
    def deduct_money(self, amount, description=""):
        """Deduct money from wallet with transaction record"""
        amount = Decimal(str(amount))
        with transaction.atomic():
            # Lock the wallet row to prevent race conditions
            wallet = Wallet.objects.select_for_update().get(pk=self.pk)
            if wallet.balance < amount:
                raise ValueError("Insufficient wallet balance")
            wallet.balance -= amount
            wallet.save()
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='debit',
                amount=amount,
                description=description,
                balance_after=wallet.balance
            )
            self.balance = wallet.balance  # Sync caller's reference


class WalletTransaction(TimeStampedModel):
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, default='')
    balance_after = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', '-created_at']),
        ]

    def __str__(self):
        return f"{self.wallet.user.username} - {self.transaction_type} ₹{self.amount}"


class UPIPaymentMethod(TimeStampedModel):
    name = models.CharField(max_length=50, unique=True, help_text="e.g., Paytm, Google Pay")
    code = models.CharField(max_length=20, unique=True, help_text="e.g., paytm, googlepay")
    logo = models.ImageField(upload_to='upi_logos/', help_text="Upload UPI app logo")
    qr_code = models.ImageField(upload_to='upi_qr_codes/', help_text="Upload QR code image for payments")
    upi_id = models.CharField(max_length=100, help_text="UPI ID for this payment method")
    is_active = models.BooleanField(default=True, help_text="Enable/disable this payment method")
    display_order = models.PositiveIntegerField(default=1, help_text="Order in which to display")
    
    class Meta:
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name



class Order(TimeStampedModel):
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending Payment Approval'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('online', 'Pay Online (Razorpay)'),
        ('wallet', 'Wallet Payment'),
        ('wallet_partial', 'Wallet + Online Payment'),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    full_name = models.CharField(max_length=120)
    address_line1 = models.CharField(max_length=500)
    address_line2 = models.CharField(max_length=500, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    phone = models.CharField(max_length=20)
    payment_method = models.CharField(max_length=15, choices=PAYMENT_METHOD_CHOICES, default='online')
    upi_provider = models.CharField(max_length=20, blank=True, null=True)  # Store selected UPI provider
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    wallet_amount_used = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    remaining_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=15, choices=ORDER_STATUS_CHOICES, default='processing')
    # Razorpay Payment Gateway Fields
    razorpay_order_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    razorpay_payment_status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ])
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    tracking_url = models.URLField(blank=True, null=True)
    carrier_name = models.CharField(max_length=100, blank=True, null=True, help_text='e.g., Delhivery, BlueDart, DTDC')
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    is_returned = models.BooleanField(default=False)
    return_reason = models.TextField(blank=True, null=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    estimated_delivery_date = models.DateField(null=True, blank=True, help_text='Estimated delivery date shown at checkout')

    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['razorpay_order_id']),
        ]

    def __str__(self):
        return f"Order #{self.id}"

    @property
    def items_count(self):
        return sum(item.quantity for item in self.items.all())
    
    @property
    def can_be_delivered(self):
        """Check if order can be marked as delivered"""
        return self.status == 'shipped'
    
    @property
    def can_be_returned(self):
        """Check if order can be returned"""
        return (self.status == 'delivered' and not self.is_returned and 
                not hasattr(self, 'return_request'))
    
    @property
    def has_pending_return(self):
        """Check if order has a pending return request"""
        return (hasattr(self, 'return_request') and 
                self.return_request.status == 'pending')
    
    def mark_as_shipped(self, tracking_number=None, user=None):
        """Mark order as shipped with audit trail"""
        if self.status == 'processing':
            self.update_status(
                'shipped',
                user=user,
                note='Marked as shipped',
                tracking_number=tracking_number,
            )
    
    def mark_as_delivered(self, user=None):
        """Mark order as delivered with audit trail and clean up cart"""
        if self.status == 'shipped':
            self.update_status('delivered', user=user, note='Marked as delivered')
            # Remove personalized items from cart when order is delivered
            if self.user:
                self._cleanup_personalized_cart_items()
    
    def get_status_badge_class(self):
        """Get CSS class for status badge"""
        status_classes = {
            'pending': 'bg-info',
            'processing': 'bg-warning',
            'shipped': 'bg-info',
            'delivered': 'bg-success',
            'cancelled': 'bg-danger',
        }
        return status_classes.get(self.status, 'bg-secondary')

    def update_status(self, new_status, user=None, note='', tracking_number=None, tracking_url=None, carrier_name=None, send_email=True):
        """
        Update order status with full audit trail and optional email notification.
        
        Args:
            new_status: New status value
            user: User making the change (admin)
            note: Optional note for this status change
            tracking_number: Shipping tracking number
            tracking_url: Shipping tracking URL
            carrier_name: Name of the shipping carrier
            send_email: Whether to send notification email
        """
        from accounts.email_utils import send_order_status_update_email

        old_status = self.status
        
        if old_status == new_status:
            return False

        # Update order fields
        self.status = new_status
        
        if tracking_number is not None:
            self.tracking_number = tracking_number
        if tracking_url is not None:
            self.tracking_url = tracking_url
        if carrier_name is not None:
            self.carrier_name = carrier_name

        # Set timestamps based on status
        if new_status == 'shipped' and not self.shipped_at:
            self.shipped_at = timezone.now()
        elif new_status == 'delivered' and not self.delivered_at:
            self.delivered_at = timezone.now()

        self.save()

        # Create audit trail entry
        OrderStatusHistory.objects.create(
            order=self,
            old_status=old_status,
            new_status=new_status,
            note=note,
            changed_by=user,
            tracking_number=tracking_number or self.tracking_number,
            tracking_url=tracking_url or self.tracking_url,
            carrier_name=carrier_name or self.carrier_name,
        )

        # Send email notification
        if send_email and self.user and self.user.email:
            status_messages = {
                'pending': 'Your order is awaiting payment confirmation.',
                'processing': 'Your order has been confirmed and is being prepared!',
                'shipped': f'Great news! Your order has been shipped.{(" Tracking: " + str(tracking_number or self.tracking_number)) if (tracking_number or self.tracking_number) else ""}',
                'delivered': 'Your order has been delivered. Enjoy your purchase!',
                'cancelled': 'Your order has been cancelled. If you have questions, please contact support.',
            }
            try:
                send_order_status_update_email(self, status_messages.get(new_status, f'Order status updated to: {self.get_status_display()}'))
            except Exception:
                pass  # Don't fail the status update if email fails

        return True

    def get_status_timeline(self):
        """Get the full status timeline for this order."""
        return self.status_history.all().order_by('created_at')
    
    def _cleanup_personalized_cart_items(self):
        """Remove personalized items from cart when order is delivered"""
        from .models import Cart, CartItem, PersonalizationRequest
        
        try:
            # Get user's cart
            cart = Cart.objects.get(user=self.user)
            
            # Get all order items for this order
            order_product_ids = list(self.items.values_list('product_id', flat=True))
            
            # Find personalization requests for products in this order
            personalized_requests = PersonalizationRequest.objects.filter(
                user=self.user,
                product_id__in=order_product_ids,
                status='order_accepted'
            )
            
            # Remove corresponding cart items
            for request in personalized_requests:
                CartItem.objects.filter(
                    cart=cart,
                    product=request.product
                ).delete()
                
        except Cart.DoesNotExist:
            pass  # No cart exists, nothing to clean up
    
    def get_personalization_images(self):
        """Get personalization images specific to this order"""
        personalization_data = []
        
        for item in self.items.all():
            if item.personalization:
                personalization = item.personalization
                personalization_data.append({
                    'product_name': item.product_name,
                    'user_image': personalization.uploaded_image,
                    'admin_image': personalization.admin_final_image,
                    'admin_notes': personalization.admin_notes,
                    'request_id': personalization.id
                })
            else:
                # Fallback to old query pattern for legacy orders
                personalizations = PersonalizationRequest.objects.filter(
                    user=self.user,
                    product=item.product,
                    status='order_accepted'
                )
                if personalizations.count() == 1:
                    personalization = personalizations.first()
                    personalization_data.append({
                        'product_name': item.product_name,
                        'user_image': personalization.uploaded_image,
                        'admin_image': personalization.admin_final_image,
                        'admin_notes': personalization.admin_notes,
                        'request_id': personalization.id
                    })
        
        return personalization_data

class OrderStatusHistory(TimeStampedModel):
    """Audit trail for every order status change."""
    # Reuse Order's status choices so the two never drift apart.
    ORDER_STATUSES = Order.ORDER_STATUS_CHOICES

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=15, choices=ORDER_STATUSES, blank=True, null=True)
    new_status = models.CharField(max_length=15, choices=ORDER_STATUSES)
    note = models.TextField(blank=True, default='')
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_status_changes')
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    tracking_url = models.URLField(blank=True, null=True)
    carrier_name = models.CharField(max_length=100, blank=True, null=True, help_text='e.g., Delhivery, BlueDart, DTDC')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order Status History'
        verbose_name_plural = 'Order Status Histories'

    def __str__(self):
        return f"Order #{self.order.id}: {self.old_status or 'created'} → {self.new_status} at {self.created_at}"


class ReturnRequest(TimeStampedModel):
    RETURN_STATUS_CHOICES = [
        ('pending', 'Pending Admin Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Refund Completed'),
    ]
    
    RETURN_REASON_CHOICES = [
        ('defective', 'Product is Defective'),
        ('wrong_item', 'Wrong Item Delivered'),
        ('not_as_described', 'Not as Described'),
        ('size_issue', 'Size Issue'),
        ('quality_issue', 'Quality Issue'),
        ('changed_mind', 'Changed Mind'),
        ('other', 'Other'),
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='return_request')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.CharField(max_length=20, choices=RETURN_REASON_CHOICES)
    description = models.TextField(blank=True, help_text='Additional details about the return')
    status = models.CharField(max_length=15, choices=RETURN_STATUS_CHOICES, default='pending')
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    admin_notes = models.TextField(blank=True, help_text='Admin notes for this return request')
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['user', 'status']),
        ]
    
    def __str__(self):
        return f"Return Request for Order #{self.order.id} - {self.status}"
    
    def approve_return(self, admin_notes=""):
        """Approve return request and process refund to wallet"""
        if self.status != 'pending':
            raise ValueError("Return request is not in pending status")
        
        with transaction.atomic():
            # Update return request status
            self.status = 'approved'
            self.approved_at = timezone.now()
            self.admin_notes = admin_notes
            self.refund_amount = self.order.total_amount
            self.save()
            
            # Update order status
            self.order.is_returned = True
            self.order.return_reason = self.get_reason_display()
            self.order.returned_at = timezone.now()
            self.order.save()
            
            # Add refund to user's wallet
            wallet, created = Wallet.objects.get_or_create(user=self.user)
            wallet.add_money(
                self.refund_amount,
                f"Refund for returned Order #{self.order.id} - {self.get_reason_display()}"
            )
            
            # Mark as completed
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()
    
    def reject_return(self, admin_notes=""):
        """Reject return request"""
        if self.status != 'pending':
            raise ValueError("Return request is not in pending status")
        
        self.status = 'rejected'
        self.admin_notes = admin_notes
        self.save()


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=150)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    size = models.ForeignKey('Size', on_delete=models.SET_NULL, null=True, blank=True)
    color = models.ForeignKey('Color', on_delete=models.SET_NULL, null=True, blank=True)
    personalization = models.ForeignKey('PersonalizationRequest', on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')

    def __str__(self):
        return f"{self.quantity}x {self.product_name}"
