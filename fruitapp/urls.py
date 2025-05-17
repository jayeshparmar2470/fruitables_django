from django.contrib import admin
from django.urls import path
from . import views
urlpatterns = [
    path("",views.home,name="home"),
    path("shop/",views.shop,name="shop"),
    path("cart/",views.cart,name="cart"),
    path("add_to_cart/<int:prod_id>",views.add_to_cart,name="add_to_cart"),
    path("remove_from_cart/<int:prod_id>",views.remove_from_cart,name="remove_from_cart"),
    path("shipping_details/<int:zip_code>",views.shipping_details,name="shipping_details"),
    path("checkout/",views.checkout,name="checkout"),
    path("place_order/",views.place_order,name="place_order"),
    path("contact/",views.contact,name="contact"),
    path("testimonial/",views.testimonial,name="testimonial"),
    path("shop-detail/",views.shop_detail,name="shop_detail"),
    path("error/",views.error,name="error"),
    
    path("login/",views.login_view,name="login"),
    path("register/",views.register,name="register"),   
    path("logout/",views.logout1,name="logout"),


    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),


    # urls.py
    path('razorpay/verify/', views.razorpay_verify, name='razorpay_verify'),
    path('order/success/', views.order_success, name='order_success'),
    
]