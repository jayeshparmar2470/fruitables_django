from django.contrib import admin
from django.urls import path
from . import views
urlpatterns = [
    path("",views.home,name="home"),
    path("shop/",views.shop,name="shop"),
    path("cart/",views.cart,name="cart"),
    path("checkout/",views.checkout,name="checkout"),
    path("contact/",views.contact,name="contact"),
    path("testimonial/",views.testimonial,name="testimonial"),
    path("shop-detail/",views.shop_detail,name="shop_detail"),
    path("error/",views.error,name="error"),
]