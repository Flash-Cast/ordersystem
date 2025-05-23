from django.db import models
from django.utils.html import format_html

class MenuItem(models.Model):
    name = models.CharField(max_length=100)
    price = models.IntegerField()
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='menu_images/', blank=True, null=True)

    def image_tag(self):
        if self.image:
            return format_html('<img src="{}" width="100" height="100" />', self.image.url)
        return "No Image"
    image_tag.short_description = '画像表示'
    
    def __str__(self):
        return f"{self.name}（{self.price}円）"

class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    total_price = models.IntegerField()
    completed_at = models.DateTimeField(null=True, blank=True) 

    def __str__(self):
        return f"注文 {self.id} - {self.total_price}円"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.IntegerField()
