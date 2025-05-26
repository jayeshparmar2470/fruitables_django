from django.shortcuts import render
from .models import Product,category,addtocart,Shippingfee,Billingaddress,Order,OrderItem, Review, Wishlist
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseRedirect,JsonResponse
from django.db import models
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from decouple import config
import razorpay
from django.views.decorators.csrf import csrf_exempt
import json
from decimal import Decimal
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import requests

# Create your views here.
from django.contrib.auth import get_user_model
User = get_user_model()


def get_shipping_details_from_session(session):
    zip_code = session.get('zip_code', '')
    if zip_code:
        ship_qs = Shippingfee.objects.filter(zip_code=zip_code)
        if ship_qs.exists():
            ship_obj = ship_qs.first()
            return {
                'shipping_fee': float(ship_obj.shipping_fee),
                'local_fee': float(ship_obj.local_fee),
                'zip_code': ship_obj.zip_code
            }
    # Default return if no match or no zip_code
    return {
        'shipping_fee': 0.00,
        'local_fee': 0.00,
        'zip_code': ''
    }

from django.shortcuts import redirect
from django.db.models import Q

def search_redirect(request):
    query = request.GET.get('q', '').strip().lower()
    
    if not query:
        return redirect('shop')  # Empty search goes to shop
    
    # First try to find matching category (case-insensitive)
    matching_categories = category.objects.filter(name__icontains=query)
    
    if matching_categories.exists():
        # If only one category matches, go directly to it
        if matching_categories.count() == 1:
            return redirect(f'/shop?cat={matching_categories.first().name}')
        # If multiple categories match, show shop page with search
        return redirect(f'/shop?q={query}')
    
    # Then try to find products with similar names
    matching_products = Product.objects.filter(
        Q(name__icontains=query) | 
        Q(keywords__icontains=query)  # Add a keywords field if you have one
    ).distinct()
    
    if matching_products.exists():
        # If only one product matches closely, go to its detail page
        if matching_products.count() == 1:
            return redirect('shop_detail', slug=matching_products.first().slug)
        # If multiple products match, show shop page with search
        return redirect(f'/shop?q={query}')
    
    # No matches found - show shop with search query
    return redirect(f'/shop?q={query}')

def home(request):
  # Get all categories for tabs
    categories = category.objects.all()

    for cat in categories:
        # Filter products where is_organic=True
        cat.filtered_products = cat.products.filter(is_organic=True)[:4]
    
    # Get featured organic products
    featured_products = Product.objects.filter(is_featured=True, is_organic=True)[:8]
    
    # Get bestseller products
    bestseller_products = Product.objects.filter(is_bestseller=True)[:8]
    
    # Get vegetable products (assuming you have a 'Vegetables' category)
    vegetable_products = Product.objects.filter(category__name='Vegetables', is_organic=True)[:6]
    
    
    context = {
        'categories': categories,
        'featured_products': featured_products,
        'bestseller_products': bestseller_products,
        'vegetable_products': vegetable_products,
    }
    return render(request, 'index.html', context)
def shop(request):
    # Base queryset
    products = Product.objects.all()
    
    # Get all categories
    categories = category.objects.all()
    
    # Apply filters
    cat_param = request.GET.get('cat')
    if cat_param:
        products = products.filter(category__name=cat_param)
    
    # Price filter
    if 'price' in request.GET:
        products = products.filter(price__lte=request.GET['price'])
    
    # Organic filter
    if 'organic' in request.GET:
        products = products.filter(is_organic=True)
    
    # Sorting
    if 'sort' in request.GET:
        sort_option=request.GET['sort']
        if sort_option == 'price_asc':
            products = products.order_by('price')
        elif sort_option == 'price_desc':
            products = products.order_by('-price')
        elif sort_option == 'name_asc':
            products = products.order_by('name')
        elif sort_option == 'name_desc':
            products = products.order_by('-name')
        elif sort_option == 'rating':
            products = products.order_by('-star') 
        # elif sort_option == 'newest':
        #     products = products.order_by('-created_at')  # Assuming you have created_at field
        # elif sort_option == 'popular':
        #     products = products.order_by('-sales_count')  # Assuming you track sales
 
    
    # Search functionality
    search_query = request.GET.get('q')
    if search_query:
        products = products.filter(name__icontains=search_query)

    # Calculate counts for each category with current filters applied
    categories_with_counts = []
    for cat in categories:
        cat_products = products.filter(category=cat)
        
        # Apply non-category filters to category counts
        if 'price' in request.GET:
            cat_products = cat_products.filter(price__lte=request.GET['price'])
        if 'organic' in request.GET:
            cat_products = cat_products.filter(is_organic=True)
            
        categories_with_counts.append({
            'name': cat.name,
            'count': cat_products.count(),
            'id': cat.id
        })
    
    # Count for "ALL" with current filters
    all_count = products.count()
    
    # Featured products (with stars)
    feautured_products_raw = Product.objects.filter(is_featured=True)[:8]
    feautured_products = []
    for p in feautured_products_raw:
        full_stars = int(p.star)
        empty_stars = 5 - full_stars
        feautured_products.append({
            'product': p,
            'full_stars': range(full_stars),
            'empty_stars': range(empty_stars),
        })
    
    # Pagination
    paginator = Paginator(products, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'product': page_obj,
        'categories_with_counts': categories_with_counts,
        'all_count': all_count,
        'feautured_products': feautured_products,
        # Pass all GET parameters to template for filter preservation
        'current_filters': {
            'cat': request.GET.get('cat'),
            'price': request.GET.get('price'),
            'organic': request.GET.get('organic'),
            'sort': request.GET.get('sort'),
            'q': request.GET.get('q'),
        }
    }
    
    return render(request, "shop.html", context)
@login_required(login_url='login')  # Redirects to login page if user not authenticated
def cart(request):
    my_items=addtocart.objects.filter(user=request.user)
    total_price=my_items.aggregate(total=models.Sum('total'))['total'] or 0.00
     
    ship_obj_dict=get_shipping_details_from_session(request.session)
     
    # Get and remove the alert flag from session
    show_zip_alert = request.session.pop('show_zip_alert', False)
    
    # ship_obj={'ship_fee':request.session.get('shipping_fee',0.00),
    # 'local_fee':request.session.get('local_fee',0.00),
    # 'zip_code':request.session.get('zip_code','')
    # }
    return render(request,"cart.html",{'my_items':my_items,'total_price':total_price,
                                       'ship_obj':ship_obj_dict,
                                       'show_zip_alert': show_zip_alert,
                                         'has_zip_code': 'zip_code' in request.session
                                         })


@login_required(login_url='login')  # Redirects to login page if user not authenticated
def add_to_cart(request,prod_id):
    flag=request.GET.get('flag')
    product=Product.objects.get(id=prod_id)
    cart_item,created=addtocart.objects.get_or_create(
        product=product,
        user=request.user
    )
    if not created:
        if flag=='plus':
            cart_item.quantity+=1
            cart_item.save()
        else:
            if cart_item.quantity>1:
                cart_item.quantity-=1
                cart_item.save()
            else:
                cart_item.delete()
    
       
    # Redirect back to the page the user came from
    # referer = request.META.get('HTTP_REFERER', '/shop')  # fallback to 'shop' if referer not available
    # return HttpResponseRedirect(referer)
    return redirect('cart')


def remove_from_cart(request,prod_id):
    product=Product.objects.get(id=prod_id)
    # cart_item=addtocart.objects.get(product=product,user=request.user)
    # cart_item.delete()

    cart_item = addtocart.objects.filter(product=product, user=request.user).first()
    if cart_item:
        cart_item.delete()

    # Redirect back to the page the user came from
    referer = request.META.get('HTTP_REFERER', '/shop')  # fallback to 'shop' if referer not available
    return HttpResponseRedirect(referer)
    # return redirect('shop')

import random

def shipping_details(request,zip_code):
    ship_obj,created=Shippingfee.objects.get_or_create(zip_code=zip_code)
    if created:
        ship_obj.shipping_fee=random.randint(5,12)
        ship_obj.local_fee=random.randint(5,12)
        ship_obj.save()
    request.session['shipping_fee']=float(ship_obj.shipping_fee)
    request.session['local_fee']=float(ship_obj.local_fee)
    request.session['zip_code']=zip_code
    # If the zip code exists, we can reset the session flag to avoid showing the alert again
    if 'show_zip_alert' in request.session:
        del request.session['show_zip_alert']  # Reset the flag after showing the alert

    return redirect('cart')

# In your views.py
def get_location_from_pincode(pincode):
    try:
        response = requests.get(f'https://api.postalpincode.in/pincode/{pincode}')
        if response.status_code == 200:
            data = response.json()
            if data[0]['Status'] == 'Success':
                first_post_office = data[0]['PostOffice'][0]
                return {
                    'district': first_post_office['District'],
                    'state': first_post_office['State'],
                    'country': 'India'
                }
    except Exception as e:
        print(f"Error fetching pincode data: {str(e)}")
    return None 

@login_required(login_url='login')  # Redirects to login page if user not authenticated
def checkout(request):
    user=request.user

     # Check if zip code is set in session
    if 'zip_code' not in request.session:
        # If no zip code in session, redirect to cart page
        request.session['show_zip_alert'] = True
        return redirect('cart')
 # Get location data
    location_data = {}
    if 'zip_code' in request.session:
        pincode_data = get_location_from_pincode(request.session['zip_code'])
        if pincode_data:
            location_data = {
                'city': pincode_data['district'],  # Using district as city
                'state': pincode_data['state'],
                'country': pincode_data['country']
            }
    
    # Fallback to default values if API fails
    if not location_data:
        location_data = {
            'city': '',
            'state': '',
            'country': 'India'
        }
    # ship_obj_dict=get_shipping_details_from_session(request.session)
    ship_obj_dict = Shippingfee.objects.get(zip_code=request.session['zip_code'])
    shipping_fee = ship_obj_dict.shipping_fee
    local_fee = ship_obj_dict.local_fee


    my_items=addtocart.objects.filter(user=request.user)
    if not my_items.exists():
        return redirect('cart')
    
    is_first_order = not Order.objects.filter(user=request.user).exists()
    
    if is_first_order:
        shipping_fee = Decimal('0.00')
        local_fee = Decimal('0.00')
    else:
        shipping_fee = ship_obj_dict.shipping_fee
        local_fee = ship_obj_dict.local_fee


    # total_price=my_items.aggregate(total=models.Sum('total'))['total'] or 0.00
    total_price = sum([item.total for item in my_items])

    bef_final_amount = float(total_price + shipping_fee + local_fee)  
    final_amount = float(total_price + shipping_fee + local_fee) * 100  # in paise

        # Razorpay client
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
    # Create Razorpay Order
    razorpay_order = client.order.create(dict(
        amount=int(final_amount),
        currency='INR',
        payment_capture='1'
    ))

    context = {
        'user': request.user,
        'my_items': my_items,
        'total_price': total_price,
        'ship_obj': ship_obj_dict,
        'is_first_order': is_first_order,
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_merchant_key': settings.RAZORPAY_KEY_ID,
        'final_amount': int(final_amount),
        'bef_final_amount': bef_final_amount,
        'currency': 'INR',
        'location_data': location_data,
    }

    
    return render(request,"checkout.html",context)

# from django.views.decorators.csrf import csrf_exempt
# from razorpay import Client, Utility

@csrf_exempt
def razorpay_verify(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        razorpay_order_id = data.get("razorpay_order_id")
        razorpay_payment_id = data.get("razorpay_payment_id")
        razorpay_signature = data.get("razorpay_signature")

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        try:
            # Verify signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }

            client.utility.verify_payment_signature(params_dict)

            # Create order
            return place_order(request, payment_method='razorpay')
        except Exception as e:
            print(f"Payment verification failed: {str(e)}")  # Debug logging
            messages.error(request, "Payment verification failed")
            return redirect('checkout')
        
def order_success(request):
    return render(request, 'order_success.html')

@login_required
def order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # # Calculate progress for tracking (example logic)
    # status_order = ['processing', 'shipped', 'in_transit', 'out_for_delivery', 'delivered']
    # try:
    #     progress = (status_order.index(order.shipping_status) + 1) * 20
    # except ValueError:
    #     progress = 20
    
    order_subtotal = order.items.aggregate(total=models.Sum('total'))['total'] or 0.00

    order_shipping_fee = order.billing_address.shippingfee.shipping_fee + order.billing_address.shippingfee.local_fee
    order_total = order_subtotal + order_shipping_fee


    context = {
        'order': order,
        'progress': 20,
        'status_order': 'processing',
        'order_subtotal': order_subtotal,
        'order_shipping_fee': order_shipping_fee,
        'order_total': order_total,

    }
    return render(request, 'order_details.html', context)

@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-order_date').prefetch_related('items', 'billing_address__shippingfee')
    return render(request, 'order_list.html', {'orders': orders})

def place_order(request):
    if request.method=="POST":
       try:
        payment_method = request.POST.get('payment_method', 'cod')

        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        if first_name and last_name:
            request.user.full_name = f"{first_name} {last_name}"
            request.user.save()
    
        billing_add,created=Billingaddress.objects.get_or_create(
            user=request.user,
            email=request.POST.get('email', ''),
            phone=request.POST.get('phone', ''),
            address_line1=request.POST.get('address', ''),
            city=request.POST.get('city', ''),
            state=request.POST.get('state', ''),
            country=request.POST.get('country', ''),
            shippingfee=Shippingfee.objects.filter(zip_code=request.POST.get('zip_code')).first()       
              )
        
        order= Order.objects.create(
                user=request.user,
                billing_address=billing_add,
                order_date=timezone.now(),
                # order_date=models.DateTimeField(auto_now_add=True),
                payment_method=payment_method,
                payment_status='completed' if payment_method == 'razorpay' else 'pending'
             )

        for item in addtocart.objects.filter(user=request.user):
            OrderItem.objects.create(
                  order=order,
                   # order=Order.objects.filter(user=request.user).latest('order_date'),
                    product=item.product,
                    quantity=item.quantity, 
                    total=item.total
                )
            # item.delete()
            if payment_method == 'razorpay':
                order.payment_id = request.POST.get('razorpay_payment_id')
                order.save()
        return redirect('order_success')
       except Exception as e:
            print(f"Order creation failed: {str(e)}")
            messages.error(request, "Order creation failed")
            return redirect('checkout')

def contact(request):
    return render(request,"contact.html")

def testimonial(request):
    return render(request,"testimonial.html")

def shop_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    category1 = category.objects.all()

      # Handle review submission
    if request.method == 'POST' and 'submit_review' in request.POST:
        if not request.user.is_authenticated:
            messages.warning(request, 'Please login to submit a review.')
            return redirect('login')  # Make sure you have a login URL named 'login'
            
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        if not rating or not comment:
            messages.error(request, 'Please provide both rating and comment.')
        else:
            Review.objects.create(
                product=product,
                user=request.user,
                rating=int(rating),
                comment=comment
            )
            messages.success(request, 'Thank you for your review!')
            return redirect('shop_detail', slug=product.slug)



    feautured_products_raw = Product.objects.filter(is_featured=True)[:8]
    feautured_products = []

    # Add full and empty star ranges for each featured product
    for p in feautured_products_raw:
        full_stars = int(p.star)
        empty_stars = 5 - full_stars
        feautured_products.append({
            'product': p,
            'full_stars': range(full_stars),
            'empty_stars': range(empty_stars),
        })

    related_products = Product.objects.filter(category=product.category).exclude(slug=product.slug)[:8]

    full_stars = int(product.star)
    empty_stars = 5 - full_stars

     # Product rating - now using reviews if available
    reviews = product.reviews.all().order_by('-created_at')
    # avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or product.star


    context = {
        'product': product,
        'full_stars': range(full_stars),
        'empty_stars': range(empty_stars),
        'category': category1,
        'feautured_products': feautured_products,
        'related_products': related_products,
        'reviews': reviews,
    }
    return render(request, 'shop_detail.html', context)



def error(request):
    return render(request,"404.html")
 



def add_unique_message(request, level, msg):
    storage = messages.get_messages(request)
    if not any(m.message == msg for m in storage):
        messages.add_message(request, level, msg)



def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')  # Already logged in, redirect
    if request.method == "POST":
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        # user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            add_unique_message(request, messages.ERROR, "Invalid username or password")

    return render(request, "login.html")

import requests
def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
 
        # Check if username or email already exists
        if User.objects.filter(username=username).exists():
            add_unique_message(request, messages.ERROR, "Username already exists")
            return render(request, "register.html")

        if User.objects.filter(email=email).exists():
            add_unique_message(request, messages.ERROR, "Email already registered")
            return render(request, "register.html")
        
        
        # Validate email using Abstract API
        
        api_key = config('ABSTRACT_API_KEY')

        validation_url = f"https://emailvalidation.abstractapi.com/v1/?api_key={api_key}&email={email}"
        email_response = requests.get(validation_url).json()

      
        is_valid_email = email_response.get('is_valid_format', {}).get('value', False)
        can_deliver = email_response.get('deliverability') == 'DELIVERABLE'

        if not is_valid_email or not can_deliver:
            add_unique_message(request, messages.ERROR, "Invalid or undeliverable email address")
            return render(request, "register.html")

        if password != confirm_password:
            add_unique_message(request, messages.ERROR, "Passwords do not match")
            return render(request, "register.html")


        # Create user
        User.objects.create_user(username=username, email=email, password=password)
        add_unique_message(request, messages.SUCCESS, "Registration successful")
        return redirect('login')


    return render(request, "register.html")
# @login_required
# def logout(request):
#     if request.method=="POST":
#         logout(request)
#         return redirect('home')

@login_required
def logout1(request):
    logout(request)
    return redirect('home')
    
    

# from django.shortcuts import render, redirect
# from django.contrib.auth import get_user_model
from django.core.mail import send_mail
import random

# User = get_user_model()

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST['email']
        try:
            user = User.objects.get(email=email)
            otp = random.randint(100000, 999999)
            request.session['reset_email'] = email
            request.session['reset_otp'] = str(otp)

            send_mail(
                'Your OTP Code',
                f'Your OTP code is: {otp}',
                settings.DEFAULT_FROM_EMAIL,  # This should be your email
                [email],
                fail_silently=False,
            )
            return redirect('verify_otp')
        except User.DoesNotExist:
            return render(request, 'forgot_password.html', {'error': 'Email not registered'})
    return render(request, 'forgot_password.html')


def verify_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST['otp']
        real_otp = request.session.get('reset_otp')

        if entered_otp == real_otp:
            return redirect('reset_password')
        else:
            return render(request, 'verify_otp.html', {'error': 'Invalid OTP'})
    return render(request, 'verify_otp.html')


from django.contrib.auth.hashers import make_password

def reset_password(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm = request.POST['confirm']
        email = request.session.get('reset_email')

        if password != confirm:
            return render(request, 'reset_password.html', {'error': 'Passwords do not match'})

        user = User.objects.get(email=email)
        if user:
            user.password = make_password(password)
            user.save()
        return redirect('login')  # or your login page
    return render(request, 'reset_password.html')



def add_to_wishlist(request, product_id):
    if not request.user.is_authenticated:
        messages.warning(request, "Please login to add items to your wishlist")
        return redirect('login')
    
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if created:
        messages.success(request, f"{product.name} added to your wishlist")
    else:
        messages.info(request, f"{product.name} is already in your wishlist")
    
    return redirect(request.META.get('HTTP_REFERER', 'home'))

def remove_from_wishlist(request, product_id):
    if not request.user.is_authenticated:
        return redirect('login')
    
    wishlist_item = get_object_or_404(Wishlist, user=request.user, product_id=product_id)
    product_name = wishlist_item.product.name
    wishlist_item.delete()
    messages.success(request, f"{product_name} removed from your wishlist")
    
    return redirect(request.META.get('HTTP_REFERER', 'wishlist'))

def wishlist_view(request):
    if not request.user.is_authenticated:
        messages.warning(request, "Please login to view your wishlist")
        return redirect('login')
    
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
     
    # Pagination - show 8 items per page
    paginator = Paginator(wishlist_items, 8)
    page = request.GET.get('page')
    
    try:
        wishlist_items = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        wishlist_items = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results
        wishlist_items = paginator.page(paginator.num_pages)
    
    context = {
        'wishlist_items': wishlist_items
    }
    return render(request, 'wishlist.html', context)