from django.urls import path, include
from . import views
from . import hooks

urlpatterns = [
   
   path('place_order/', views.place_order, name='place_order'),
   # path('payments/', views.payments, name='payments'),
   path('payment_success/', views.payment_success, name='payment_success'),
   path('payment_failed/', views.payment_failed, name='payment_failed'),
   path('paypal/', include('paypal.standard.ipn.urls')),
   path('create_checkout_session', views.create_checkout_Session, name='create_checkout_session'),
   path('stripe_webhook', hooks.stripe_webhook, name='stripe_webhook')
] 
