import os
import django
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from store.models import Product, ProductImage
from django.core.files.base import ContentFile
import requests

def add_dummy_images():
    products = Product.objects.all()
    if not products.exists():
        print("No products found to add images to.")
        return

    # Fashion images from Unsplash
    sample_images = [
        "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=800",
        "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=800",
        "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=800",
        "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=800",
        "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=800"
    ]

    print(f"Adding images to {products.count()} products...")

    for product in products:
        # Check if product already has gallery images
        if product.images.count() >= 2:
            continue
            
        print(f"Processing {product.name}...")
        
        # Add 2-3 random images
        count = random.randint(2, 3)
        for i in range(count):
            img_url = random.choice(sample_images)
            try:
                response = requests.get(img_url, timeout=10)
                if response.status_code == 200:
                    pi = ProductImage(product=product, alt_text=f"Gallery {i}")
                    pi.image.save(f"prod_{product.id}_gallery_{i}.jpg", ContentFile(response.content), save=False)
                    pi.save()
                    print(f"  - Added image {i+1}")
            except Exception as e:
                print(f"  - Error adding image: {e}")

if __name__ == "__main__":
    add_dummy_images()
