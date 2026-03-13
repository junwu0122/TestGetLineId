import os
import sys
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    SourceGroup, SourceRoom, SourceUser, JoinEvent
)

app = Flask(__name__)

# --- 配置區：從環境變數讀取憑證 ---
# 這些變數必須在 Render 的 Dashboard -> Settings -> Environment Variables 設定
CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    print("❌ 錯誤：找不到環境變數 LINE_CHANNEL_ACCESS_TOKEN 或 LINE_CHANNEL_SECRET")
    sys.exit(1)

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# --- 1. 根目錄路由 (解決 Render 健康檢查與 404 問題) ---
@app.route("/", methods=['GET'])
def index():
    return "<h1>LINE Bot 測試伺服器已啟動</h1><p>請確認 Webhook 指向 /callback，測試推播請訪問 /test-push</p>", 200

# --- 2. Webhook 核心接收端 ---
@app.route("/callback", methods=['POST'])
def callback():
    # 獲取 Header 中的簽章，用於安全驗證
    signature = request.headers.get('X-Line-Signature')
    # 獲取請求主體
    body = request.get_data(as_text=True)
    
    # 在 Render Logs 中印出原始內容，方便暴力偵錯
    print(f"--- 收到原始 Webhook 數據 ---\n{body}")
    sys.stdout.flush()

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ 簽章驗證失敗，請檢查 CHANNEL_SECRET 是否填寫正確")
        abort(400)
    return 'OK'

# --- 3. 測試用推播邏輯 (用於驗證 Uptime Kuma 為何 400) ---
@app.route("/test-push", methods=['GET'])
def test_push():
    # 💡 請在此填入妳從 Log 抓到的 C 開頭群組 ID
    TARGET_ID = "C15e3e1094ff40afd0c843bbd6a14e384" 
    
    test_message = "🚨 系統測試通報\n狀態：連線正常\n來源：Render 診斷路徑"
    
    try:
        line_bot_api.push_message(TARGET_ID, TextSendMessage(text=test_message))
        return f"<h1>推播發送成功！</h1><p>目標 ID: {TARGET_ID}</p>", 200
    except LineBotApiError as e:
        # 詳細印出 LINE API 報錯的內容 (這就是找出 400 錯誤的核心)
        error_info = {
            "status_code": e.status_code,
            "message": e.error.message,
            "details": e.error.details
        }
        print(f"❌ LINE API 推播失敗: {error_info}")
        sys.stdout.flush()
        return f"<h1>推播失敗 (400/403)</h1><pre>{json.dumps(error_info, indent=2, ensure_ascii=False)}</pre>", e.status_code
    except Exception as e:
        return f"<h1>系統層級錯誤</h1><p>{str(e)}</p>", 500

# --- 4. 訊息處理邏輯：自動抓取並回覆所有類型的 ID ---
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 初始化 ID 資訊
    user_id = event.source.user_id
    group_id = None
    room_id = None
    source_type = event.source.type # user, group, or room

    # 邏輯判斷：根據來源類型提取對應 ID
    if isinstance(event.source, SourceGroup):
        group_id = event.source.group_id
        target_id = group_id
    elif isinstance(event.source, SourceRoom):
        room_id = event.source.room_id
        target_id = room_id
    else:
        target_id = user_id

    # 組合回覆訊息內容
    response_msg = (
        f"✅ 成功辨識來源！\n"
        f"類型：{source_type}\n"
        f"目前 ID：{target_id}\n"
        f"----------------\n"
        f"您的 UserID: {user_id}"
    )

    # 1. 透過 LINE 回覆給使用者
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=response_msg)
    )

    # 2. 同步印在 Render Logs
    print(f"--- [ID 捕捉成功] ---\n{response_msg}")
    sys.stdout.flush()

# --- 5. 當 Bot 加入群組時主動通報 ID ---
@handler.add(JoinEvent)
def handle_join(event):
    if event.source.type == "group":
        g_id = event.source.group_id
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"感謝邀請！本群組 ID：\n{g_id}")
        )
        print(f"🚀 Bot 加入了新群組: {g_id}")
        sys.stdout.flush()

if __name__ == "__main__":
    # Render 會自動配置環境變數 PORT
    port = int(os.environ.get("PORT", 5000))
    # 必須監聽 0.0.0.0 才能接收外部流量
    app.run(host="0.0.0.0", port=port)
