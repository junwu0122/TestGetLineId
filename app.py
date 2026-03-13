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

# --- 1. 憑證設定 (從 Render 環境變數讀取) ---
CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

# 若環境變數未設定，啟動時直接在 Logs 噴錯
if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    print("❌ 錯誤：找不到環境變數 LINE_CHANNEL_ACCESS_TOKEN 或 LINE_CHANNEL_SECRET")
    sys.stdout.flush()

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# --- 2. 根目錄 (解決 Render 健康檢查與 404 問題) ---
@app.route("/", methods=['GET'])
def index():
    return "Group ID Grabber: Online", 200

# --- 3. Webhook 核心接收端 ---
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    
    # 暴力列印數據，確保在 Logs 能看到 JSON
    print(f"--- 接收到 Webhook ---\n{body}")
    sys.stdout.flush()

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ 簽章驗證失敗")
        sys.stdout.flush()
        abort(400)
    return 'OK'

# --- 4. 診斷推播路徑 (解決 Uptime Kuma 400 報錯的關鍵) ---
# 網址： https://你的網址/test-push
@app.route("/test-push", methods=['GET'])
def test_push():
    # 💡 這裡請務必確認填入的是你抓到的 C 開頭 ID
    TARGET_ID = "C15e3e1094ff40afd0c843bbd6a14e384" 
    
    try:
        line_bot_api.push_message(
            TARGET_ID, 
            TextSendMessage(text="🚨 系統測試通報：Render 推播功能正常！")
        )
        return "<h1>推播發送成功！</h1><p>請檢查群組訊息。</p>", 200
    except LineBotApiError as e:
        # 【已修正變數名稱】不再噴 500 錯誤
        error_payload = {
            "status_code": e.status_code,
            "message": e.error.message,
            "details": e.error.details
        }
        print(f"❌ LINE API 報錯: {error_payload}")
        sys.stdout.flush()
        # 網頁會顯示為何 400 (例如: "The property, 'to', is invalid")
        return f"<h1>推播失敗 (400)</h1><pre>{json.dumps(error_payload, indent=2, ensure_ascii=False)}</pre>", 400
    except Exception as e:
        print(f"❌ 系統層級崩潰: {str(e)}")
        sys.stdout.flush()
        return f"<h1>系統崩潰 (500)</h1><p>{str(e)}</p>", 500

# --- 5. 自動抓 ID 並回覆邏輯 ---
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
    
    # 回覆在 LINE
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=result_text)
    )
    
    # 印在 Logs
    print(f"--- [ID 捕捉成功] ---\n{result_text}")
    sys.stdout.flush()

# --- 6. 加入群組時主動通報 ---
@handler.add(JoinEvent)
def handle_join(event):
    if event.source.type == "group":
        g_id = event.source.group_id
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"已加入群組！本群組 ID：\n{g_id}")
        )
        sys.stdout.flush()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
