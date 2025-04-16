from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request,"index.html")

def shop(request):
    return render(request,"shop.html")

def cart(request):
    return render(request,"cart.html")

def checkout(request):
    return render(request,"checkout.html")

def contact(request):
    return render(request,"contact.html")

def testimonial(request):
    return render(request,"testimonial.html")

def shop_detail(request):  
    return render(request,"shop-detail.html")

def error(request):
    return render(request,"404.html")
 


