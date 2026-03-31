import os
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import urllib.request
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

API_KEY = os.environ.get("OPENWEATHER_API_KEY")
CITY = "Taipei, TW"
BASE_URL = "http://api.openweathermap.org/data/2.5"

COLOR_BG = '#EAE7E1'
COLOR_PRIMARY = '#4A5568'
COLOR_SECONDARY = '#8F8981'
COLOR_CHART_LINE = '#7C8A76'
COLOR_CHART_FILL = '#B4BCB1'

def get_icon(icon_code, size=2):
    url = f"http://openweathermap.org/img/wn/{icon_code}@{size}x.png"
    try:
        response = requests.get(url)
        img = Image.open(io.BytesIO(response.content)).convert("RGBA")
        return img
    except:
        return None

def update_weather():
    font_path = "font.otf"
    if not os.path.exists(font_path):
        font_url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
        urllib.request.urlretrieve(font_url, font_path)

    font_huge = ImageFont.truetype(font_path, 200)
    font_large = ImageFont.truetype(font_path, 80)
    font_medium = ImageFont.truetype(font_path, 50)
    font_small = ImageFont.truetype(font_path, 40)

    img = Image.new('RGB', (2048, 1536), color=COLOR_BG)
    draw = ImageDraw.Draw(img)
    
    current_url = f"{BASE_URL}/weather?q={CITY}&appid={API_KEY}&units=metric&lang=zh_tw"
    cur = requests.get(current_url).json()
    lat, lon = cur['coord']['lat'], cur['coord']['lon']
    
    aqi_url = f"{BASE_URL}/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
    aqi_data = requests.get(aqi_url).json()
    aqi = aqi_data['list'][0]['main']['aqi']
    
    forecast_url = f"{BASE_URL}/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=zh_tw"
    fc = requests.get(forecast_url).json()

    # 左上：當前天氣
    temp = round(cur['main']['temp'])
    feels_like = round(cur['main']['feels_like'])
    desc = cur['weather'][0]['description']
    icon_code = cur['weather'][0]['icon']
    
    draw.text((100, 100), f"{temp}°C", fill=COLOR_PRIMARY, font=font_huge)
    draw.text((100, 350), f"體感 {feels_like}°C  |  {desc}", fill=COLOR_PRIMARY, font=font_large)
    
    icon_img = get_icon(icon_code, size=4)
    if icon_img:
        icon_img = icon_img.resize((300, 300))
        img.paste(icon_img, (550, 80), icon_img)

    # 左下：詳細指標
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
        draw.text((x, y_offset), text, fill=COLOR_PRIMARY, font=font_medium)
        if i % 2 == 1:
            y_offset += 100
    if len(details) % 2 != 0:
        y_offset += 100

    # 右上：所在地與日期
    local_time = datetime.utcnow() + timedelta(hours=8)
    weekdays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]
    weekday_index = int(local_time.strftime("%w"))
    date_display = f"{local_time.strftime('%Y年%m月%d日')} {weekdays[weekday_index]}"
    
    draw.text((1100, 80), "台北市, 台灣", fill=COLOR_PRIMARY, font=font_large)
    draw.text((1100, 180), date_display, fill=COLOR_SECONDARY, font=font_medium)

    # 右上中：5天預報
    daily_forecasts = {}
    for item in fc['list']:
        dt = datetime.utcfromtimestamp(item['dt']) + tz_offset
        date_str = dt.strftime('%m/%d')
        if date_str not in daily_forecasts:
            daily_forecasts[date_str] = {'temps': [], 'icon': item['weather'][0]['icon']}
        daily_forecasts[date_str]['temps'].append(item['main']['temp'])
    
    x_offset = 1100
    count = 0
    for date_str, data in daily_forecasts.items():
        if count >= 5: break
        high = round(max(data['temps']))
        low = round(min(data['temps']))
        
        draw.text((x_offset, 280), date_str, fill=COLOR_SECONDARY, font=font_medium)
        f_icon = get_icon(data['icon'], size=2)
        if f_icon:
            f_icon = f_icon.resize((150, 150))
            img.paste(f_icon, (x_offset - 20, 350), f_icon)
        
        draw.text((x_offset, 520), f"{high}°|{low}°", fill=COLOR_PRIMARY, font=font_small)
        
        x_offset += 180
        count += 1

    # 右下：24小時溫度趨勢圖
    times = []
    temps = []
    for item in fc['list'][:8]:
        dt = datetime.utcfromtimestamp(item['dt']) + tz_offset
        times.append(dt.strftime('%H:%M'))
        temps.append(item['main']['temp'])

    plt.figure(figsize=(9, 5), dpi=100)
    plt.plot(times, temps, marker='o', color=COLOR_CHART_LINE, linewidth=3, markersize=10, 
             markeredgecolor=COLOR_CHART_LINE, markerfacecolor='white')
    plt.fill_between(times, temps, min(temps)-2, color=COLOR_CHART_FILL, alpha=0.3)
    plt.grid(axis='y', linestyle=':', alpha=0.5, color='#CCCCCC')
    
    plt.xticks(fontsize=14, color=COLOR_PRIMARY)
    plt.yticks(fontsize=14, color=COLOR_PRIMARY)
    
    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(COLOR_PRIMARY)
    ax.spines['bottom'].set_color(COLOR_PRIMARY)
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    buf.seek(0)
    chart_img = Image.open(buf).convert("RGBA")
    img.paste(chart_img, (1100, 700), chart_img)
    plt.close()

    local_time = datetime.utcnow() + timedelta(hours=8)
    draw.text((1100, 1400), f"最後更新: {local_time.strftime('%Y/%m/%d %H:%M:%S')}", fill=COLOR_SECONDARY, font=font_small)

    img.save('weather.png')

if __name__ == "__main__":
    update_weather()
