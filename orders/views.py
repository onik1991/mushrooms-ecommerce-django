from django.shortcuts import render, redirect
from django.http import HttpResponse
from carts.models import CartItem, Cart
from .forms import OrderForm
from .models import Order, Payment, OrderProduct
import datetime 
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from paypal.standard.forms import PayPalPaymentsForm
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .hooks import stripe_webhook, paypal_payment_received
import uuid
import requests
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

# Create your views here.
# def payments(request):
 
# def _order_number(request):
#     order_number = request.session.session_key
#     if not order_number:
#         order_number = request.session.create()
#     return order_number



def place_order(request, total=0, quantity=0):
    current_user = request.user
    
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')
    
    grand_total = 0
    tax = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity
    tax = (20 * total)/100
    grand_total = total + tax 
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.email = form.cleaned_data['email']
            data.phone = form.cleaned_data['phone']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.city = form.cleaned_data['city']
            data.county = form.cleaned_data['county']
            data.postcode = form.cleaned_data['postcode']
            data.country = form.cleaned_data['country']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()

            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr,mt,dt)
            current_date = d.strftime("%Y%m%d")
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()
            request.session['order_number']=order_number

            order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)

            host = request.get_host()
            
            
            paypal_dict = {
                'business': settings.PAYPAL_RECEIVER_EMAIL,
                'amount': grand_total,
                'item_name': order_number,
                'invoice': order_number,
                'currency_code': 'GBP',
                # 'image_url': '',

                'notify_url': 'https://{}{}'.format(host, reverse("paypal-ipn")),
                'return_url': 'https://{}{}'.format(host, reverse("payment_success")),
                'cancel_url': 'https://{}{}'.format(host, reverse("payment_failed")),
            }

            paypal_button = PayPalPaymentsForm(initial=paypal_dict)
           
            context = {
                'order': order,
                'cart_items': cart_items,
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
                'paypal_button': paypal_button,
            }

            return render(request, 'orders/payments.html', context) 
    else:
        return redirect('checkout')
    
    
@login_required 
@csrf_exempt
def create_checkout_Session(request):
    if request.method == 'POST':
        order_number = request.session['order_number']
        order = Order.objects.get(order_number=order_number)
        order_total = order.order_total
        email = order.email

        stripe_checkout_session = stripe.checkout.Session.create(
            customer_email=email,
            payment_method_types=["card"],
            line_items = [
                {
                "price_data":{
                    "currency":"GBP",
                    "product_data":{
                        "name": order.order_number,
                    },
                    "unit_amount": int(order_total * 100),
                    },
                "quantity":1
                }    
            ],
            metadata = {
                "order_number": order.order_number
                },
            mode="payment",
            success_url= request.build_absolute_uri(reverse('payment_success')) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url= request.build_absolute_uri(reverse('payment_failed')),
            
        )
        return redirect(stripe_checkout_session.url)
    
   
def payment_success(request):
    order_number = request.session['order_number']
    

    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        payment_id = order.payment
        payment_object = Payment.objects.get(payment_id=payment_id)
        order_date = order.created_at
        payment_status = payment_object.status
        name = order.full_name
        address = order.full_address
        city = order.city
        county = order.county
        postcode = order.postcode
        country = order.country
        ordered_products = OrderProduct.objects.filter(order_id=order.id)
        sub_total = 0
        for i in ordered_products:
            sub_total += i.product_price * i.quantity
        tax = order.tax
        total = payment_object.amount_paid
        context = {
            'order': order,
            'ordered_products': ordered_products,
            'order_number': order.order_number,
            'payment_id': payment_id,
            'order_date': order_date,
            'payment_status': payment_status,
            'name': name,
            'address': address,
            'city': city,
            'county': county,
            'postcode': postcode,
            'country': country,
            'sub_total': sub_total,
            'tax': tax,
            'total': total,
        }
        return render (request, 'orders/payment_success.html', context)
    except:
        return render(request, 'orders/payment_failed.html')

    

def payment_failed(request):
    return render(request, 'orders/payment_failed.html')


