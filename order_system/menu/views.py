from django.shortcuts import render, redirect, get_object_or_404
from .models import MenuItem, Order, OrderItem
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.db import transaction
import logging
from django.urls import reverse
import csv # csvモジュールをインポート
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

# --- Excel関連の関数 (_get_excel_workbook, _get_or_create_sheet_by_name) と定数はすべて削除 ---

def menu_list(request):
    items = MenuItem.objects.all()
    return render(request, 'menu/menu_list.html', {'items': items})

def order_confirm(request):
    if request.method == 'POST':
        items = MenuItem.objects.all()
        order_items_data = []
        total = 0
        for item in items:
            quantity_str = request.POST.get(f'quantity_{item.id}', '0')
            try:
                qty = int(quantity_str)
                if qty < 0: qty = 0
            except ValueError:
                qty = 0
            if qty > 0:
                subtotal = item.price * qty
                order_items_data.append({
                    'id': item.id,
                    'name': item.name,
                    'price': item.price,
                    'quantity': qty,
                    'subtotal': subtotal
                })
                total += subtotal
        if not order_items_data:
            return redirect('menu:menu_list')
        return render(request, 'menu/order_confirm.html', {
            'order_items': order_items_data,
            'total': total
        })
    return redirect('menu:menu_list')

@transaction.atomic
def order_submit(request):
    if request.method == 'POST':
        items = MenuItem.objects.all()
        # status はデフォルトで 'pending' になるので、total_price=0 だけでOK
        order = Order.objects.create(total_price=0)
        current_total = 0
        
        has_items = False # 注文アイテムがあるかどうかのフラグ
        for item_model in items:
            quantity_str = request.POST.get(f'quantity_{item_model.id}', '0')
            try:
                qty = int(quantity_str)
                if qty < 0: qty = 0
            except ValueError:
                qty = 0
            if qty > 0:
                has_items = True
                OrderItem.objects.create(order=order, item=item_model, quantity=qty)
                current_total += item_model.price * qty

        if not has_items:
            return HttpResponse("注文アイテムが選択されていません。 <a href=\"/\">戻る</a>")
        
        order.total_price = current_total
        order.save()

        # --- ここからExcelへの書き込み処理をすべて削除 ---

        context = {
            'order_id': order.id,
            'total_price': order.total_price,
            'user': request.user
        }
        return render(request, 'menu/order_complete.html', context)
    return HttpResponse("無効なアクセスです。POSTメソッドで注文してください。 <a href=\"/\">戻る</a>")

@login_required
def order_list(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'menu/order_list.html', {'orders': orders})

@login_required
@transaction.atomic
def complete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.status == 'pending': # 未完了の場合のみ更新
        order.status = 'completed'
        order.completed_at = timezone.now()
        order.save()

    # --- ここからExcelへの書き込み処理をすべて削除 ---

    return redirect('menu:order_list')

# --- latest_orders_api は変更なし (ただしstatusの表示を調整) ---
@login_required 
def latest_orders_api(request):
    last_order_id_str = request.GET.get('last_order_id')
    
    orders_queryset = Order.objects.none()

    if last_order_id_str and last_order_id_str.isdigit():
        last_order_id = int(last_order_id_str)
        orders_queryset = Order.objects.filter(id__gt=last_order_id).order_by('id')
    elif not last_order_id_str:
        return JsonResponse({'orders': []})
    else:
        return JsonResponse({'error': 'Invalid last_order_id format'}, status=400)

    orders_data = []
    for order in orders_queryset:
        items_details_list = [f"{item.item.name} x {item.quantity}" for item in order.orderitem_set.all()]
        
        # status の表示をモデルの get_status_display() を使うように変更
        status_display_text = order.get_status_display()
        if order.completed_at:
             status_display_text += f'（{order.completed_at.strftime("%Y-%m-%d %H:%M")}）'
        
        action_html_parts = []
        if order.status == 'pending':
            try:
                complete_url = reverse('complete_order', args=[order.id])
                complete_form_html = f'<form method="POST" action="{complete_url}" class="complete-order-form" style="display: inline-block; margin-right: 5px;"><input type="hidden" name="csrfmiddlewaretoken" value="CSRF_TOKEN_PLACEHOLDER"><button type="submit" class="btn btn-small btn-success">完了</button></form>'
                action_html_parts.append(complete_form_html)
            except Exception as e:
                logger.error(f"URLのreverseに失敗しました (complete_order): order.id={order.id}, エラー: {e}")
                action_html_parts.append("<span>完了操作不可</span>")
        else:
            action_html_parts.append('<span class="action-completed-icon">✔</span>')

        action_html_combined = f'<div style="display: flex; flex-wrap: wrap; gap: 5px; justify-content: center;">{" ".join(action_html_parts)}</div>'

        orders_data.append({
            'id': order.id,
            'created_at': order.created_at.strftime("%Y-%m-%d %H:%M"),
            'items_details_html': "<br>".join(items_details_list),
            'total_price_display': f"{order.total_price}円",
            'status_display': order.get_status_display(),
            'is_completed': bool(order.completed_at),
            'action_html': action_html_combined,
            'entry_method': order.entry_method, 
            'completed_at_formatted': order.completed_at.strftime("%H:%M") if order.completed_at else None,
        })

    return JsonResponse({'orders': orders_data})

@login_required
def export_orders_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    # 日本語のファイル名が文字化けしないように設定
    response['Content-Disposition'] = 'attachment; filename="orders_list.csv"'

    writer = csv.writer(response)
    # ヘッダー行を書き込み
    writer.writerow(['注文ID', '注文日時', '完了日時', '合計金額', 'ステータス', '注文内容'])

    orders = Order.objects.all().order_by('-created_at')
    for order in orders:
        # 注文内容を文字列として結合
        items_str = ", ".join([f"{oi.item.name}({oi.quantity}点)" for oi in order.orderitem_set.all()])
        writer.writerow([
            order.id,
            order.created_at.strftime("%Y-%m-%d %H:%M"),
            order.completed_at.strftime("%Y-%m-%d %H:%M") if order.completed_at else '',
            order.total_price,
            order.get_status_display(), # 'pending' -> '未完了' のように変換
            items_str,
        ])
    return response

@login_required
def export_sales_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'

    writer = csv.writer(response)
    # ヘッダー行を書き込み
    writer.writerow(['注文ID', '完了日時', '商品名', '単価', '数量', '小計'])

    # 完了した注文のみを対象
    completed_orders = Order.objects.filter(status='completed').order_by('completed_at')
    for order in completed_orders:
        for item in order.orderitem_set.all():
            writer.writerow([
                order.id,
                order.completed_at.strftime("%Y-%m-%d %H:%M"),
                item.item.name,
                item.item.price,
                item.quantity,
                item.item.price * item.quantity,
            ])
            
    return response

@login_required
@require_POST # POSTリクエストのみ受け付けるように制限
def reset_orders(request):
    """すべての注文と注文アイテムを削除するビュー"""
    try:
        # OrderItemはOrderに紐づいているため、Orderを削除すれば自動的に削除されます(on_delete=CASCADE)
        Order.objects.all().delete()
        # 成功メッセージなどを追加することも可能
    except Exception as e:
        logger.error(f"注文のリセット中にエラーが発生しました: {e}")
        # エラーメッセージなどを追加することも可能
    
    return redirect('menu:order_list')

@login_required
@transaction.atomic
def staff_order_entry(request):
    # GETリクエストの場合 (ページを最初に表示したとき)
    if request.method != 'POST':
        items = MenuItem.objects.all()
        return render(request, 'menu/staff_order_entry.html', {'items': items})

    # POSTリクエストの場合 (フォームが送信されたとき)
    items = MenuItem.objects.all()
    # statusはデフォルトで'pending'になる
    order = Order.objects.create(total_price=0, entry_method='manual')
    current_total = 0
    has_items = False

    for item_model in items:
        quantity_str = request.POST.get(f'quantity_{item_model.id}', '0')
        try:
            qty = int(quantity_str)
            if qty < 0: qty = 0
        except ValueError:
            qty = 0
        
        if qty > 0:
            has_items = True
            OrderItem.objects.create(order=order, item=item_model, quantity=qty)
            current_total += item_model.price * qty
    
    # 商品が一つも選択されていなかった場合
    if not has_items:
        order.delete() # 作成した空の注文を削除
        return render(request, 'menu/staff_order_entry.html', {
            'items': items,
            'error': '商品を1つ以上選択してください。'
        })

    order.total_price = current_total
    order.save()
    
    # 成功したら注文一覧ページにリダイレクト
    return redirect('menu:order_list')