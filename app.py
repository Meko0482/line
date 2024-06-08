import logging
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, LocationMessage
import requests
import os

app = Flask(__name__)

# 直接在代码中硬编码 LINE Bot 的 Channel Access Token 和 Channel Secret
LINE_CHANNEL_ACCESS_TOKEN = 'EVJjdnTQ+p02Btrm/1iTYnFlKcuwbmcSDJSHb2HA/i7DiWMX0zLSito0mejJUmLjafYFdAKduaffBVAq0NIvKsMGLWwggUDdY1tnebNiPf5R9vW9Ns+QJitUTdeVNnNKQCr1VKRDhAJGFZrk3G7nhgdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = 'e9e71edac68e482a57c9d84c6a1862f3'

# 检查是否正确设置了 Channel Access Token 和 Channel Secret
if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    logging.error("LINE_CHANNEL_ACCESS_TOKEN 和 LINE_CHANNEL_SECRET 必须被设置.")
    raise ValueError("LINE_CHANNEL_ACCESS_TOKEN 和 LINE_CHANNEL_SECRET 必须被设置.")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    if event.message.text.lower() == "天氣":
        weather_info = fetch_weather_data("淡水")
        reply = f"淡水区的天气是：\n{weather_info}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

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
                station = next((s for s in data["records"]["Station"] if s["Parameter"]["parameterValue"] == city), None)
                if station:
                    weather_element = station["Parameter"]
                    weather = weather_element.get("parameterName", "N/A")
                    temperature = weather_element.get("parameterValue", "N/A")
                    humidity = weather_element.get("parameterName", "N/A")
                    return f"天氣: {weather}, 温度: {temperature}°C, 湿度: {humidity}%"
                else:
                    return f"找不到{city}區的天氣资料"
            else:
                return "無法獲取天氣信息。"
        else:
            return "無法獲取天气信息。"
    except Exception as e:
        return f"發生錯誤": {e}"

if __name__ == "__main__":
    app.run()
