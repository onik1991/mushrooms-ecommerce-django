from django.shortcuts import render
from store.models import Product, ReviewRating, Variation

def home(request):
    products = Product.objects.all().filter(is_available=True).order_by('-reviewrating')
    # for product in products:
    #     variations = Variation.objects.get(product=product.id)
    #     print(variations)
    for product in products:
        reviews = ReviewRating.objects.filter(product_id=product.id, status=True)

    context = {
        'products': products,
        # 'variations': variations,
        'reviews': reviews,
    }
    return render(request, 'home.html', context)
