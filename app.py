import os
import sys
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, MemberJoinedEvent, TextSendMessage, JoinEvent

app = Flask(__name__)

# 1. 補上首頁路由，讓 Render 偵測 Port 時不會報 404
@app.route("/", methods=['GET'])
def index():
    return "Bot is Online!", 200

line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    
    # --- 強效偵錯：直接印出所有進來的 JSON ---
    print("--- 收到原始 Webhook 內容 ---")
    print(body)
    sys.stdout.flush() 
    # ---------------------------------------

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ 簽章驗證失敗，請檢查 Secret 是否正確")
        abort(400)
    return 'OK'

# 功能 1：當有人發訊息時（抓 ID 的最快方法）
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    source_type = event.source.type
    user_id = event.source.user_id
    
    print(f"--- 偵測到訊息事件 (來源類型: {source_type}) ---")
    
    if source_type == 'group':
        g_id = event.source.group_id
        print(f"✅ 抓到 Group ID: {g_id}")
        # 直接回覆在群組，你就不用一直看電腦 Log
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"群組 ID 是：\n{g_id}"))
    
    elif source_type == 'room':
        r_id = event.source.room_id
        print(f"✅ 抓到 Room ID: {r_id}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"多人聊天室 ID：\n{r_id}"))
    
    else:
        print(f"這是個人私訊，User ID: {user_id}")
    
    sys.stdout.flush()

# 功能 2：當 Bot 被加入群組時（主動抓 ID）
@handler.add(JoinEvent)
def handle_join(event):
    if event.source.type == "group":
        g_id = event.source.group_id
        print(f"🚀 Bot 已加入群組！ID: {g_id}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"感謝邀請！本群組 ID：\n{g_id}"))
    sys.stdout.flush()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
