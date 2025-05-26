from django.db import models
# from django.contrib.auth.models import User
# Create your models here.
from django.conf import settings  # For referencing the custom user model
from django.utils.text import slugify

class Product(models.Model):
    name = models.CharField(max_length=40)
    price = models.DecimalField(decimal_places=2, max_digits=10)
    image = models.ImageField(upload_to='images/')
    desc = models.TextField(max_length=150)
    category = models.ForeignKey('category', on_delete=models.CASCADE, default=1,related_name='products')
    star=models.IntegerField(default=0)
    slug = models.SlugField( unique=True,blank=True,null=True)  # Slug field for SEO-friendly URLs
    # Add these NEW fields (all optional to prevent breaks)
    is_organic = models.BooleanField(default=False)  # For your template
    is_featured = models.BooleanField(default=False)  # For homepage sections
    is_bestseller = models.BooleanField(default=False)  # For bestseller tabs

    
    keywords = models.TextField(blank=True, help_text="Comma-separated search terms")
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        # Auto-generate keywords if empty
        if not self.keywords:
            self.keywords = f"{self.name},{self.category.name}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class category(models.Model):
    name= models.CharField(max_length=40)

    def __str__(self):
        return self.name


class addtocart(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE,related_name='product')
    quantity = models.IntegerField(default=1)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,on_delete=models.SET_NULL)

    # user = models.ForeignKey(User, on_delete=models.CASCADE)  # set built-in User as foreign key
    total=models.DecimalField(max_digits=10,decimal_places=2,default=0.00)

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"

    def save(self,*args,**kwargs):
        self.total=self.quantity * self.product.price
        super().save(*args,**kwargs)

class Shippingfee(models.Model):
    zip_code = models.PositiveBigIntegerField(default=380015)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    local_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"ship_fee={self.shipping_fee} for {self.zip_code}"

class Billingaddress(models.Model):
    # user = models.ForeignKey(User, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,null=True, blank=True, on_delete=models.SET_NULL)

    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    phone=models.CharField(max_length=15, blank=True, null=True)
    email=models.EmailField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100,default='ahmedabad')
    state = models.CharField(max_length=100,default='gujarat')
    country = models.CharField(max_length=100, default='India')
    shippingfee=models.ForeignKey(Shippingfee, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.city}"



class Order(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('razorpay', 'Razorpay'),
    ]

    # user = models.ForeignKey(User, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,null=True, blank=True, on_delete=models.SET_NULL)

    billing_address = models.ForeignKey(Billingaddress, on_delete=models.CASCADE,null=True, blank=True)
    order_date = models.DateTimeField(auto_now_add=True)

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cod'  # Default to COD for existing orders
    )
    payment_status = models.CharField(
        max_length=20,
        default='pending'  # Add this field if you want to track payment status
    )
    payment_id = models.CharField(max_length=100, blank=True, null=True)  

        
    @property
    def subtotal(self):
        """Calculate sum of all order items"""
        return self.items.aggregate(total=models.Sum('total'))['total'] or Decimal('0.00')
    
    @property
    def shipping_cost(self):
        """Calculate shipping fees"""
        if hasattr(self.billing_address, 'shippingfee'):
            return (
                self.billing_address.shippingfee.shipping_fee + 
                self.billing_address.shippingfee.local_fee
            )
        return Decimal('0.00')
    
    @property
    def total(self):
        """Calculate grand total"""
        return self.subtotal + self.shipping_cost
        

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"
    
    

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    total=models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.product.name} x {self.quantity} by {self.order.user.username} for order {self.order.id}"
    
class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')  # Prevent duplicate items
        ordering = ['-added_date']

    def __str__(self):
        return f"{self.user.username}'s wishlist: {self.product.name}"    

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Review by {self.user.username} for {self.product.name}"

# from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin



class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        if not username:
            raise ValueError("Username is required")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, email, password, **extra_fields)




class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)  # must be unique since it's the login field
    full_name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'username'  # 🔑 login with username
    REQUIRED_FIELDS = ['email', 'full_name']  # 🔧 prompted in createsuperuser
    EMAIL_FIELD = 'email'  # 📩 used by Django for sending emails

    objects = UserManager()

    
    # Add these at the bottom of your model class:
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name="fruitapp_user_set",  # Unique related_name
        related_query_name="fruitapp_user",
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="fruitapp_user_set",  # Unique related_name
        related_query_name="fruitapp_user",
    )

    def __str__(self):
        return self.username

