from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import UserProfile
import re

PHONE_REGEX = re.compile(r"^[0-9]{7,15}$")
# Only letters and spaces allowed for names
NAME_REGEX = re.compile(r"^[a-zA-Z\s]+$")

class RegistrationForm(forms.ModelForm):
    email = forms.EmailField(
        required=False, 
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        }),
        help_text="Provide either email or mobile number (mandatory)."
    )
    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your mobile number'
        }),
        help_text="Provide either email or mobile number (mandatory)."
    )

    class Meta:
        model = User
        fields = ("username", "email")
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            })
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with that username already exists.")
        return username

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            if not PHONE_REGEX.match(phone):
                raise ValidationError("Enter a valid mobile number (digits only, 7-15 characters).")
            if UserProfile.objects.filter(phone=phone).exists():
                raise ValidationError("This mobile number is already registered.")
        return phone

    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get("email", "").strip()
        if email:
            # Check if email already exists (case-insensitive)
            if User.objects.filter(email__iexact=email).exists():
                raise ValidationError("This email address is already registered.")
        return email

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email", "").strip()
        phone = cleaned.get("phone", "").strip()

        if not email and not phone:
            raise ValidationError("Please provide either an email address or a mobile number (at least one is required).")

        return cleaned

    def _post_clean(self):
        """Override to bypass Django's default username validation"""
        super()._post_clean()
        # Remove username validation errors added by Django
        if 'username' in self._errors:
            # Check if it's Django's default error message
            username_errors = self._errors['username']
            for i, error in enumerate(username_errors.data):
                if 'Enter a valid username' in str(error):
                    # Remove Django's default username validation error
                    del username_errors.data[i]
                    break
            # If no errors left, remove the field from errors
            if not username_errors.data:
                del self._errors['username']

    def save(self, commit=True):
        user = super().save(commit=False)
        # Set a random unusable password since we are doing OTP login
        user.set_unusable_password()
        email = self.cleaned_data.get("email", "").strip()
        phone = self.cleaned_data.get("phone", "").strip()
        if email:
            user.email = email
        if commit:
            user.save()
            # Ensure UserProfile exists
            UserProfile.objects.get_or_create(user=user, defaults={'phone': phone if phone else None})
        return user


class CustomLoginForm(forms.Form):
    """Custom login form that accepts email, mobile, or username"""
    login_field = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email, mobile number, or username',
            'autofocus': True
        }),
        label='Email / Mobile / Username'
    )

    def clean_login_field(self):
        login_field = self.cleaned_data.get('login_field', '').strip()
        if not login_field:
            raise ValidationError('This field is required.')
        return login_field

class OTPVerifyForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control otp-input',
            'placeholder': 'Enter 6-digit OTP',
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric'
        }),
        label='Enter OTP'
    )
