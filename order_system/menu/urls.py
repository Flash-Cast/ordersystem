from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .forms import CustomLoginForm 

app_name = 'menu' # この行を追加

urlpatterns = [
    path('', views.menu_list, name='menu_list'),
    path('order/confirm/', views.order_confirm, name='order_confirm'),
    path('order/submit/', views.order_submit, name='order_submit'),
    #販売者ページ
    path('orders/', views.order_list, name='order_list'),
    path('complete/<int:order_id>/', views.complete_order, name='complete_order'),
    #販売者ログインログアウト
    path('login/', auth_views.LoginView.as_view(template_name='menu/login.html',authentication_form=CustomLoginForm,redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='menu:menu_list'), name='logout'),
    # API
    path('api/latest-orders/', views.latest_orders_api, name='latest_orders_api'),
    
    # --- ここからCSVエクスポート用のURLを追加 ---
    path('export/orders/', views.export_orders_csv, name='export_orders'),
    path('export/sales/', views.export_sales_csv, name='export_sales'),
    # --- ここからリセット用のURLを追加 ---
    path('orders/reset/', views.reset_orders, name='reset_orders'),
    # --- ここから手動注文入力用のURLを追加 ---
    path('orders/new/', views.staff_order_entry, name='staff_order_entry'),
]