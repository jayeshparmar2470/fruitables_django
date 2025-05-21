from django.db import models
# from django.contrib.auth.models import User
# Create your models here.
from django.conf import settings  # For referencing the custom user model

class Product(models.Model):
    name = models.CharField(max_length=40)
    price = models.DecimalField(decimal_places=2, max_digits=10)
    image = models.ImageField(upload_to='images/')
    desc = models.TextField(max_length=150)
    category = models.ForeignKey('category', on_delete=models.CASCADE, default=1,related_name='products')
    

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
    shippingfee=models.OneToOneField(Shippingfee, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.city}"



class Order(models.Model):
    # user = models.ForeignKey(User, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,null=True, blank=True, on_delete=models.SET_NULL)

    billing_address = models.ForeignKey(Billingaddress, on_delete=models.CASCADE,null=True, blank=True)
    order_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"
    
    

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    total=models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.product.name} x {self.quantity} by {self.order.user.username} for order {self.order.id}"
    

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

