from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from .models import MenuItem
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from .models import MenuItem, Order, OrderItem
from openpyxl import Workbook, load_workbook
import os
from django.conf import settings

def menu_list(request):
    items = MenuItem.objects.all()
    return render(request, 'menu/menu_list.html', {'items': items})

@csrf_exempt  # テスト用。実運用ではPOSTにcsrf_tokenをつけてください。
def order_create(request):
    if request.method == 'POST':
        items = MenuItem.objects.all()
        order = Order.objects.create(total_price=0)
        total = 0

        for item in items:
            qty = int(request.POST.get(f'quantity_{item.id}', 0))
            if qty > 0:
                OrderItem.objects.create(order=order, item=item, quantity=qty)
                total += item.price * qty

        order.total_price = total
        order.save()

        # Excel出力処理
        excel_path = os.path.join(settings.BASE_DIR, 'orders.xlsx')

        if not os.path.exists(excel_path):
            wb = Workbook()
            ws = wb.active
            ws.title = "注文履歴"
            ws.append(["整理番号", "注文日時", "品目", "数量", "小計"])
        else:
            wb = load_workbook(excel_path)
            ws = wb["注文履歴"]

        # 注文ごとに記録
        for item in order.orderitem_set.all():
            ws.append([
                order.id,
                order.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                item.item.name,
                item.quantity,
                item.item.price * item.quantity
            ])

        # 合計金額行
        ws.append(["合計", "", "", "", total])
        ws.append([])  # 空行で区切る

        wb.save(excel_path)

        return HttpResponse(f"""
            <h2>ご注文ありがとうございます！</h2>
            <p>整理番号: {order.id}</p>
            <p>合計金額: {total}円</p>
            <a href="/">戻る</a>
        """)

    return HttpResponse("無効なアクセスです")
