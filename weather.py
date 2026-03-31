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

# --- 莫蘭迪配色定義 (Morandi Palette) ---
COLOR_BG = '#EAE7E1'      # 背景：暖灰白
COLOR_PRIMARY = '#4A5568'   # 主文字/主要內容：深莫蘭迪藍灰
COLOR_SECONDARY = '#8F8981' # 次要文字：莫蘭迪暖灰
COLOR_CHART_LINE = '#7C8A76' # 圖表線條：莫蘭迪鼠尾草綠
COLOR_CHART_FILL = '#B4BCB1' # 圖表填充：淺鼠尾草綠

def get_icon(icon_code, size=2):
    # 此為 OpenWeatherMap 官方圖示
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

    # 建立畫布 (使用新的背景色)
    img = Image.new('RGB', (2048, 1536), color=COLOR_BG)
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

    tz_offset = timedelta(seconds=cur['timezone'])
    local_time = datetime.utcnow() + timedelta(hours=8)
    weekdays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]
    weekday_index = int(local_time.strftime("%w"))
    date_display = f"{local_time.strftime('%Y年%m月%d日')} {weekdays[weekday_index]}"

    # --- 最上方頁眉 (Header)：當前天氣 (左上) ---
    temp = round(cur['main']['temp'])
    feels_like = round(cur['main']['feels_like'])
    desc = cur['weather'][0]['description']
    icon_code = cur['weather'][0]['icon']
    
    # 當前溫度文字 (非常大)
    draw.text((100, 80), f"{temp}°C", fill=COLOR_PRIMARY, font=font_huge)
    
    # 天氣描述/體感
    draw.text((100, 260), f"體感 {feels_like}°C  |  {desc}", fill=COLOR_PRIMARY, font=font_large)
    
    # 天氣圖示
    icon_img = get_icon(icon_code, size=4)
    if icon_img:
        icon_img = icon_img.resize((300, 300))
        img.paste(icon_img, (500, 80), icon_img)

    # --- 最上方頁眉 (Header)：所在地與日期 (右上) ---
    draw.text((1100, 80), "台北市, 台灣", fill=COLOR_PRIMARY, font=font_large)
    draw.text((1100, 160), date_display, fill=COLOR_SECONDARY, font=font_medium)

    # --- 五天預報分區 (中右下) ---
    # 移除了舊版中的預報標題

    daily_forecasts = {}
    for item in fc['list']:
        dt = datetime.utcfromtimestamp(item['dt']) + tz_offset
        date_str = dt.strftime('%m/%d')
        if date_str not in daily_forecasts:
            daily_forecasts[date_str] = {'temps': [], 'icon': item['weather'][0]['icon']}
        daily_forecasts[date_str]['temps'].append(item['main']['temp'])
    
    # 將預報部分移到當前天氣頁眉下方
    x_offset = 1000 # 稍微左移
    count = 0
    for date_str, data in daily_forecasts.items():
        if count >= 5: break
        high = round(max(data['temps']))
        low = round(min(data['temps']))
        
        # 日期使用次要文字顏色 COLOR_SECONDARY
        draw.text((x_offset, 280), date_str, fill=COLOR_SECONDARY, font=font_medium)
        f_icon = get_icon(data['icon'], size=2)
        if f_icon:
            # 將圖示縮小一些
            f_icon = f_icon.resize((150, 150))
            img.paste(f_icon, (x_offset - 20, 350), f_icon)
        
        # 溫度高低使用主文字顏色 COLOR_PRIMARY
        draw.text((x_offset, 520), f"{high}°|{low}°", fill=COLOR_PRIMARY, font=font_small)
        
        x_offset += 180
        count += 1

    # --- 左下詳細指標分區 (左下) ---
    # 將所有指標移到左下角

    humidity = cur['main']['humidity']
    wind = cur['wind']['speed']
    pressure = cur['main']['pressure']
    visibility = cur.get('visibility', 0) / 1000
    
    sunrise = (datetime.utcfromtimestamp(cur['sys']['sunrise']) + tz_offset).strftime('%H:%M')
    sunset = (datetime.utcfromtimestamp(cur['sys']['sunset']) + tz_offset).strftime('%H:%M')

    details = [
        f"日出: {sunrise}", f"日落: {sunset}",
        f"風速: {wind} m/s", f"濕度: {humidity}%",
        f"氣壓: {pressure} hPa", f"能見度: {visibility} km",
        f"空氣品質指標 (AQI): {aqi}"
    ]
    
    y_offset = 600 # 稍微下移
    for i, text in enumerate(details):
        x = 100 if i % 2 == 0 else 600
        # 文字使用 COLOR_PRIMARY
        draw.text((x, y_offset), text, fill=COLOR_PRIMARY, font=font_medium)
        if i % 2 == 1:
            y_offset += 100
    if len(details) % 2 != 0:
        y_offset += 100

    # --- 右下趨勢圖分區 (右下) ---
    # 移到最右下角

    times = []
    temps = []
    for item in fc['list'][:8]: # 取未來 24 小時
        dt = datetime.utcfromtimestamp(item['dt']) + tz_offset
        times.append(dt.strftime('%H:%M'))
        temps.append(item['main']['temp'])

    # 設定 Matplotlib 配色
    # 稍微調整圖表的大小以適應新的排版
    plt.figure(figsize=(9, 5), dpi=100)
    
    # 使用莫蘭迪綠色線條 COLOR_CHART_LINE
    plt.plot(times, temps, marker='o', color=COLOR_CHART_LINE, linewidth=3, markersize=10, 
             markeredgecolor=COLOR_CHART_LINE, markerfacecolor='white')
    
    # 使用淺鼠尾草綠填充 COLOR_CHART_FILL，並調整透明度
    plt.fill_between(times, temps, min(temps)-2, color=COLOR_CHART_FILL, alpha=0.3)
    
    # 網格使用淡灰色，alpha調更低
    plt.grid(axis='y', linestyle='--', alpha=0.5, color='#CCCCCC')
    
    # 刻度文字使用主文字顏色 COLOR_PRIMARY
    plt.xticks(fontsize=14, color=COLOR_PRIMARY)
    plt.yticks(fontsize=14, color=COLOR_PRIMARY)
    
    # 移除邊框
    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(COLOR_PRIMARY) # 左邊框保留顏色
    ax.spines['bottom'].set_color(COLOR_PRIMARY) # 下邊框保留顏色
    
    plt.tight_layout()
    
    # 將圖表存入記憶體並貼到主圖
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    buf.seek(0)
    chart_img = Image.open(buf).convert("RGBA")
    # 將貼上位置移到最右下角
    img.paste(chart_img, (1100, 800), chart_img)
    plt.close()

    # --- 最後更新時間 (底部正中央) ---
    # 將時間移到最底部的中央
    # 計算時間文字的大小以準確對齊
    time_str = local_time.strftime('%Y/%m/%d %H:%M:%S')
    draw.text((600, 1450), f"最後更新: {time_str}", fill=COLOR_SECONDARY, font=font_small)

    img.save('weather.png')

if __name__ == "__main__":
    update_weather()
