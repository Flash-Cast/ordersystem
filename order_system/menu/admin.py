from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import MenuItem


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    readonly_fields = ['image_tag']
    list_display = ('name', 'price', 'image')

