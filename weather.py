import os
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import urllib.request
import io
import matplotlib
matplotlib.use('Agg') # 確保在無介面伺服器正常繪圖
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import make_interp_spline
from matplotlib.ticker import FuncFormatter

API_KEY = os.environ.get("OPENWEATHER_API_KEY")
CITY = "Taipei, TW"
BASE_URL = "http://api.openweathermap.org/data/2.5"

# --- 莫蘭迪配色定義 (Morandi Palette) ---
COLOR_BG = '#EAE7E1'      
COLOR_PRIMARY = '#4A5568'   
COLOR_SECONDARY = '#8F8981' 
COLOR_CHART_LINE = '#7C8A76' 
COLOR_CHART_FILL = '#B4BCB1' 

def get_icon(icon_code, size=2):
    url = f"http://openweathermap.org/img/wn/{icon_code}@{size}x.png"
    try:
        response = requests.get(url)
        return Image.open(io.BytesIO(response.content)).convert("RGBA")
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

    # 📌 [微調尺寸] 建立畫布：(寬 2048, 高 1536)
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

    tz_offset = timedelta(seconds=cur['timezone'])
    local_time = datetime.utcnow() + timedelta(hours=8)
    weekdays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]
    weekday_index = int(local_time.strftime("%w"))
    date_display = f"{local_time.strftime('%Y年%m月%d日')} {weekdays[weekday_index]}"

    # ==========================================
    # --- 最上方頁眉 (Header)：當前天氣 (左上) ---
    # ==========================================
    temp = round(cur['main']['temp'])
    feels_like = round(cur['main']['feels_like'])
    desc = cur['weather'][0]['description']
    icon_code = cur['weather'][0]['icon']
    
    # 📌 [微調位置] 當前溫度文字 (X=100, Y=80)
    draw.text((100, 80), f"{temp}°C", fill=COLOR_PRIMARY, font=font_huge)
    
    # 📌 [微調位置] 天氣描述/體感 (X=100, Y=350)
    draw.text((100, 350), f"體感 {feels_like}°C  |  {desc}", fill=COLOR_PRIMARY, font=font_large)
    
    # 天氣圖示
    icon_img = get_icon(icon_code, size=4)
    if icon_img:
        # 📌 [微調尺寸] 放大當前天氣圖示 (寬 300, 高 300)
        icon_img = icon_img.resize((300, 300))
        # 📌 [微調位置] 貼上天氣圖示 (X=500, Y=80)
        img.paste(icon_img, (500, 80), icon_img)

    # ==========================================
    # --- 最上方頁眉 (Header)：所在地與日期 (右上) ---
    # ==========================================
    # 📌 [微調位置] 城市名稱 (X=1100, Y=80)
    draw.text((1100, 80), "台北市, 台灣", fill=COLOR_PRIMARY, font=font_large)
    
    # 📌 [微調位置] 當前日期 (X=1100, Y=190)
    draw.text((1100, 190), date_display, fill=COLOR_SECONDARY, font=font_medium)

    # ==========================================
    # --- 五天預報分區 (中右下) ---
    # ==========================================
    daily_forecasts = {}
    for item in fc['list']:
        dt = datetime.utcfromtimestamp(item['dt']) + tz_offset
        date_str = dt.strftime('%m/%d')
        if date_str not in daily_forecasts:
            daily_forecasts[date_str] = {'temps': [], 'icon': item['weather'][0]['icon']}
        daily_forecasts[date_str]['temps'].append(item['main']['temp'])
    
    # 📌 [微調位置] 預報區塊起始 X 座標 (預設為 1000)
    x_offset = 1000 
    count = 0
    for date_str, data in daily_forecasts.items():
        if count >= 5: break
        high = round(max(data['temps']))
        low = round(min(data['temps']))
        
        # 📌 [微調位置] 預報日期 Y 座標 (Y=310)
        draw.text((x_offset, 310), date_str, fill=COLOR_SECONDARY, font=font_medium)
        f_icon = get_icon(data['icon'], size=2)
        if f_icon:
            # 📌 [微調尺寸] 預報小圖示大小 (寬 150, 高 150)
            f_icon = f_icon.resize((150, 150))
            # 📌 [微調位置] 預報小圖示 Y 座標 (X往左偏移20, Y=380)
            img.paste(f_icon, (x_offset - 20, 380), f_icon)
        
        # 📌 [微調位置] 預報高低溫 Y 座標 (Y=530)
        draw.text((x_offset, 530), f"{low}°|{high}°", fill=COLOR_PRIMARY, font=font_small)
        
        # 📌 [微調位置] 每個預報欄位之間的間距 (增加 180)
        x_offset += 180
        count += 1

    # ==========================================
    # --- 左下詳細指標分區 (左下) ---
    # ==========================================
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
    
   # 📌 [微調位置] 詳細指標區塊起始 Y 座標 (預設為 600)
    y_offset = 600 
    
    for text in details:
        # 📌 [微調位置] 變成單欄，固定 X=100
        x = 100 
        
        draw.text((x, y_offset), text, fill=COLOR_PRIMARY, font=font_medium)
        
        # 📌 [微調位置] 每印完一行，固定往下移 (行距：可依喜好調整，目前設為 100)
        y_offset += 100

    # ==========================================
    # --- 右下趨勢圖分區 (右下) ---
    # ==========================================
    times = []
    temps = []
    for item in fc['list'][:8]: # 取未來 24 小時
        dt = datetime.utcfromtimestamp(item['dt']) + tz_offset
        # 將時間轉為 12 小時制 AM/PM，並去掉開頭的 0 (例如: 05PM -> 5PM)
        time_str = dt.strftime('%I%p').lstrip('0')
        times.append(time_str)
        temps.append(item['main']['temp'])

    # 📌 [微調尺寸] 圖表本身的長寬比例：寬12, 高7 (數字越大圖越大)
    plt.figure(figsize=(12, 7), dpi=100)
    
    # --- 開始平滑化曲線的計算 ---
    # 因為 Matplotlib 預設是直線連接字串 X 軸，我們需先用數字索引 (0,1,2...) 來計算平滑曲線
    x_indices = np.arange(len(times))
    # 產生 300 個細密點來畫平滑曲線
    x_smooth = np.linspace(x_indices.min(), x_indices.max(), 300) 
    # 使用三次樣條插值 (Cubic Spline) 產生平滑的 Y 值
    spline = make_interp_spline(x_indices, temps, k=3) 
    y_smooth = spline(x_smooth)

    # 畫平滑曲線的主線條 (zorder 決定圖層順序，數字越大越上層)
    plt.plot(x_smooth, y_smooth, color=COLOR_CHART_LINE, linewidth=3, zorder=2)
    
    # 畫出每個時段原本的「資料點」(實心白底、圓框線)
    plt.scatter(x_indices, temps, s=100, color='white', edgecolors=COLOR_CHART_LINE, linewidths=3, zorder=3)
    
    # 填充平滑曲線下方的面積
    plt.fill_between(x_smooth, y_smooth, min(y_smooth)-2, color=COLOR_CHART_FILL, alpha=0.3, zorder=1)
    
    # 網格線設定
    plt.grid(axis='y', linestyle='--', alpha=0.5, color='#CCCCCC')

    # 計算並強制設定 5 個 Y 軸刻度
    min_temp = min(temps)
    max_temp = max(temps)
    if min_temp == max_temp:
        min_temp -= 2
        max_temp += 2
    step = (max_temp - min_temp) / 4
    y_ticks = [round(min_temp + step * i, 1) for i in range(5)]
    
    # 📌 [微調圖表字體大小] 調整 X 軸時間 (5PM, 8PM 等格式) 字體大小
    plt.xticks(ticks=x_indices, labels=times, fontsize=24, color=COLOR_PRIMARY)
    
    # 使用 FuncFormatter 為 Y 軸動態加上 °C 符號 (18°C, 20°C 等格式)
    plt.gca().yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{int(y)}°C"))
    # 📌 [微調圖表字體大小] 調整 Y 軸溫度字體大小
    plt.yticks(fontsize=24, color=COLOR_PRIMARY)
    
    # 移除圖表上下左右多餘的邊框
    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(COLOR_PRIMARY) 
    ax.spines['bottom'].set_color(COLOR_PRIMARY) 
    
    plt.tight_layout()
    
    # 存入記憶體並貼到畫布
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    buf.seek(0)
    chart_img = Image.open(buf).convert("RGBA")
    
    # 📌 [微調位置] 將整個圖表貼上的座標 (X=700, Y=650)
    img.paste(chart_img, (700, 650), chart_img)
    plt.close()

    # ==========================================
    # --- 最後更新時間 (底部正中央) ---
    # ==========================================
    time_str = local_time.strftime('%Y/%m/%d %H:%M:%S')
    
    # 📌 [微調位置] 更新時間顯示座標 (X=600, Y=1450)
    draw.text((600, 1450), f"最後更新: {time_str}", fill=COLOR_SECONDARY, font=font_small)

    img.save('weather.png')

if __name__ == "__main__":
    update_weather()
