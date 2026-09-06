"""Product catalog views: home, categories, product detail, all products."""

import logging

from django.shortcuts import render, get_object_or_404
from django.db.models import Q

from .models import Product, ProductImage, Category, Size, Color

logger = logging.getLogger(__name__)


def home(request):
    # Base querysets
    products = Product.objects.all().prefetch_related('sizes', 'colors')
    all_sizes = Size.objects.all().order_by('display_order', 'code')
    all_colors = Color.objects.all().order_by('name')

    # Get filter parameters
    q = request.GET.get('q')
    selected_sizes = request.GET.getlist('size')
    selected_colors = request.GET.getlist('color')
    max_price = request.GET.get('price')

    # Apply filters
    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(category__name__icontains=q)
        )

    if selected_sizes:
        products = products.filter(sizes__code__in=selected_sizes).distinct()

    if selected_colors:
        products = products.filter(colors__id__in=selected_colors).distinct()

    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass

    # Dynamic Fandom section
    fandom_parent = Category.objects.filter(name__iexact='Fandom & Superhero Edition').first()

    # Top-level categories
    if fandom_parent:
        categories = Category.objects.filter(parent__isnull=True).exclude(id=fandom_parent.id).select_related()
    else:
        categories = Category.objects.filter(parent__isnull=True).select_related()

    # Pagination simulation (Featured)
    featured_products = products[:20]
    has_more_products = products.count() > 20

    fandoms = fandom_parent.children.all() if fandom_parent else []

    return render(request, 'store/home.html', {
        'products': products,
        'featured_products': featured_products,
        'categories': categories,
        'fandoms': fandoms,
        'fandom_parent': fandom_parent,
        'has_more_products': has_more_products,
        'all_sizes': all_sizes,
        'all_colors': all_colors,
        'selected_sizes': selected_sizes,
        'selected_colors': [int(c) for c in selected_colors if c.isdigit()],
        'current_max_price': max_price or "2000",
    })


def category_page(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    # Get sub-categories if this is a parent category
    sub_categories = Category.objects.filter(parent=category)

    # Get products from this category OR any of its sub-categories
    products = Product.objects.filter(
        Q(category=category) | Q(category__parent=category)
    ).distinct().prefetch_related('sizes')

    # Create a list of products with their available sizes
    products_with_sizes = []
    for product in products:
        products_with_sizes.append({
            'product': product,
            'available_sizes': list(product.sizes.all())
        })

    return render(request, 'store/category_page.html', {
        'category': category,
        'sub_categories': sub_categories,
        'products_with_sizes': products_with_sizes
    })


def _category_by_name(request, name):
    """Helper: look up a Category by name (case-insensitive) and render category_page."""
    category = Category.objects.filter(name__iexact=name).first()
    if category:
        return category_page(request, category.id)
    # Fallback: show empty category-like page
    return render(request, 'store/category_page.html', {'category': None, 'sub_categories': [], 'products_with_sizes': []})


def plain_shirt(request):
    return _category_by_name(request, 'Plain Shirt')


def cap(request):
    return _category_by_name(request, 'Cap')


def bottle(request):
    return _category_by_name(request, 'Bottle')


def mug(request):
    return _category_by_name(request, 'Mug')


def god_goddess(request):
    return _category_by_name(request, 'God & Goddess')


def oversize(request):
    return _category_by_name(request, 'Oversize')


def polo_shirt(request):
    return _category_by_name(request, 'Polo Shirt')


def regular_thin(request):
    return _category_by_name(request, 'Regular Thin')


def regular_thick(request):
    return _category_by_name(request, 'Regular Thick')


def combo(request):
    return _category_by_name(request, 'Combo')


def couple(request):
    return _category_by_name(request, 'Couple')


def women_specific(request):
    return _category_by_name(request, 'Women Specific')


def personal_customise(request):
    return _category_by_name(request, 'Personal Customise')


def sports(request):
    return _category_by_name(request, 'Sports (Cricket & Football)')


def regional_preference(request):
    return _category_by_name(request, 'Regional Preference')


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # Get related products from the same category (excluding current product)
    related_products = Product.objects.filter(category=product.category).exclude(id=product_id)[:4]
    available_sizes = list(product.sizes.all())

    # Get all product images (main + additional)
    product_images = product.images.all()

    return render(request, 'store/product_detail.html', {
        'product': product,
        'related_products': related_products,
        'available_sizes': available_sizes,
        'product_images': product_images,
    })


def all_products(request):
    query = request.GET.get('q')
    if query:
        products = Product.objects.filter(name__icontains=query).order_by('-id')
    else:
        products = Product.objects.all().order_by('-id')

    return render(request, 'store/all_products.html', {
        'products': products,
        'query': query
    })


def personal_customize_products(request):
    """Query customizable products from the database."""
    products = Product.objects.filter(can_customize=True).select_related('category').order_by('-id')
    return render(request, 'store/personal_customize_products.html', {'products': products})


# ─── Policy pages ───────────────────────────────────────────────

def refund_cancellation_policy(request):
    return render(request, 'store/refund_cancellation_policy.html')


def shipping_policy(request):
    return render(request, 'store/shipping_policy.html')


def terms_conditions(request):
    return render(request, 'store/terms_conditions.html')


def privacy_policy(request):
    return render(request, 'store/privacy_policy.html')
