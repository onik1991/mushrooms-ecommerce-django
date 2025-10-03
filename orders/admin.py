from django.contrib import admin
from .models import Payment, Order, OrderProduct

# Register your models here.
class OrderProductInLine(admin.TabularInline):
    model = OrderProduct
    readonly_fields = ('payment', 'user', 'product', 'quantity', 'product_price', 'ordered')
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'full_name', 'email', 'phone', 'order_total', 'tax', 'is_ordered', 'status']
    list_filter = ['status', 'is_ordered']
    search_fields = ['order_number', 'phone', 'email', 'status']
    list_per_page = 20
    inlines = [OrderProductInLine]
   

admin.site.register(Payment)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderProduct)

def ready(self):
    import orders.hooks