import os
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import urllib.request
import io
import matplotlib
matplotlib.use('Agg') # 確保在無介面伺服器正常繪圖
import matplotlib.pyplot as plt

API_KEY = os.environ.get("OPENWEATHER_API_KEY")
CITY = "Taipei, TW"
BASE_URL = "http://api.openweathermap.org/data/2.5"

def get_icon(icon_code, size=2):
    url = f"http://openweathermap.org/img/wn/{icon_code}@{size}x.png"
    try:
        response = requests.get(url)
        return Image.open(io.BytesIO(response.content)).convert("RGBA")
    except:
        return None

def update_weather():
    # 準備字體
    font_path = "font.otf"
    if not os.path.exists(font_path):
        font_url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
        urllib.request.urlretrieve(font_url, font_path)

    font_huge = ImageFont.truetype(font_path, 200)
    font_large = ImageFont.truetype(font_path, 80)
    font_medium = ImageFont.truetype(font_path, 50)
    font_small = ImageFont.truetype(font_path, 40)

    # 建立畫布
    img = Image.new('RGB', (2048, 1536), color='white')
    draw = ImageDraw.Draw(img)
    
    # 取得當前天氣
    current_url = f"{BASE_URL}/weather?q={CITY}&appid={API_KEY}&units=metric&lang=zh_tw"
    cur = requests.get(current_url).json()
    lat, lon = cur['coord']['lat'], cur['coord']['lon']
    
    # 取得空氣品質
    aqi_url = f"{BASE_URL}/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
    aqi_data = requests.get(aqi_url).json()
    aqi = aqi_data['list'][0]['main']['aqi']
    
    # 取得預報資料 (每3小時)
    forecast_url = f"{BASE_URL}/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=zh_tw"
    fc = requests.get(forecast_url).json()

    # --- 左上：當前天氣 ---
    temp = round(cur['main']['temp'])
    feels_like = round(cur['main']['feels_like'])
    desc = cur['weather'][0]['description']
    icon_code = cur['weather'][0]['icon']
    
    draw.text((100, 100), f"{temp}°C", fill='black', font=font_huge)
    draw.text((100, 350), f"體感 {feels_like}°C  |  {desc}", fill='black', font=font_large)
    
    icon_img = get_icon(icon_code, size=4)
    if icon_img:
        icon_img = icon_img.resize((300, 300))
        img.paste(icon_img, (550, 80), icon_img)

    # --- 左下：詳細指標 ---
    humidity = cur['main']['humidity']
    wind = cur['wind']['speed']
    pressure = cur['main']['pressure']
    visibility = cur.get('visibility', 0) / 1000
    
    tz_offset = timedelta(seconds=cur['timezone'])
    sunrise = (datetime.utcfromtimestamp(cur['sys']['sunrise']) + tz_offset).strftime('%H:%M')
    sunset = (datetime.utcfromtimestamp(cur['sys']['sunset']) + tz_offset).strftime('%H:%M')

    details = [
        f"日出: {sunrise}", f"日落: {sunset}",
        f"風速: {wind} m/s", f"濕度: {humidity}%",
        f"氣壓: {pressure} hPa", f"能見度: {visibility} km",
        f"空氣品質指標 (AQI): {aqi}"
    ]
    
    y_offset = 600
    for i, text in enumerate(details):
        x = 100 if i % 2 == 0 else 600
        draw.text((x, y_offset), text, fill='black', font=font_medium)
        if i % 2 == 1:
            y_offset += 100
    if len(details) % 2 != 0:
        y_offset += 100

    # --- 右上：5天預報 ---
    daily_forecasts = {}
    for item in fc['list']:
        # 轉換為當地時間
        dt = datetime.utcfromtimestamp(item['dt']) + tz_offset
        date_str = dt.strftime('%m/%d')
        if date_str not in daily_forecasts:
            daily_forecasts[date_str] = {'temps': [], 'icon': item['weather'][0]['icon']}
        daily_forecasts[date_str]['temps'].append(item['main']['temp'])
    
    draw.text((1100, 100), "未來五天預報", fill='black', font=font_large)
    x_offset = 1100
    count = 0
    for date_str, data in daily_forecasts.items():
        if count >= 5: break
        high = round(max(data['temps']))
        low = round(min(data['temps']))
        
        draw.text((x_offset, 250), date_str, fill='black', font=font_medium)
        f_icon = get_icon(data['icon'], size=2)
        if f_icon:
            img.paste(f_icon, (x_offset - 20, 320), f_icon)
        draw.text((x_offset, 450), f"{high}°|{low}°", fill='black', font=font_small)
        
        x_offset += 180
        count += 1

    # --- 右下：24小時溫度趨勢圖 ---
    times = []
    temps = []
    for item in fc['list'][:8]: # 取未來 24 小時 (8 個 3 小時區間)
        dt = datetime.utcfromtimestamp(item['dt']) + tz_offset
        times.append(dt.strftime('%H:%M'))
        temps.append(item['main']['temp'])

    plt.figure(figsize=(9, 5), dpi=100)
    plt.plot(times, temps, marker='o', color='black', linewidth=3, markersize=10)
    plt.fill_between(times, temps, min(temps)-2, color='gray', alpha=0.2)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)
    plt.tight_layout()
    
    # 將圖表存入記憶體並貼到主圖
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    buf.seek(0)
    chart_img = Image.open(buf).convert("RGBA")
    img.paste(chart_img, (1100, 700), chart_img)
    plt.close()

    # 更新時間
    local_time = datetime.utcnow() + timedelta(hours=8)
    draw.text((1100, 1400), f"最後更新: {local_time.strftime('%Y-%m-%d %H:%M:%S')}", fill='gray', font=font_small)

    img.save('weather.png')

if __name__ == "__main__":
    update_weather()
