"""
Razorpay Payment Gateway Integration
"""
import razorpay
import hmac
import hashlib
from django.conf import settings

# Razorpay Configuration
RAZORPAY_KEY_ID = getattr(settings, 'RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = getattr(settings, 'RAZORPAY_KEY_SECRET', '')

# Initialize Razorpay client
def get_razorpay_client():
    """Get Razorpay client instance"""
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise ValueError(
            "Razorpay credentials not configured.\n"
            "Please add to settings.py:\n"
            "   RAZORPAY_KEY_ID = 'your_key_id'\n"
            "   RAZORPAY_KEY_SECRET = 'your_key_secret'"
        )
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def create_razorpay_order(order_id, amount, currency='INR'):
    """
    Create a Razorpay order
    
    Args:
        order_id: Your internal order ID
        amount: Amount in rupees (will be converted to paise)
        currency: Currency code (default: INR)
    
    Returns:
        dict: Razorpay order response containing order ID, amount, etc.
    """
    try:
        client = get_razorpay_client()
        
        # Razorpay expects amount in paise (smallest currency unit)
        amount_in_paise = int(float(amount) * 100)
        
        order_data = {
            'amount': amount_in_paise,
            'currency': currency,
            'receipt': f'order_{order_id}',
            'notes': {
                'order_id': str(order_id)
            }
        }
        
        razorpay_order = client.order.create(data=order_data)
        print(f"Razorpay order created: {razorpay_order}")
        
        return {
            'success': True,
            'razorpay_order_id': razorpay_order['id'],
            'amount': razorpay_order['amount'],
            'currency': razorpay_order['currency'],
            'key_id': RAZORPAY_KEY_ID
        }
        
    except razorpay.errors.BadRequestError as e:
        print(f"Razorpay BadRequestError: {e}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        print(f"Error creating Razorpay order: {e}")
        return {'success': False, 'error': str(e)}


def verify_razorpay_payment(razorpay_order_id, razorpay_payment_id, razorpay_signature):
    """
    Verify Razorpay payment signature
    
    Args:
        razorpay_order_id: Razorpay order ID
        razorpay_payment_id: Razorpay payment ID
        razorpay_signature: Razorpay signature from callback
    
    Returns:
        bool: True if payment is verified, False otherwise
    """
    try:
        client = get_razorpay_client()
        
        # Verify signature using Razorpay's utility
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        
        client.utility.verify_payment_signature(params_dict)
        print(f"Payment verified successfully: {razorpay_payment_id}")
        return True
        
    except razorpay.errors.SignatureVerificationError as e:
        print(f"Signature verification failed: {e}")
        return False
    except Exception as e:
        print(f"Error verifying payment: {e}")
        return False


def verify_razorpay_signature_manual(razorpay_order_id, razorpay_payment_id, razorpay_signature):
    """
    Manually verify Razorpay payment signature using HMAC
    
    This is an alternative verification method if the SDK utility fails
    """
    try:
        # Create the signature verification string
        message = f"{razorpay_order_id}|{razorpay_payment_id}"
        
        # Generate signature using HMAC-SHA256
        generated_signature = hmac.new(
            RAZORPAY_KEY_SECRET.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        is_valid = hmac.compare_digest(generated_signature, razorpay_signature)
        print(f"Manual signature verification: {is_valid}")
        return is_valid
        
    except Exception as e:
        print(f"Error in manual signature verification: {e}")
        return False


def get_payment_details(payment_id):
    """
    Fetch payment details from Razorpay
    
    Args:
        payment_id: Razorpay payment ID
    
    Returns:
        dict: Payment details or None
    """
    try:
        client = get_razorpay_client()
        payment = client.payment.fetch(payment_id)
        return payment
    except Exception as e:
        print(f"Error fetching payment details: {e}")
        return None


def refund_payment(payment_id, amount=None, notes=None):
    """
    Refund a Razorpay payment
    
    Args:
        payment_id: Razorpay payment ID
        amount: Amount to refund in paise (optional, full refund if not provided)
        notes: Additional notes for the refund
    
    Returns:
        dict: Refund response or error
    """
    try:
        client = get_razorpay_client()
        
        refund_data = {}
        if amount:
            refund_data['amount'] = amount
        if notes:
            refund_data['notes'] = notes
        
        refund = client.payment.refund(payment_id, refund_data)
        return {'success': True, 'refund': refund}
        
    except Exception as e:
        print(f"Error processing refund: {e}")
        return {'success': False, 'error': str(e)}
