from django.contrib import admin
from .models import MenuItem, Order, OrderItem


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    readonly_fields = ['image_tag']
    list_display = ('name', 'price', 'image')

admin.site.register(Order)
admin.site.register(OrderItem)