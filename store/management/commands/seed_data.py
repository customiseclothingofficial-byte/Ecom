"""
Management command to seed the database with realistic dummy data.
Usage: python manage.py seed_data
"""
import os
import urllib.request
from decimal import Decimal
from io import BytesIO

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from store.models import (
    Category, Product, Size, Color, ProductImage,
    PersonalizationRequest, Order, OrderItem,
)


# ── Unsplash source URLs (reliable free images) ─────────────────
# Using direct Unsplash source URLs which redirect to actual images
UNSPLASH = {
    # T-Shirts
    'tshirt-black': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600&q=80',
    'tshirt-white': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600&q=80',
    'tshirt-red': 'https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=600&q=80',
    'tshirt-blue': 'https://images.unsplash.com/photo-1618354691373-d851c5c3a990?w=600&q=80',
    'tshirt-green': 'https://images.unsplash.com/photo-1618354691438-25bc04584c23?w=600&q=80',
    'tshirt-yellow': 'https://images.unsplash.com/photo-1562157873-818bc0726f68?w=600&q=80',
    'tshirt-purple': 'https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=600&q=80',
    # Oversize
    'oversize-1': 'https://images.unsplash.com/photo-1578587018452-892bacefd3f2?w=600&q=80',
    'oversize-2': 'https://images.unsplash.com/photo-1622445275463-afa2ab738c34?w=600&q=80',
    # Polo
    'polo-1': 'https://images.unsplash.com/photo-1625910513413-5fc42fbc11e5?w=600&q=80',
    'polo-2': 'https://images.unsplash.com/photo-1586363104862-3a5e2ab60d99?w=600&q=80',
    # Cap
    'cap-1': 'https://images.unsplash.com/photo-1588850561407-ed78c334e67a?w=600&q=80',
    'cap-2': 'https://images.unsplash.com/photo-1575428652377-a2d80e2277fc?w=600&q=80',
    # Mug
    'mug-1': 'https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=600&q=80',
    'mug-2': 'https://images.unsplash.com/photo-1577937927133-66ef06acdf18?w=600&q=80',
    # Bottle
    'bottle-1': 'https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=600&q=80',
    'bottle-2': 'https://images.unsplash.com/photo-1523362628745-0c100fc988a6?w=600&q=80',
    # Hoodie
    'hoodie-1': 'https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=600&q=80',
    'hoodie-2': 'https://images.unsplash.com/photo-1578768079470-21b604548c23?w=600&q=80',
    # Women
    'women-1': 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=600&q=80',
    'women-2': 'https://images.unsplash.com/photo-1485968579580-b6d095142e6e?w=600&q=80',
    # Couple
    'couple-1': 'https://images.unsplash.com/photo-1516726817505-f5ed825d8885?w=600&q=80',
    'couple-2': 'https://images.unsplash.com/photo-1494790108755-2616b332c31c?w=600&q=80',
    # Sports
    'sports-1': 'https://images.unsplash.com/photo-1517466787929-bc90951d0974?w=600&q=80',
    'sports-2': 'https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=600&q=80',
    # Combo
    'combo-1': 'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=600&q=80',
    'combo-2': 'https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=600&q=80',
    # God & Goddess
    'god-1': 'https://images.unsplash.com/photo-1567593810070-7a3d471af002?w=600&q=80',
    'god-2': 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&q=80',
    # Category images
    'cat-tshirt': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&q=80',
    'cat-cap': 'https://images.unsplash.com/photo-1588850561407-ed78c334e67a?w=400&q=80',
    'cat-mug': 'https://images.unsplash.com/photo-1514228742587-6b1158fcca3d?w=400&q=80',
    'cat-bottle': 'https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=400&q=80',
    'cat-oversize': 'https://images.unsplash.com/photo-1578587018452-892bacefd3f2?w=400&q=80',
    'cat-polo': 'https://images.unsplash.com/photo-1625910513413-5fc42fbc11e5?w=400&q=80',
    'cat-hoodie': 'https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=400&q=80',
    'cat-women': 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=400&q=80',
    'cat-couple': 'https://images.unsplash.com/photo-1516726817505-f5ed825d8885?w=400&q=80',
    'cat-sports': 'https://images.unsplash.com/photo-1517466787929-bc90951d0974?w=400&q=80',
    'cat-combo': 'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=400&q=80',
    'cat-god': 'https://images.unsplash.com/photo-1567593810070-7a3d471af002?w=400&q=80',
    'cat-regular': 'https://images.unsplash.com/photo-1618354691373-d851c5c3a990?w=400&q=80',
    'cat-fandom': 'https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=400&q=80',
    'cat-regional': 'https://images.unsplash.com/photo-1524492412937-b28074a5d7da?w=400&q=80',
    # Home page banners
    'banner-1': 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1200&q=80',
    'banner-2': 'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=1200&q=80',
}


def _download_image(url, filename):
    """Download image from URL and return ContentFile."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=15)
        data = response.read()
        ext = '.jpg'
        if filename.endswith('.png'):
            ext = '.png'
        return ContentFile(data, name=filename + ext)
    except Exception as e:
        print(f"  ⚠ Could not download {url}: {e}")
        return None


class Command(BaseCommand):
    help = 'Seed database with realistic dummy data for custom clothing store'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🌱 Seeding database...\n'))

        self._create_sizes()
        self._create_colors()
        self._create_categories()
        self._create_products()
        self._create_fandom_products()

        self.stdout.write(self.style.SUCCESS('\n✅ Done! Database seeded successfully.\n'))
        self.stdout.write(self.style.SUCCESS('   Products: {}'.format(Product.objects.count())))
        self.stdout.write(self.style.SUCCESS('   Categories: {}'.format(Category.objects.count())))
        self.stdout.write(self.style.SUCCESS('   Sizes: {}'.format(Size.objects.count())))
        self.stdout.write(self.style.SUCCESS('   Colors: {}'.format(Color.objects.count())))

    def _create_sizes(self):
        self.stdout.write('📏 Creating sizes...')
        sizes_data = [
            ('S', 1), ('M', 2), ('L', 3), ('XL', 4), ('XXL', 5),
        ]
        for code, order in sizes_data:
            Size.objects.get_or_create(code=code, defaults={'display_order': order})
        self.stdout.write(f'   ✓ {len(sizes_data)} sizes created')

    def _create_colors(self):
        self.stdout.write('🎨 Creating colors...')
        colors_data = [
            ('Black', '#000000', 1),
            ('White', '#FFFFFF', 2),
            ('Navy Blue', '#1E3A5F', 3),
            ('Red', '#DC2626', 4),
            ('Forest Green', '#166534', 5),
            ('Yellow', '#FACC15', 6),
            ('Purple', '#7C3AED', 7),
            ('Pink', '#EC4899', 8),
            ('Grey', '#6B7280', 9),
            ('Orange', '#EA580C', 10),
            ('Maroon', '#7F1D1D', 11),
            ('Teal', '#0D9488', 12),
            ('Beige', '#D4C5A9', 13),
            ('Sky Blue', '#38BDF8', 14),
            ('Olive', '#4D7C0F', 15),
        ]
        for name, hex_code, order in colors_data:
            Color.objects.get_or_create(
                name=name,
                defaults={'hex_code': hex_code, 'display_order': order}
            )
        self.stdout.write(f'   ✓ {len(colors_data)} colors created')

    def _create_categories(self):
        self.stdout.write('📂 Creating categories...')
        categories = {
            'Plain Shirt': {'image': 'cat-regular', 'display': 'circle', 'children': []},
            'Cap': {'image': 'cat-cap', 'display': 'circle', 'children': []},
            'Bottle': {'image': 'cat-bottle', 'display': 'circle', 'children': []},
            'Mug': {'image': 'cat-mug', 'display': 'circle', 'children': []},
            'God & Goddess': {'image': 'cat-god', 'display': 'circle', 'children': []},
            'Oversize': {'image': 'cat-oversize', 'display': 'circle', 'children': []},
            'Polo Shirt': {'image': 'cat-polo', 'display': 'circle', 'children': []},
            'Regular Thin': {'image': 'cat-regular', 'display': 'circle', 'children': []},
            'Regular Thick': {'image': 'cat-regular', 'display': 'circle', 'children': []},
            'Combo': {'image': 'cat-combo', 'display': 'circle', 'children': []},
            'Couple': {'image': 'cat-couple', 'display': 'circle', 'children': []},
            'Women Specific': {'image': 'cat-women', 'display': 'circle', 'children': []},
            'Personal Customise': {'image': 'cat-regular', 'display': 'circle', 'children': []},
            'Sports (Cricket & Football)': {'image': 'cat-sports', 'display': 'circle', 'children': []},
            'Regional Preference': {'image': 'cat-regional', 'display': 'circle', 'children': []},
        }

        for name, data in categories.items():
            cat, created = Category.objects.get_or_create(
                name=name,
                defaults={'display_style': data['display']}
            )
            if created and data['image']:
                img = _download_image(UNSPLASH[data['image']], f'cat_{name.lower().replace(" ", "_")}')
                if img:
                    cat.image = img
                    cat.save(update_fields=['image'])

        # Fandom parent with children
        fandom_parent, _ = Category.objects.get_or_create(
            name='Fandom & Superhero Edition',
            defaults={'display_style': 'circle'}
        )
        fandom_children = ['Marvel', 'DC Comics', 'Anime', 'Harry Potter', 'Star Wars']
        for child_name in fandom_children:
            child, _ = Category.objects.get_or_create(
                name=child_name,
                defaults={'parent': fandom_parent, 'display_style': 'box'}
            )

        self.stdout.write(f'   ✓ {Category.objects.count()} categories created')

    def _create_products(self):
        self.stdout.write('👕 Creating products...')

        all_sizes = list(Size.objects.all())
        all_colors = list(Color.objects.all())

        # (name, category, price, original_price, stock, description, can_customize, image_key, product_images, sizes_subset, colors_subset)
        products_data = [
            # ── Plain Shirts ──
            ('Classic Cotton T-Shirt', 'Plain Shirt', 299, 599, 150,
             'Premium 100% cotton round neck t-shirt. Soft, breathable fabric perfect for everyday wear.',
             True, 'tshirt-black', ['tshirt-black', 'tshirt-white', 'tshirt-blue'], all_sizes[:4], [c for c in all_colors if c.name in ('Black', 'White', 'Navy Blue', 'Grey')]),

            ('Premium Slim Fit Tee', 'Plain Shirt', 399, 799, 100,
             'Slim fit t-shirt with a modern cut. Ideal for casual outings and layering.',
             True, 'tshirt-red', ['tshirt-red', 'tshirt-green', 'tshirt-black'], all_sizes[:4], [c for c in all_colors if c.name in ('Red', 'Black', 'White')]),

            ('Oversized Streetwear Tee', 'Oversize', 499, 999, 80,
             'Trendy oversized fit with dropped shoulders. Street style essential.',
             True, 'oversize-1', ['oversize-1', 'oversize-2', 'tshirt-black'], all_sizes, [c for c in all_colors if c.name in ('Black', 'White', 'Grey')]),

            ('Graphic Print Oversize Tee', 'Oversize', 549, 1099, 60,
             'Bold graphic print on premium oversized fabric. Make a statement.',
             True, 'oversize-2', ['oversize-2', 'oversize-1'], all_sizes, [c for c in all_colors if c.name in ('Black', 'White')]),

            # ── Polo Shirts ──
            ('Classic Polo Shirt', 'Polo Shirt', 499, 999, 90,
             'Timeless polo with contrast collar. Smart casual at its best.',
             False, 'polo-1', ['polo-1', 'polo-2'], all_sizes[:4], [c for c in all_colors if c.name in ('Navy Blue', 'White', 'Black', 'Grey')]),

            ('Premium Pique Polo', 'Polo Shirt', 699, 1299, 50,
             'Premium pique cotton polo with embroidered logo. Professional look.',
             False, 'polo-2', ['polo-2'], all_sizes[:4], [c for c in all_colors if c.name in ('Black', 'Navy Blue', 'Forest Green')]),

            # ── Regular Thin ──
            ('Regular Fit Thin Tee', 'Regular Thin', 249, 499, 200,
             'Lightweight regular fit t-shirt. Perfect for summer days.',
             True, 'tshirt-blue', ['tshirt-blue', 'tshirt-white', 'tshirt-green'], all_sizes[:4], all_colors[:8]),

            # ── Regular Thick ──
            ('Heavy Cotton Thick Tee', 'Regular Thick', 349, 699, 120,
             'Thick premium cotton for a structured look. Durability meets style.',
             True, 'tshirt-yellow', ['tshirt-yellow', 'tshirt-purple', 'tshirt-red'], all_sizes[:4], [c for c in all_colors if c.name in ('Black', 'White', 'Yellow', 'Purple')]),

            # ── Caps ──
            ('Classic Baseball Cap', 'Cap', 199, 399, 200,
             'Adjustable baseball cap with curved brim. One size fits all.',
             True, 'cap-1', ['cap-1', 'cap-2'], [], [c for c in all_colors if c.name in ('Black', 'White', 'Navy Blue', 'Red')]),

            ('Premium Embroidered Cap', 'Cap', 299, 599, 150,
             'Premium cap with custom embroidery option. High-quality stitching.',
             True, 'cap-2', ['cap-2', 'cap-1'], [], [c for c in all_colors if c.name in ('Black', 'Grey', 'Maroon')]),

            # ── Mugs ──
            ('Classic Coffee Mug', 'Mug', 149, 299, 300,
             'Ceramic coffee mug with glossy finish. Dishwasher safe.',
             True, 'mug-1', ['mug-1', 'mug-2'], [], [c for c in all_colors if c.name in ('White', 'Black')]),

            ('Premium Photo Mug', 'Mug', 249, 499, 200,
             'Upload your favorite photo! High-quality print on ceramic mug.',
             True, 'mug-2', ['mug-2'], [], [c for c in all_colors if c.name in ('White',)]),

            # ── Bottles ──
            ('Steel Water Bottle', 'Bottle', 349, 699, 150,
             'Double-wall insulated steel bottle. Keeps drinks cold for 24hrs.',
             True, 'bottle-1', ['bottle-1', 'bottle-2'], [], [c for c in all_colors if c.name in ('Black', 'White', 'Navy Blue', 'Red')]),

            ('Custom Print Bottle', 'Bottle', 399, 799, 100,
             'Personalized steel bottle with your design. Premium quality.',
             True, 'bottle-2', ['bottle-2'], [], [c for c in all_colors if c.name in ('Black', 'White')]),

            # ── Hoodies (under Regular Thick) ──
            ('Classic Pullover Hoodie', 'Regular Thick', 799, 1499, 70,
             'Warm fleece-lined hoodie with kangaroo pocket. Winter essential.',
             True, 'hoodie-1', ['hoodie-1', 'hoodie-2'], all_sizes, [c for c in all_colors if c.name in ('Black', 'Grey', 'Navy Blue')]),

            ('Zip-Up Hoodie', 'Regular Thick', 899, 1699, 50,
             'Full-zip hoodie with dual pockets. Easy layering piece.',
             False, 'hoodie-2', ['hoodie-2'], all_sizes, [c for c in all_colors if c.name in ('Black', 'White', 'Grey')]),

            # ── Women Specific ──
            ('Women Relaxed Fit Tee', 'Women Specific', 349, 699, 100,
             'Relaxed fit tee designed for women. Soft-touch fabric.',
             True, 'women-1', ['women-1', 'women-2'], all_sizes[:4], [c for c in all_colors if c.name in ('White', 'Pink', 'Yellow', 'Teal')]),

            ('Women Cropped Hoodie', 'Women Specific', 899, 1599, 40,
             'Trendy cropped hoodie with ribbed hem. Perfect for layering.',
             False, 'women-2', ['women-2'], all_sizes[:4], [c for c in all_colors if c.name in ('Pink', 'White', 'Lavender', 'Grey')]),

            # ── Couple Tees ──
            ('His & Hers Combo Tee', 'Couple', 599, 1199, 80,
             'Matching couple t-shirts. Show the world you are together!',
             True, 'couple-1', ['couple-1', 'couple-2'], all_sizes[:4], [c for c in all_colors if c.name in ('Black', 'White')]),

            # ── Sports ──
            ('Cricket Jersey Tee', 'Sports (Cricket & Football)', 499, 999, 100,
             'Lightweight sports tee for cricket enthusiasts. Moisture-wicking fabric.',
             True, 'sports-1', ['sports-1', 'sports-2'], all_sizes, [c for c in all_colors if c.name in ('Blue', 'White', 'Yellow')]),

            ('Football Training Tee', 'Sports (Cricket & Football)', 449, 899, 90,
             'Performance training tee for football. Breathable and durable.',
             False, 'sports-2', ['sports-2'], all_sizes, [c for c in all_colors if c.name in ('Black', 'Red', 'White')]),

            # ── God & Goddess ──
            ('Lord Shiva Graphic Tee', 'God & Goddess', 399, 799, 100,
             'Beautiful Lord Shiva artwork on premium cotton. Spiritual meets style.',
             True, 'god-1', ['god-1', 'god-2'], all_sizes[:4], [c for c in all_colors if c.name in ('Black', 'White', 'Saffron', 'Grey')]),

            ('Hanuman Premium Tee', 'God & Goddess', 449, 899, 80,
             'Lord Hanuman illustration on high-quality fabric. Faith in fashion.',
             True, 'god-2', ['god-2', 'god-1'], all_sizes[:4], [c for c in all_colors if c.name in ('Orange', 'Black', 'Red')]),

            # ── Combo ──
            ('3-Pack Essentials Combo', 'Combo', 699, 1499, 60,
             'Bundle of 3 plain cotton tees. Best value pack!',
             False, 'combo-1', ['combo-1', 'combo-2'], all_sizes[:4], [c for c in all_colors if c.name in ('Black', 'White', 'Grey')]),

            # ── Regional Preference ──
            ('Odisha Heritage Tee', 'Regional Preference', 499, 999, 50,
             'Celebrate Odisha culture with this heritage-inspired design.',
             True, 'combo-2', ['combo-2'], all_sizes[:4], [c for c in all_colors if c.name in ('White', 'Yellow', 'Red')]),
        ]

        created_count = 0
        for data in products_data:
            (name, cat_name, price, orig_price, stock, desc,
             can_custom, img_key, img_keys, sizes_subset, colors_subset) = data

            product, created = Product.objects.get_or_create(
                name=name,
                defaults={
                    'category': Category.objects.filter(name=cat_name).first(),
                    'price': Decimal(str(price)),
                    'original_price': Decimal(str(orig_price)),
                    'stock': stock,
                    'description': desc,
                    'can_customize': can_custom,
                }
            )

            if created:
                created_count += 1

                # Set sizes
                if sizes_subset:
                    product.sizes.set(sizes_subset)

                # Set colors
                if colors_subset:
                    product.colors.set(colors_subset)

                # Download and set main product image
                if img_key and img_key in UNSPLASH:
                    img = _download_image(UNSPLASH[img_key], f'prod_{name.lower().replace(" ", "_")}')
                    if img:
                        product.image = img
                        product.save(update_fields=['image'])

                # Create product images (color variants)
                for i, ik in enumerate(img_keys):
                    if ik in UNSPLASH:
                        img = _download_image(UNSPLASH[ik], f'prodimg_{name.lower().replace(" ", "_")}_{i}')
                        if img:
                            color_obj = colors_subset[i] if i < len(colors_subset) else None
                            ProductImage.objects.create(
                                product=product,
                                image=img,
                                color=color_obj,
                            )

                self.stdout.write(f'   ✓ {name}')

        self.stdout.write(f'   ✓ {created_count} products created')

    def _create_fandom_products(self):
        self.stdout.write('🦸 Creating fandom products...')
        fandom_parent = Category.objects.filter(name='Fandom & Superhero Edition').first()
        if not fandom_parent:
            return

        all_sizes = list(Size.objects.all())
        fandom_data = [
            ('Spider-Man Graphic Tee', 'Marvel', 499, 999, 80,
             'Web-slinger inspired tee. Marvel official style.',
             True, 'god-1', ['god-1']),
            ('Batman Dark Knight Tee', 'DC Comics', 499, 999, 70,
             'Gotham\'s protector on premium cotton.',
             True, 'god-2', ['god-2']),
            ('Dragon Ball Z Tee', 'Anime', 449, 899, 90,
             'Saiyan power! Goku inspired graphic tee.',
             True, 'sports-1', ['sports-1']),
            ('Naruto Uzumaki Tee', 'Anime', 449, 899, 85,
             'Believe it! Naruto themed premium tee.',
             True, 'sports-2', ['sports-2']),
            ('Hogwarts House Tee', 'Harry Potter', 499, 999, 60,
             'Choose your house! Gryffindor, Slytherin, Ravenclaw, or Hufflepuff.',
             True, 'god-1', ['god-1', 'god-2']),
            ('Stormtrooper Tee', 'Star Wars', 549, 1099, 55,
             'The dark side never looked this good.',
             True, 'tshirt-black', ['tshirt-black', 'tshirt-white']),
        ]

        created_count = 0
        for data in fandom_data:
            (name, child_name, price, orig_price, stock,
             desc, can_custom, img_key, img_keys) = data

            child_cat = Category.objects.filter(name=child_name, parent=fandom_parent).first()
            if not child_cat:
                continue

            product, created = Product.objects.get_or_create(
                name=name,
                defaults={
                    'category': child_cat,
                    'price': Decimal(str(price)),
                    'original_price': Decimal(str(orig_price)),
                    'stock': stock,
                    'description': desc,
                    'can_customize': can_custom,
                }
            )

            if created:
                created_count += 1
                product.sizes.set(all_sizes[:4])
                product.colors.set(Color.objects.filter(name__in=['Black', 'White']))

                if img_key and img_key in UNSPLASH:
                    img = _download_image(UNSPLASH[img_key], f'prod_{name.lower().replace(" ", "_")}')
                    if img:
                        product.image = img
                        product.save(update_fields=['image'])

                for i, ik in enumerate(img_keys):
                    if ik in UNSPLASH:
                        img = _download_image(UNSPLASH[ik], f'prodimg_{name.lower().replace(" ", "_")}_{i}')
                        if img:
                            ProductImage.objects.create(product=product, image=img)

                self.stdout.write(f'   ✓ {name}')

        self.stdout.write(f'   ✓ {created_count} fandom products created')
