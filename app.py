import os
import sys
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
# 修正處：加入了 TextSendMessage
from linebot.models import MessageEvent, TextMessage, MemberJoinedEvent, TextSendMessage

app = Flask(__name__)

# 從環境變數讀取
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

# 功能 1：抓取發言者與群組 ID
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    group_id = getattr(event.source, 'group_id', 'N/A')
    print(f"!!! 抓到 ID !!!\nUser ID: {user_id}\nGroup ID: {group_id}")
    sys.stdout.flush() # 確保 Log 立即顯示在 Render

# 功能 2：有人加入群組時抓 ID
@handler.add(MemberJoinedEvent)
def handle_member_joined(event):
    for member in event.joined.members:
        print(f"!!! 新成員加入 !!!\nUser ID: {member.user_id}")
    sys.stdout.flush()

# 測試路由：主動推播訊息到群組
@app.route("/test-push")
def test_push():
    # 這是你剛才抓到的 Group ID
    target_id = "C15e3e1094ff40afd0c843bbd6a14e384" 
    try:
        line_bot_api.push_message(
            target_id,
            TextSendMessage(text="🚨 測試推播：監視系統連線正常！\n目前設備地點：Render 測試環境")
        )
        return "<h1>推播成功！</h1><p>請檢查您的 Line 群組訊息。</p>"
    except Exception as e:
        return f"<h1>推播失敗</h1><p>錯誤原因：{e}</p>"

if __name__ == "__main__":
    # Render 會提供 PORT 環境變數
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
