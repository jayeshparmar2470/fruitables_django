from fruitapp.models import addtocart

def cart_items_count(request):
    if request.user.is_authenticated:
        my_cart_items = addtocart.objects.filter(user=request.user)
    else:
        my_cart_items = []
    return {'my_cart_items': my_cart_items}


from fruitapp.models import Wishlist

def wishlist_count(request):
    if request.user.is_authenticated:
        wishlist_items = Wishlist.objects.filter(user=request.user)
        return {'wishlist_items_count': wishlist_items.count()}
    return {'wishlist_items_count': 0}