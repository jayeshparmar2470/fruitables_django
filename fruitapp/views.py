from django.shortcuts import render
from .models import Product,category,addtocart,Shippingfee,Billingaddress,Order,OrderItem
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


def home(request):
    return render(request,"index.html")

def shop(request):
    product=Product.objects.all()
    category1=category.objects.all()
    param=request.GET.get('cat')
    if param:
        product=Product.objects.filter(category__name=param)
    else:
        product=Product.objects.all()
    total_products = Product.objects.count()  # For ALL

    return render(request,"shop.html",{'product':product,'category':category1,'total_products':total_products})


@login_required(login_url='login')  # Redirects to login page if user not authenticated
def cart(request):
    my_items=addtocart.objects.filter(user=request.user)
    total_price=my_items.aggregate(total=models.Sum('total'))['total'] or 0.00
     
    ship_obj_dict=get_shipping_details_from_session(request.session)

    # ship_obj={'ship_fee':request.session.get('shipping_fee',0.00),
    # 'local_fee':request.session.get('local_fee',0.00),
    # 'zip_code':request.session.get('zip_code','')
    # }
    return render(request,"cart.html",{'my_items':my_items,'total_price':total_price,'ship_obj':ship_obj_dict})


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

@login_required(login_url='login')  # Redirects to login page if user not authenticated
def checkout(request):
    user=request.user

     # Check if zip code is set in session
    if 'zip_code' not in request.session:
        # If no zip code in session, redirect to cart page
        request.session['show_zip_alert'] = True
        return redirect('cart')
    
    # ship_obj_dict=get_shipping_details_from_session(request.session)
    ship_obj_dict = Shippingfee.objects.get(zip_code=request.session['zip_code'])
    shipping_fee = ship_obj_dict.shipping_fee
    local_fee = ship_obj_dict.local_fee

    my_items=addtocart.objects.filter(user=request.user)
    if not my_items.exists():
        return redirect('cart')
    
    if not Order.objects.filter(user=request.user).exists():
        # User has no orders yet, so this is their first order
        shipping_fee =Decimal('0.00')
        local_fee = Decimal('0.00')

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
        'is_first_order': not Order.objects.filter(user=request.user).exists(),
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_merchant_key': settings.RAZORPAY_KEY_ID,
        'final_amount': int(final_amount),
        'bef_final_amount': bef_final_amount,
        'currency': 'INR',
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

            # Signature matched, create order in DB
            user = request.user
            my_items = addtocart.objects.filter(user=user)
            # billing = Billingaddress.objects.create(user=user, city="demo")  # Get form data as needed
            # order = Order.objects.create(user=user, billing_address=billing)
            
            request.user.first_name = request.POST.get('first_name')
            request.user.last_name = request.POST.get('last_name')
            request.user.save()
    
            billing_add,created=Billingaddress.objects.get_or_create(
            user=request.user,
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            # address_line1=request.POST.get('address'),
            address_line1='akakakaka',
            # city=request.POST.get('city'),
            city='city',
            # state=request.POST.get('state'),
            state='state',
            # country=request.POST.get('country'),
            country='country',
            # Shippingfee=Shippingfee.objects.filter(zip_code=request.POST.get('zip_code')).first()       
            Shippingfee=Shippingfee.objects.filter(zip_code='380015').first()       
            )
        
            order= Order.objects.create(
                user=request.user,
                billing_address=billing_add,
                order_date=timezone.now()

                # order_date=models.DateTimeField(auto_now_add=True),
                 )
            for item in my_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    total=item.total

                )
                item.delete()

            return JsonResponse({'status': 'success'})
        except Exception as e:
            print(f"Payment verification failed: {str(e)}")  # Debug logging
            return JsonResponse({'status': 'failed', 'error': str(e)})
        
def order_success(request):
    return render(request, 'order_success.html')


def place_order(request):
    if request.method=="POST":

        request.user.first_name = request.POST.get('first_name')
        request.user.last_name = request.POST.get('last_name')
        request.user.save()
    
        billing_add,created=Billingaddress.objects.get_or_create(
            user=request.user,
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            address_line1=request.POST.get('address'),
            city=request.POST.get('city'),
            state=request.POST.get('state'),
            country=request.POST.get('country'),
            Shippingfee=Shippingfee.objects.filter(zip_code=request.POST.get('zip_code')).first()       
              )
        
        order= Order.objects.create(
                user=request.user,
                billing_address=billing_add,
                order_date=timezone.now()

                # order_date=models.DateTimeField(auto_now_add=True),
             )
        for item in addtocart.objects.filter(user=request.user):
            OrderItem.objects.create(
                order=order,
                # order=Order.objects.filter(user=request.user).latest('order_date'),
                    product=item.product,
                    quantity=item.quantity, 
                    total=item.total
                )
            item.delete()
        return redirect('order_success')


def contact(request):
    return render(request,"contact.html")

def testimonial(request):
    return render(request,"testimonial.html")

def shop_detail(request):  
    return render(request,"shop-detail.html")

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


