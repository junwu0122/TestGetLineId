import os
import sys
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 首頁 (讓 Render 健康檢查過關)
@app.route("/", methods=['GET'])
def index():
    return "Group ID Grabber: Online", 200

line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    
    # 保留暴力 Log，以防萬一
    print(f"--- Webhook Data ---\n{body}")
    sys.stdout.flush()

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 判斷來源：如果是群組就抓 GroupID，如果是多人聊天室就抓 RoomID
    source_type = event.source.type
    target_id = "未知"
    
    if source_type == "group":
        target_id = event.source.group_id
    elif source_type == "room":
        target_id = event.source.room_id
    else:
        target_id = event.source.user_id

    # 邏輯：Bot 直接在 LINE 裡面噴出 ID
    reply_text = f"✅ 抓到 ID 了！\n類型: {source_type}\nID: {target_id}"
    
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )
    
    # 同步印在 Render Logs
    print(f"\n[SUCCESS] {reply_text}\n")
    sys.stdout.flush()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
