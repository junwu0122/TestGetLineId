import os
import sys
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 根目錄，讓 Render 顯示健康
@app.route("/", methods=['GET'])
def index():
    return "Debug Mode: Online", 200

line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    
    # 只要有訊號進來，Log 一定會印出這一行
    print(f"--- 接收到訊號 ---")
    print(body)
    sys.stdout.flush()

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 取得發送者的 ID
    user_id = event.source.user_id
    
    # 取得群組或聊天室 ID (如果有)
    group_id = getattr(event.source, 'group_id', '非群組')
    room_id = getattr(event.source, 'room_id', '非聊天室')

    msg = f"抓到 ID 了！\n你的 UserID: {user_id}\n群組 ID: {group_id}\n聊天室 ID: {room_id}"
    
    # 讓 Bot 直接回話，妳在手機上就能看到
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
    
    print(msg)
    sys.stdout.flush()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
