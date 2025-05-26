from django.contrib import admin
from .models import Product,category,addtocart,Order,Billingaddress,Shippingfee,OrderItem,User, Review, Wishlist
# Register your models here.

admin.site.register(Product)
admin.site.register(category)
admin.site.register(addtocart)
admin.site.register(Order)
admin.site.register(Billingaddress)
admin.site.register(Shippingfee)
admin.site.register(OrderItem)
admin.site.register(Review)
admin.site.register(Wishlist)

# from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# from .models import User  # or from yourapp.models import User



class UserAdmin(BaseUserAdmin):
    ordering = ['id']
    list_display = ['username', 'email', 'is_staff']
    
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {'fields': ('full_name',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'full_name', 'password1', 'password2'),
        }),
    )
    
    search_fields = ['username', 'email']

admin.site.register(User, UserAdmin)
