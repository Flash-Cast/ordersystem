# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from .models import MenuItem, Order, OrderItem
from django.views.decorators.csrf import csrf_exempt # 実運用ではCSRF保護を有効にしてください
from django.http import HttpResponse
from openpyxl import Workbook, load_workbook
import os
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.db import transaction # トランザクションのために追加

# Excel関連の定数
EXCEL_FILE_NAME = 'orders.xlsx'
EXCEL_SHEET_NAME = "注文履歴"
EXCEL_HEADERS = ["整理番号", "注文日時", "品目", "数量", "小計"]

def _get_or_create_orders_workbook():
    """
    注文履歴Excelファイルを取得または新規作成し、ワークブックとワークシートを返す。
    """
    excel_path = os.path.join(settings.BASE_DIR, EXCEL_FILE_NAME)
    if not os.path.exists(excel_path):
        wb = Workbook()
        ws = wb.active
        ws.title = EXCEL_SHEET_NAME
        ws.append(EXCEL_HEADERS)
    else:
        wb = load_workbook(excel_path)
        if EXCEL_SHEET_NAME not in wb.sheetnames:
            ws = wb.create_sheet(EXCEL_SHEET_NAME)
            ws.append(EXCEL_HEADERS) # 新規シートの場合もヘッダーを追加
        else:
            ws = wb[EXCEL_SHEET_NAME]
    return wb, ws, excel_path

def menu_list(request):
    items = MenuItem.objects.all()
    return render(request, 'menu/menu_list.html', {'items': items})

def order_confirm(request):
    if request.method == 'POST':
        items = MenuItem.objects.all()
        order_items = []
        total = 0

        for item in items:
            quantity_str = request.POST.get(f'quantity_{item.id}', '0')
            try:
                qty = int(quantity_str)
                if qty < 0: # マイナス数量は0として扱う
                    qty = 0
            except ValueError:
                qty = 0 # 数値に変換できない場合は0として扱う
            
            if qty > 0:
                subtotal = item.price * qty
                order_items.append({
                    'id': item.id,
                    'name': item.name,
                    'price': item.price,
                    'quantity': qty,
                    'subtotal': subtotal
                })
                total += subtotal

        if not order_items:
            # 何も選択されていない場合はメッセージと共にメニューリストに戻すなどの処理も検討可能
            return redirect('menu_list') 

        return render(request, 'menu/order_confirm.html', {
            'order_items': order_items,
            'total': total
        })

    return redirect('menu_list')

@csrf_exempt # 注意: これはテスト用です。実運用ではPOSTリクエストにCSRFトークンを含めてください。
@transaction.atomic # データベース操作をアトミックにする
def order_submit(request):
    if request.method == 'POST':
        items = MenuItem.objects.all() # 効率化の余地あり: 必要なItemのみ取得する
        
        # 注文データ作成 (total_priceは後で更新)
        order = Order.objects.create(total_price=0) 
        current_total = 0
        order_created_items = [] # Excel出力用に注文されたアイテムを一時保存

        for item in items:
            quantity_str = request.POST.get(f'quantity_{item.id}', '0')
            try:
                qty = int(quantity_str)
                if qty < 0: qty = 0
            except ValueError:
                qty = 0

            if qty > 0:
                OrderItem.objects.create(order=order, item=item, quantity=qty)
                current_total += item.price * qty
                order_created_items.append({
                    'name': item.name,
                    'quantity': qty,
                    'subtotal': item.price * qty
                })

        if not order_created_items: # 何も注文されなかった場合
            # orderオブジェクトは作成されてしまっているが、total_price=0のまま。
            # この注文を削除するか、このシナリオを許容するかは設計次第。
            # ここでは、空の注文が作成されるのを防ぐためにリダイレクト。
            # (もしOrder作成前にチェックするなら、ループを2回回すか、POSTデータを先に処理する必要がある)
            # より良いのは、order_confirmから渡されるデータ構造を見直し、
            # 実際に注文するアイテムIDと数量のリストのみをPOSTで受け取ること。
            return HttpResponse("注文アイテムが選択されていません。 <a href=\"/\">戻る</a>")


        order.total_price = current_total
        order.save()

        # Excel出力処理
        wb, ws, excel_path = _get_or_create_orders_workbook()

        # 注文ごとに記録
        order_time_str = order.created_at.strftime("%Y-%m-%d %H:%M:%S")
        for created_item in order_created_items:
            ws.append([
                order.id,
                order_time_str,
                created_item['name'],
                created_item['quantity'],
                created_item['subtotal']
            ])
        
        # 合計金額行
        ws.append(["合計", "", "", "", order.total_price])
        ws.append([])  # 空行で区切る

        wb.save(excel_path)

        return HttpResponse(f"""
            <h2>ご注文ありがとうございます！</h2>
            <h2>整理番号: {order.id}</h2>
            <p>合計金額: {order.total_price}円</p>
            <a href="/">戻る</a>
        """)

    return HttpResponse("無効なアクセスです。POSTメソッドで注文してください。 <a href=\"/\">戻る</a>")

@login_required
def order_list(request):
    orders = Order.objects.all().order_by('-created_at')  # 新しい順に表示
    return render(request, 'menu/order_list.html', {'orders': orders})

@login_required
@csrf_exempt # 注意: CSRF保護を検討してください。
@transaction.atomic
def complete_order(request, order_id):
    # order = Order.objects.get(id=order_id) # DoesNotExist例外の可能性
    order = get_object_or_404(Order, id=order_id) # 存在しない場合は404エラー

    if order.completed_at: # 既に完了している場合は何もしない（冪等性）
        return redirect('order_list')

    order.completed_at = timezone.now()
    order.save()

    # Excelファイル更新
    wb, ws, excel_path = _get_or_create_orders_workbook()
    
    # 完了情報を追記 (ヘッダーの5列に合わせる)
    # [整理番号, 日時(完了日時), 品目(完了ステータス), 数量(空), 小計(注文総額)]
    ws.append([
        order.id,
        order.completed_at.strftime("%Y-%m-%d %H:%M:%S"),
        "【注文完了】", # 品目の列に完了ステータスを記載
        "", # 数量は該当なし
        order.total_price # 小計の列に注文総額を記載 (参考情報として)
    ])
    ws.append([]) # 空行で区切る

    wb.save(excel_path)

    return redirect('order_list')

def custom_logout(request):
    logout(request)
    return redirect('menu_list')