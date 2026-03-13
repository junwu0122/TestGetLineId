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

# --- 1. 憑證設定 ---
CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# --- 2. 根目錄 ---
@app.route("/", methods=['GET'])
def index():
    return "Group ID Grabber: Online", 200

# --- 3. Webhook 接收端 ---
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    print(f"--- 接收到 Webhook ---\n{body}")
    sys.stdout.flush()
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# --- 4. 診斷推播 (關鍵修正區) ---
@app.route("/test-push", methods=['GET'])
def test_push():
    # ⚠️ 這裡填入妳抓到的 C 開頭 ID
    TARGET_ID = "C15e3e1094ff40afd0c843bbd6a14e384" 
    
    try:
        line_bot_api.push_message(
            TARGET_ID, 
            TextSendMessage(text="🚨 系統測試：Render 推播正常！")
        )
        return "<h1>推播發送成功！</h1>", 200
    except LineBotApiError as e:
        # 這裡所有的變數名稱都統一為 error_data，不會再噴 500
        error_data = {
            "status_code": e.status_code,
            "message": e.error.message,
            "details": e.error.details
        }
        print(f"❌ LINE API 報錯: {error_data}")
        sys.stdout.flush()
        return f"<h1>推播失敗 (400)</h1><pre>{json.dumps(error_data, indent=2, ensure_ascii=False)}</pre>", 400
    except Exception as e:
        print(f"❌ 系統崩潰: {str(e)}")
        sys.stdout.flush()
        return f"<h1>系統崩潰 (500)</h1><p>{str(e)}</p>", 500

# --- 5. 自動回報 ID ---
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    source_type = event.source.type
    target_id = getattr(event.source, f"{source_type}_id", "未知")
    result_text = f"✅ 辨識成功！\n類型: {source_type}\nID: {target_id}"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result_text))
    print(f"--- [ID 捕捉成功] ---\n{result_text}")
    sys.stdout.flush()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
