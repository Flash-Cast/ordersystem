# Generated by Django 5.2.1 on 2025-05-16 01:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0002_order_orderitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='menuitem',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='menuitem',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='menu_images/'),
        ),
    ]
