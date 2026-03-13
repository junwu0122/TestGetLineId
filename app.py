import os
import sys
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    SourceGroup, SourceRoom, JoinEvent
)

app = Flask(__name__)

# --- 1. 憑證設定 (務必確保 Render 環境變數已填寫) ---
CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

# 如果沒讀到變數，啟動時立刻報錯
if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    print("❌ 啟動失敗：請檢查 Render 環境變數是否包含 LINE_CHANNEL_ACCESS_TOKEN 與 LINE_CHANNEL_SECRET")
    sys.stdout.flush()

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# --- 2. 根目錄路由 (確認伺服器狀態與健康檢查) ---
@app.route("/", methods=['GET'])
def index():
    print("--- [訪問首頁] ---")
    sys.stdout.flush()
    return "Group ID Grabber: Online", 200

# --- 3. Webhook 核心接收端 ---
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    
    # 暴力列印所有 Webhook 內容，保證在 Log 裡一定能看到原始資料
    print("--- [接收到 Webhook 原始數據] ---")
    print(body)
    sys.stdout.flush()

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ 簽章驗證失敗，請檢查 CHANNEL_SECRET")
        sys.stdout.flush()
        abort(400)
    return 'OK'

# --- 4. 偵錯推播路徑 (解決 Uptime Kuma 400 錯誤的核心) ---
# 這個網址可以手動在瀏覽器打開： https://你的網址/test-push
@app.route("/test-push", methods=['GET'])
def test_push():
    # 💡 重要：請在此處填入你抓到的 C 開頭群組 ID
    # 如果還沒抓到，可以先填一個測試，或者等抓到後回來改
    TARGET_ID = "C15e3e1094ff40afd0c843bbd6a14e384" 
    
    print(f"--- [執行推播測試] 目標 ID: {TARGET_ID} ---")
    sys.stdout.flush()
    
    try:
        line_bot_api.push_message(
            TARGET_ID, 
            TextSendMessage(text="🚨 系統診斷測試：推播功能正常！")
        )
        return "<h1>推播發送成功！</h1><p>請確認您的 LINE 群組。</p>", 200
    except LineBotApiError as e:
        # 這裡是解決 Uptime Kuma 400 錯誤的關鍵資訊
        error_detail = {
            "status_code": e.status_code,
            "message": e.error.message,
            "details": e.error.details
        }
        print(f"❌ LINE API 報錯內容: {json.dumps(error_info, indent=2)}")
        sys.stdout.flush()
        # 網頁會直接印出 400 錯誤的具體原因
        return f"<h1>推播失敗 (400)</h1><pre>{json.dumps(error_detail, indent=2)}</pre>", 400
    except Exception as e:
        return f"<h1>系統錯誤</h1><p>{str(e)}</p>", 500

# --- 5. 自動回傳 ID 邏輯 ---
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    source_type = event.source.type
    target_id = "未知"
    
    # 判斷來源並提取 ID
    if isinstance(event.source, SourceGroup):
        target_id = event.source.group_id
    elif isinstance(event.source, SourceRoom):
        target_id = event.source.room_id
    else:
        target_id = event.source.user_id

    result_text = f"✅ 辨識成功！\n類型: {source_type}\nID: {target_id}"
    
    # 直接在 LINE 聊天室回覆
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=result_text)
    )
    
    # 同步輸出至 Render 日誌
    print(f"--- [ID 抓取成功] ---\n{result_text}")
    sys.stdout.flush()

# --- 6. 加入群組時自動報 ID ---
@handler.add(JoinEvent)
def handle_join(event):
    if event.source.type == "group":
        g_id = event.source.group_id
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"已加入群組！本群組 ID：\n{g_id}")
        )
        print(f"🚀 加入新群組，ID: {g_id}")
        sys.stdout.flush()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
