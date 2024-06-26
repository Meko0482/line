import sqlite3
import datetime
import threading
import logging
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, LocationMessage
import requests

app = Flask(__name__)

# LINE Bot 的 Channel Access Token 和 Channel Secret
LINE_CHANNEL_ACCESS_TOKEN = 'EVJjdnTQ+p02Btrm/1iTYnFlKcuwbmcSDJSHb2HA/i7DiWMX0zLSito0mejJUmLjafYFdAKduaffBVAq0NIvKsMGLWwggUDdY1tnebNiPf5R9vW9Ns+QJitUTdeVNnNKQCr1VKRDhAJGFZrk3G7nhgdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = 'e9e71edac68e482a57c9d84c6a1862f3'

# 建立主数据库连接
conn = sqlite3.connect('calendar.db', check_same_thread=False)
cursor = conn.cursor()

# 建立行事历数据库连接
calendar_conn = sqlite3.connect('calendar_events.db', check_same_thread=False)
calendar_cursor = calendar_conn.cursor()

# LINE Bot API 初始化
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 建立行事历事件表格（如果尚未创建）
calendar_cursor.execute('''
    CREATE TABLE IF NOT EXISTS calendar (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        date DATE NOT NULL
    )
''')
calendar_conn.commit()

# 新增备忘录事件
def add_event(username, title, date, time=None, location=None):
    cursor.execute('''
        INSERT INTO events (title, date, time, location, username)
        VALUES (?, ?, ?, ?, ?)
    ''', (title, date, time, location, username))
    conn.commit()

# 查詢备忘录事件
def get_events(username, date):
    cursor.execute('SELECT * FROM events WHERE date = ? AND username = ?', (date, username))
    return cursor.fetchall()

# 查詢行事历事件
def get_calendar_events(date):
    calendar_cursor.execute('SELECT * FROM calendar WHERE date = ?', (date,))
    return calendar_cursor.fetchall()

# 刪除备忘录事件
def delete_event(event_id, username):
    cursor.execute('DELETE FROM events WHERE id = ? AND username = ?', (event_id, username))
    conn.commit()

# 檢查並提醒事件
def check_reminder():
    today = datetime.date.today()
    calendar_events = get_calendar_events(str(today))
    for event in calendar_events:
        message = "提醒：今天有 '{}' 行事曆事件".format(event[1])
        line_bot_api.push_message(user[0], TextSendMessage(text=message))

    # 設置計時器，每天檢查一次
    threading.Timer(86400, check_reminder).start()  # 86400 秒 = 1 天

# LINE Bot 訊息處理
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 處理文字訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    user_id = event.source.user_id  # 获取用户ID
    if user_message == "1":
        reply_message = "請輸入日期（YYYY-MM-DD）："
    elif user_message.startswith('日期：'):
        date = user_message.split('：')[1]
        calendar_events = get_calendar_events(date)
        reply_message = "日期 {} 的行事曆事件如下：\n".format(date)
        if calendar_events:
            for event in calendar_events:
                reply_message += "{}\n".format(event[1])
        else:
            reply_message = "日期 {} 沒有任何行事曆事件。".format(date)
    elif user_message.lower() == "天氣":
        weather_info = fetch_weather_data("淡水")
        reply_message = f"淡水區的天氣是：\n{weather_info}"
    else:
        reply_message = "請輸入'1'來檢視行事曆事件，或者輸入'天氣'來查詢天氣資訊。"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

# 取得天氣資訊
def fetch_weather_data(city):
    # 氣象局 API 的 URL
    url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001?Authorization=CWA-7A752AE1-2953-4680-A2BA-6B1B13AAB708&format=JSON&StationId=466900"

    try:
        # 發送 GET 請求
        response = requests.get(url)

        # 檢查請求是否成功
        if response.status_code == 200:
            # 解析 JSON 回應
            data = response.json()

            # 提取並返回天氣資料
            if "records" in data and "Station" in data["records"]:
                station = data["records"]["Station"][0]  # 只取第一個城市的資料
                station_name = station["StationName"]
                weather_element = station["WeatherElement"]
                weather = weather_element.get("Weather", "N/A")
                temperature = weather_element.get("AirTemperature", "N/A")
                humidity = weather_element.get("RelativeHumidity", "N/A")
                return f"城市: {station_name}, 天氣: {weather}, 溫度: {temperature}, 濕度: {humidity}"
            else:
                return "無法取得天氣資訊。"
        else:
            return "無法取得天氣資訊。"
    except Exception as e:
        return f"發生錯誤: {e}"

# 主程式功能
def main():
    check_reminder()  # 啟動計時器
    app.run(debug=True)

if __name__ == "__main__":
    main()
