import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, MemberJoinedEvent

app = Flask(__name__)

# 從環境變數讀取，不要寫死在程式碼中
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 核心功能：有人說話就抓 ID
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    group_id = getattr(event.source, 'group_id', 'N/A')
    print(f"!!! 抓到 ID !!!\nUser ID: {user_id}\nGroup ID: {group_id}")

# 核心功能：有人加入群組就抓 ID
@handler.add(MemberJoinedEvent)
def handle_member_joined(event):
    for member in event.joined.members:
        print(f"!!! 新成員加入 !!!\nUser ID: {member.user_id}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
