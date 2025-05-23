from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .forms import CustomLoginForm 

urlpatterns = [
    path('', views.menu_list, name='menu_list'),
    path('order/confirm/', views.order_confirm, name='order_confirm'),
    path('order/submit/', views.order_submit, name='order_submit'),
    #販売者ページ
    path('orders/', views.order_list, name='order_list'),
    path('complete/<int:order_id>/', views.complete_order, name='complete_order'),
    #販売者ログインログアウト
    path('login/', auth_views.LoginView.as_view(template_name='menu/login.html',authentication_form=CustomLoginForm,redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='menu_list'), name='logout'),
]