from paypal.standard.models import ST_PP_COMPLETED
from paypal.standard.ipn.signals import valid_ipn_received
from django.dispatch import receiver
import stripe
from django.conf import settings

from .models import Order, Payment, OrderProduct
from carts.models import Cart, CartItem
from store.models import Product

from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from django.http import HttpResponse

from django.template.loader import render_to_string
from django.core.mail import EmailMessage


@receiver(valid_ipn_received)
def paypal_payment_received(sender, **kwargs):
    
    paypal_obj = sender
    my_invoice = str(paypal_obj.invoice)
    txn_id = str(paypal_obj.txn_id)
    payment_type = str(paypal_obj.payment_type)
    gross_amount = str(paypal_obj.mc_gross)
    payment_status = str(paypal_obj.payment_status)
    my_order = Order.objects.get(order_number=my_invoice)
    
    payment = Payment(
        user = my_order.user,
        payment_id = txn_id,
        payment_method = "paypal",
        amount_paid = gross_amount,
        status = payment_status,
    )
    payment.save()

    my_order.payment = payment
    my_order.is_ordered = True
    my_order.save()
    
    user = my_order.user
    cart_items = CartItem.objects.filter(user=user)

    for item in cart_items:
        orderproduct = OrderProduct()
        orderproduct.order_id = my_order.id
        orderproduct.payment = payment
        orderproduct.user_id = user.id
        orderproduct.product_id = item.product.id
        orderproduct.quantity = item.quantity
        orderproduct.product_price = item.product.price
        orderproduct.ordered = True
        orderproduct.save()

        cart_item = CartItem.objects.get(id=item.id)
        product_variation = cart_item.variations.all()
        orderproduct = OrderProduct.objects.get(id=orderproduct.id)
        orderproduct.variations.set(product_variation)
        orderproduct.save()

    product = Product.objects.get(id=item.product_id)
    product.stock -= item.quantity
    product.save()

    delete_cart = CartItem.objects.filter(user=user)
    delete_cart.delete()

    mail_subject = 'Thank you for your oder'
    message = render_to_string('orders/order_received_email.html', {
        'user': user,
        'order': my_order,
    })
    to_email = my_order.email
    send_email = EmailMessage(mail_subject, message, to=[to_email])
    send_email.send()

        
@require_POST
@csrf_exempt
def stripe_webhook(request):
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
        payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    if (
        event['type'] == 'checkout.session.completed'
        or event['type'] == 'checkout.session.async_payment_succeeded'
    ):
        
        session = event['data']['object']
        checkout_session_id = session.get('id')
        amount_total = session.get('amount_total')
        status  = session.get('status')
        order_number = session['metadata']['order_number']
        order = Order.objects.get(order_number=order_number)
      

        payment = Payment(
            user = order.user,
            payment_id = checkout_session_id,
            payment_method = "stripe",
            amount_paid = (amount_total/100),
            status = status,
        )
        payment.save()

        order.payment = payment
        order.is_ordered = True
        order.save()

        user = order.user
    cart_items = CartItem.objects.filter(user=user)

    for item in cart_items:
        orderproduct = OrderProduct()
        orderproduct.order_id = order.id
        orderproduct.payment = payment
        orderproduct.user_id = user.id
        orderproduct.product_id = item.product.id
        orderproduct.quantity = item.quantity
        orderproduct.product_price = item.product.price
        orderproduct.ordered = True
        orderproduct.save()

        cart_item = CartItem.objects.get(id=item.id)
        product_variation = cart_item.variations.all()
        orderproduct = OrderProduct.objects.get(id=orderproduct.id)
        orderproduct.variations.set(product_variation)
        orderproduct.save()

    product = Product.objects.get(id=item.product_id)
    product.stock -= item.quantity
    product.save()

    delete_cart = CartItem.objects.filter(user=user)
    delete_cart.delete()

    mail_subject = 'Thank you for your oder'
    message = render_to_string('orders/order_received_email.html', {
        'user': user,
        'order': order,
    })
    to_email = order.email
    send_email = EmailMessage(mail_subject, message, to=[to_email])
    send_email.send()
    
    return HttpResponse(status=200)