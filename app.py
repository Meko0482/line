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
        weather_info = get_weather_info()
        reply = f"您所在位置的天氣是：\n{weather_info}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

def get_weather_info():
    url = f"https://opendata.cwb.gov.tw/api/v1/rest/datastore/O-A0003-001?Authorization=CWB-7A752AE1-2953-4680-A2BA-6B1B13AAB708&format=JSON&locationName=新北市淡水區"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if "records" in data and "location" in data["records"]:
                location = data["records"]["location"][0]
                station_name = location["locationName"]
                weather_elements = {elem['elementName']: elem['elementValue'] for elem in location['weatherElement']}
                weather = weather_elements.get("Weather", "N/A")
                temperature = weather_elements.get("TEMP", "N/A")
                humidity = weather_elements.get("HUMD", "N/A")
                rain = weather_elements.get("24R", "N/A")
                return f"城市: {station_name}\n天氣: {weather}\n温度: {temperature}°C\n湿度: {humidity}%\n降雨量: {rain} mm"
            else:
                return "無法獲取天氣信息。"
        else:
            return "無法獲取天氣信息。"
    except Exception as e:
        return f"發生錯誤: {e}"

if __name__ == "__main__":
    app.run()
