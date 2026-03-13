import os
import sys
import json
from datetime import datetime
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    SourceGroup, SourceRoom, JoinEvent
)

app = Flask(__name__)

# --- [手動標記：部署版本] ---
# 每次修改代碼建議改一下這個時間，這樣妳打開網頁就能確認 Render 更新了沒
DEPLOY_VERSION = "2026-03-13 8787 (最新修正診斷版)"

# --- 1. 憑證設定與主動檢查 ---
CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

# 建立 API 物件
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN) if CHANNEL_ACCESS_TOKEN else None
handler = WebhookHandler(CHANNEL_SECRET) if CHANNEL_SECRET else None

# --- 2. 視覺化診斷首頁 ---
@app.route("/", methods=['GET'])
def index():
    # 檢查環境變數是否到位
    token_status = "✅ 已讀取" if CHANNEL_ACCESS_TOKEN else "❌ 缺失 (請檢查 Render 設定)"
    secret_status = "✅ 已讀取" if CHANNEL_SECRET else "❌ 缺失 (請檢查 Render 設定)"
    
    html_content = f"""
    <div style="font-family: sans-serif; padding: 20px; line-height: 1.6;">
        <h1 style="color: #00b900;">LINE Bot 診斷儀表板</h1>
        <hr>
        <p><strong>部署版本：</strong> <span style="color: blue;">{DEPLOY_VERSION}</span></p>
        <p><strong>伺服器時間：</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <div style="background: #f4f4f4; padding: 15px; border-radius: 8px;">
            <h3>環境變數狀態：</h3>
            <ul>
                <li>Access Token: {token_status}</li>
                <li>Channel Secret: {secret_status}</li>
            </ul>
        </div>
        <h3>功能測試路徑：</h3>
        <ul>
            <li><a href="/test-push">點此執行推播測試 (/test-push)</a></li>
            <li>Webhook 地址：<code>/callback</code></li>
        </ul>
        <p style="color: #666; font-size: 0.9em;">※ 如果妳修改了代碼但「部署版本」沒變，代表 Render 還在跑舊版。</p>
    </div>
    """
    return html_content, 200

# --- 3. Webhook 核心端點 ---
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    
    print(f"--- [Webhook 入站訊號] ---\n{body}")
    sys.stdout.flush()

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ 簽章驗證失敗")
        abort(400)
    except Exception as e:
        print(f"❌ Webhook 處理出錯: {e}")
    return 'OK'

# --- 4. 診斷推播 (解決 Uptime Kuma 400 錯誤) ---
@app.route("/test-push", methods=['GET'])
def test_push():
    # 💡 這裡填入妳抓到的 C 開頭 ID
    TARGET_ID = "C40b1192a7c468e4077ce58c296f149e9" 
    
    if not line_bot_api:
        return "<h1>錯誤</h1><p>找不到 Channel Access Token。</p>", 500

    try:
        line_bot_api.push_message(
            TARGET_ID, 
            TextSendMessage(text=f"🚨 診斷通報\n版本：{DEPLOY_VERSION}\n狀態：連線正常！")
        )
        return f"""
        <h1 style="color: green;">推播成功！</h1>
        <p>目標 ID: {TARGET_ID}</p>
        <p>請檢查您的 LINE 群組訊息。</p>
        <a href="/">回到儀表板</a>
        """, 200
    except LineBotApiError as e:
        # 詳細的錯誤資料
        error_data = {
            "HTTP 狀態碼": e.status_code,
            "LINE 錯誤訊息": e.error.message,
            "詳細定義": e.error.details
        }
        print(f"❌ 推播失敗: {error_data}")
        sys.stdout.flush()
        return f"""
        <h1 style="color: red;">推播失敗 (400)</h1>
        <p>這是 LINE 伺服器回傳的具體原因：</p>
        <pre style="background: #eee; padding: 10px;">{json.dumps(error_data, indent=2, ensure_ascii=False)}</pre>
        <p><strong>常見原因：</strong></p>
        <ul>
            <li>Bot 被踢出群組了 (請檢查群組成員)</li>
            <li>ID 填寫錯誤 (不是 C 開頭)</li>
            <li>免費訊息額度已用完</li>
        </ul>
        <a href="/">回到儀表板</a>
        """, 400
    except Exception as e:
        return f"<h1>系統崩潰 (500)</h1><p>{str(e)}</p>", 500

# --- 5. 自動識別 ID 與回覆 ---
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    source_type = event.source.type
    # 自動偵測來源 ID (可能是 userId, groupId, 或 roomId)
    target_id = getattr(event.source, f"{source_type}_id", "未知")
    
    response = f"✅ 辨識成功！\n類型: {source_type}\nID: {target_id}\n版本: {DEPLOY_VERSION}"
    
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))
    print(f"--- [ID 捕捉成功] ---\n{response}")
    sys.stdout.flush()

# --- 6. 加入群組時主動打招呼 ---
@handler.add(JoinEvent)
def handle_join(event):
    if event.source.type == "group":
        g_id = event.source.group_id
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"已加入群組！\n本群組 ID：\n{g_id}")
        )
        sys.stdout.flush()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
