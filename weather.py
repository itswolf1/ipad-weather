import os
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import urllib.request

API_KEY = os.environ.get("OPENWEATHER_API_KEY")
CITY = "Taipei, TW"
URL = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric&lang=zh_tw"

def update_weather():
    # 下載免費開源的 Noto 繁體中文字體
    font_path = "font.otf"
    if not os.path.exists(font_path):
        font_url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
        urllib.request.urlretrieve(font_url, font_path)

    try:
        res = requests.get(URL).json()
        temp = round(res['main']['temp'], 1)
        desc = res['weather'][0]['description']
        text = f"{temp} °C\n{desc}"
    except Exception:
        text = "Weather Data Error"

    # 建立 2048x1536 白底圖片
    img = Image.new('RGB', (2048, 1536), color='white')
    draw = ImageDraw.Draw(img)
    
    # 修正時區 (UTC + 8 小時)
    local_time = datetime.utcnow() + timedelta(hours=8)
    time_str = local_time.strftime('%Y-%m-%d %H:%M:%S')
    
    # 設定字體大小 (主標題 250，副標題 80)
    font_large = ImageFont.truetype(font_path, 250)
    font_small = ImageFont.truetype(font_path, 80)
    
    # 將文字繪製到圖片上
    draw.text((150, 400), text, fill='black', font=font_large)
    draw.text((150, 1300), f"最後更新: {time_str}", fill='gray', font=font_small)
    
    img.save('weather.png')

if __name__ == "__main__":
    update_weather()
