// static/js/order_list_realtime.js

document.addEventListener('DOMContentLoaded', function() {
    const scriptData = document.getElementById('realtime-script-data');
    if (!scriptData) {
        console.error("Script data element not found. Realtime updates disabled.");
        return;
    }

    const API_URL = scriptData.dataset.latestOrdersApiUrl;
    const CSRF_TOKEN = scriptData.dataset.csrfToken;
    const orderTableBody = document.getElementById('order-table-body');
    const noOrdersMessage = document.getElementById('no-orders-message');

    if (!orderTableBody) {
        console.error("Order table body element not found. Realtime updates cannot start.");
        return;
    }

    /**
     * 新しい注文行のHTML文字列を生成する関数
     * @param {object} order - 注文データ
     * @returns {string} - 生成されたHTML文字列
     */
    function createOrderRowHtml(order) {
        const manualClass = order.entry_method === 'manual' ? 'is-manual' : '';
        const completedClass = order.is_completed ? 'is-completed' : '';

        // ↓↓↓ この statusHtml の生成ロジックを修正します ↓↓↓
        let statusHtml = '';
        if (order.is_completed) {
            statusHtml = `
                <span class="status-badge status-badge--completed">${order.status_display}</span>
                <span class="completion-time">(${order.completed_at_formatted})</span>
            `;
        } else {
            statusHtml = `<span class="status-badge status-badge--pending">${order.status_display}</span>`;
        }

        const actionHtml = order.action_html.replace(/CSRF_TOKEN_PLACEHOLDER/g, CSRF_TOKEN);

        // returnするHTMLは変更なし
        return `
            <tr id="order-row-${order.id}" class="${manualClass} ${completedClass}">
                <td data-label="整理番号">${order.id}</td>
                <td data-label="注文日時">${order.created_at}</td>
                <td data-label="注文内容" class="order-items-cell">${order.items_details_html}</td>
                <td data-label="合計金額" class="text-right">${order.total_price_display}</td>
                <td data-label="状態" class="order-status-cell">${statusHtml}</td>
                <td data-label="操作" class="action-cell">${actionHtml}</td>
            </tr>
        `;
    }

    /**
     * APIから最新の注文を取得してテーブルを更新する関数
     */
    async function fetchLatestOrders() {
        try {
            const response = await fetch(`${API_URL}?last_order_id=${lastOrderId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            if (data.error) {
                throw new Error(`API Error: ${data.error}`);
            }

            if (data.orders && data.orders.length > 0) {
                // 「注文はありません」メッセージを非表示に
                if (noOrdersMessage) {
                    noOrdersMessage.style.display = 'none';
                }

                data.orders.forEach(order => {
                    // 重複表示をチェック
                    if (document.getElementById(`order-row-${order.id}`)) {
                        return;
                    }

                    const newRowHtml = createOrderRowHtml(order);
                    orderTableBody.insertAdjacentHTML('afterbegin', newRowHtml);

                    if (order.id > lastOrderId) {
                        lastOrderId = order.id;
                    }
                });
            }
        } catch (error) {
            console.error('Error fetching latest orders:', error);
        }
    }

    // --- 初期化処理 ---
    const orderRows = orderTableBody.querySelectorAll('tr');
    let lastOrderId = orderRows.length > 0 ?
        Math.max(...Array.from(orderRows).map(row => parseInt(row.id.replace('order-row-', '')))) :
        0;

    setInterval(fetchLatestOrders, 30000); // 30秒ごとに更新
    console.log("Realtime order updates initialized. Last Order ID on load:", lastOrderId);
});