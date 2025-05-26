# tests.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.conf import settings
from .models import Product, addtocart, Shippingfee, Billingaddress, Order, OrderItem, category
import json
from unittest.mock import patch, MagicMock
import razorpay
import unittest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from .views import razorpay_verify
from unittest.mock import patch, MagicMock
import razorpay


User = get_user_model()

# Helper function to create test image
def create_test_image():
    return SimpleUploadedFile(
        name='test_image.jpg',
        content=b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b',
        content_type='image/jpeg'
    )

# ======================
# Authentication Tests
# ======================
class AuthenticationTests(TestCase):
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'full_name': 'Test User',
            'password': 'testpass123'
        }
        self.user = User.objects.create_user(**self.user_data)
        self.client = Client()

    def test_valid_login(self):
        """Test login with correct credentials"""
        response = self.client.post(reverse('login'), {
            'username': self.user_data['username'],
            'password': self.user_data['password']
        })
        self.assertRedirects(response, reverse('home'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_invalid_login(self):
        """Test login with wrong password"""
        response = self.client.post(reverse('login'), {
            'username': self.user_data['username'],
            'password': 'wrongpassword'
        })
        self.assertContains(response, "Invalid username or password")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    @patch('requests.get')
    def test_valid_registration(self, mock_get):
        """Test successful user registration"""
        mock_get.return_value.json.return_value = {
            'is_valid_format': {'value': True},
            'deliverability': 'DELIVERABLE'
        }
        
        new_user = {
            'username': 'newuser',
            'email': 'new@example.com',
            'full_name': 'New User',
            'password': 'newpass123',
            'confirm_password': 'newpass123'
        }
        
        response = self.client.post(reverse('register'), new_user)
        self.assertRedirects(response, reverse('login'))
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_password_reset_flow(self):
        """Test complete password reset flow"""
        # Forgot password
        response = self.client.post(reverse('forgot_password'), {
            'email': self.user_data['email']
        })
        self.assertRedirects(response, reverse('verify_otp'))
        
        # Verify OTP
        otp = self.client.session['reset_otp']
        response = self.client.post(reverse('verify_otp'), {'otp': otp})
        self.assertRedirects(response, reverse('reset_password'))
        
        # Reset password
        new_password = 'newpassword123'
        response = self.client.post(reverse('reset_password'), {
            'password': new_password,
            'confirm': new_password
        })
        self.assertRedirects(response, reverse('login'))
        
        # Verify password change
        user = User.objects.get(username=self.user_data['username'])
        self.assertTrue(user.check_password(new_password))

# ======================
# Cart Functionality Tests
# ======================
class CartTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            full_name='Test User',
            password='testpass123'
        )
        self.test_category = category.objects.create(name='Fruits')
        self.product = Product.objects.create(
            name='Apple',
            price=100.00,
            category=self.test_category,
            image=create_test_image(),
            desc='Test description'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_add_to_cart(self):
        """Test adding product to cart"""
        response = self.client.get(reverse('add_to_cart', args=[self.product.id]))
        cart_item = addtocart.objects.filter(user=self.user, product=self.product).first()
        self.assertIsNotNone(cart_item)
        self.assertEqual(cart_item.quantity, 1)
        self.assertEqual(cart_item.total, 100.00)

    def test_remove_from_cart(self):
        """Test removing product from cart"""
        # Add item first
        self.client.get(reverse('add_to_cart', args=[self.product.id]))
        
        # Then remove it
        response = self.client.get(reverse('remove_from_cart', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(addtocart.objects.filter(user=self.user).exists())

    def test_quantity_updates(self):
        """Test cart item quantity adjustments"""
        # Initial add
        self.client.get(reverse('add_to_cart', args=[self.product.id]))
        cart_item = addtocart.objects.get(user=self.user, product=self.product)
        self.assertEqual(cart_item.quantity, 1)
        
        # Increase quantity
        self.client.get(f"{reverse('add_to_cart', args=[self.product.id])}?flag=plus")
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 2)
        self.assertEqual(cart_item.total, 200.00)
        
        # Decrease quantity
        self.client.get(reverse('add_to_cart', args=[self.product.id]))
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 1)
        self.assertEqual(cart_item.total, 100.00)

# ======================
# Checkout & Payment Tests
# ======================
class CheckoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            full_name='Test User',
            password='testpass123'
        )
        self.test_category = category.objects.create(name='Fruits')
        self.product = Product.objects.create(
            name='Apple',
            price=100.00,
            category=self.test_category,
            image=create_test_image(),
            desc='Test description'
        )
        self.shipping = Shippingfee.objects.create(
            zip_code=380015,
            shipping_fee=10.00,
            local_fee=5.00
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # Add item to cart
        addtocart.objects.create(
            user=self.user,
            product=self.product,
            quantity=1
        )
        
        # Set session data
        session = self.client.session
        session['zip_code'] = 380015
        session.save()

    def test_checkout_access(self):
        """Test checkout page loads with cart items"""
        response = self.client.get(reverse('checkout'))
        self.assertEqual(response.status_code, 200)
        
        # Check context contains cart items
        self.assertTrue('my_items' in response.context)
        self.assertEqual(len(response.context['my_items']), 1)
        self.assertEqual(response.context['my_items'][0].product.name, 'Apple')
        
        # Check rendered content
        self.assertContains(response, "Apple")
        self.assertContains(response, "100.00")

    def test_anonymous_checkout_redirect(self):
        """Test anonymous user is redirected to login"""
        self.client.logout()
        response = self.client.get(reverse('checkout'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('checkout')}")

    @patch('razorpay.Client')
    def test_razorpay_payment_success(self, mock_razorpay_client):
        # Setup test user
        self.client.force_login(self.user)
        
        # Setup Razorpay mock
        mock_client = MagicMock()
        mock_razorpay_client.return_value = mock_client
        mock_client.utility.verify_payment_signature.return_value = True
        
        # Setup shipping fee mock
        shipping_fee = Shippingfee.objects.create(zip_code='380015', shipping_fee=10.00, local_fee=5.00)
        
        # Create test cart items
        product = Product.objects.create(name="Test Product", price=10.00)
        addtocart.objects.create(user=self.user, product=product, quantity=1, total=10.00)
        
        # Make the request
        response = self.client.post(
            reverse('razorpay_verify'),
            data=json.dumps({
                'razorpay_order_id': 'order_test123',
                'razorpay_payment_id': 'pay_test123',
                'razorpay_signature': 'test_signature',
                'email': 'test@example.com',
                'phone': '1234567890',
                'first_name': 'Test',
                'last_name': 'User'
            }),
            content_type='application/json'
        )

          # Then make the form submission with all required fields
        form_response = self.client.post(reverse('place_order'), {
        'email': 'test@example.com',
        'phone': '1234567890',
        'address': 'Test Address',
        'city': 'Test City',
        'state': 'Test State',
        'country': 'Test Country',
        'zip_code': '380015',
        'payment_method': 'razorpay'
          })
            # Verify final redirect
        self.assertEqual(form_response.status_code, 302)
        self.assertRedirects(form_response, reverse('order_success'))

        
        # Verify order was created
        self.assertTrue(Order.objects.filter(user=self.user).exists())
    def test_order_placement(self):
        """Test manual order placement"""
        response = self.client.post(reverse('place_order'), {
            'email': 'test@example.com',
            'phone': '1234567890',
            'address': 'Test Address',
            'city': 'Test City',
            'state': 'Test State',
            'country': 'Test Country',
            'zip_code': '380015',
            'shippingfee': self.shipping.id  # Correct lowercase field name
        })
        
        self.assertRedirects(response, reverse('order_success'))
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)

# ======================
# Shipping Tests
# ======================
class ShippingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            full_name='Test User',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_shipping_details_creation(self):
        """Test shipping fee calculation for new zip code"""
        test_zip = 380015
        response = self.client.get(reverse('shipping_details', args=[test_zip]))
        shipping = Shippingfee.objects.get(zip_code=test_zip)
        self.assertTrue(5 <= shipping.shipping_fee <= 12)
        self.assertTrue(5 <= shipping.local_fee <= 12)
        self.assertRedirects(response, reverse('cart'))

# ======================
# Product Tests
# ======================
class ProductTests(TestCase):
    def setUp(self):
        self.test_category = category.objects.create(name='Fruits')
        self.product = Product.objects.create(
            name='Apple',
            price=100.00,
            category=self.test_category,
            image=create_test_image(),
            desc='Test description'
        )
        self.client = Client()

    def test_product_listing(self):
        """Test product listing page"""
        response = self.client.get(reverse('shop'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apple")

    def test_product_filtering(self):
        """Test category filtering"""
        response = self.client.get(f"{reverse('shop')}?cat=Fruits")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apple")

# ======================
# Test Suite Runner
# ======================
if __name__ == '__main__':
    unittest.main()