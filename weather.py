import os
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import urllib.request
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import make_interp_spline
from matplotlib.ticker import FuncFormatter

# 設定中央氣象署 API Key
CWA_API_KEY = os.environ.get("CWA_API_KEY")
CITY_NAME = "臺北市" # 注意需使用「臺」

# --- 莫蘭迪配色定義 ---
COLOR_BG = '#EAE7E1'      
COLOR_PRIMARY = '#4A5568'   
COLOR_SECONDARY = '#8F8981' 
COLOR_CHART_LINE = '#7C8A76' 
COLOR_CHART_FILL = '#B4BCB1' 

def get_cwa_icon(weather_code):
    """
    氣象署本身未提供直接的 icon URL，通常建議準備一套本地對應圖示。
    此處簡化處理，若無圖示則回傳 None。
    """
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

    # 1. 抓取當前天氣 (使用自動觀測站資料)
    # 觀測站選取：臺北 (466920)
    obs_url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001?Authorization={CWA_API_KEY}&StationId=466920"
    obs_data = requests.get(obs_url).json()['records']['Station'][0]
    
    temp = round(float(obs_data['WeatherElement']['AirTemperature']))
    humidity = obs_data['WeatherElement']['RelativeHumidity']
    wind = obs_data['WeatherElement']['WindSpeed']
    pressure = obs_data['WeatherElement']['AirPressure']

    # 2. 抓取預報 (F-D0047-061 臺北市逐 3 小時預報)
    fc_url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-061?Authorization={CWA_API_KEY}&LocationName={CITY_NAME}"
    fc_res = requests.get(fc_url).json()['records']['Locations'][0]['Location'][0]
    elements = fc_res['WeatherElement']

    # 解析預報資料
    # T: 溫度, WX: 天氣現象, Pop12h: 降雨機率
    temp_list = next(e for e in elements if e['ElementName'] == 'T')['Time']
    desc_list = next(e for e in elements if e['ElementName'] == 'Wx')['Time']
    
    current_desc = desc_list[0]['ElementValue'][0]['Weather']
    
    local_time = datetime.now()
    weekdays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]
    date_display = f"{local_time.strftime('%Y年%m月%d日')} {weekdays[int(local_time.strftime('%w'))]}"

    # --- Header ---
    draw.text((100, 80), f"{temp}°C", fill=COLOR_PRIMARY, font=font_huge)
    draw.text((100, 350), f"濕度 {humidity}%  |  {current_desc}", fill=COLOR_PRIMARY, font=font_large)
    draw.text((1100, 80), "臺北市, 台灣", fill=COLOR_PRIMARY, font=font_large)
    draw.text((1100, 190), date_display, fill=COLOR_SECONDARY, font=font_medium)

    # --- 五天預報 (簡化版：從逐 3 小時資料提取每日高低溫) ---
    x_offset = 1000
    # 氣象署 F-D0047-091 為 7 天預報，此處直接使用當前資料做間隔採樣
    for i in range(0, 5):
        day_idx = i * 8 # 約略隔 24 小時
        if day_idx >= len(temp_list): break
        
        d_str = datetime.strptime(temp_list[day_idx]['StartTime'], '%Y-%m-%d %H:%M:%S').strftime('%m/%d')
        d_temp = temp_list[day_idx]['ElementValue'][0]['Temperature']
        
        draw.text((x_offset, 310), d_str, fill=COLOR_SECONDARY, font=font_medium)
        draw.text((x_offset, 530), f"{d_temp}°C", fill=COLOR_PRIMARY, font=font_small)
        x_offset += 180

    # --- 左下詳細指標 ---
    details = [
        f"風速: {wind} m/s",
        f"濕度: {humidity}%",
        f"氣壓: {pressure} hPa",
        f"降雨機率: {next(e for e in elements if e['ElementName'] == 'PoP12h')['Time'][0]['ElementValue'][0]['ProbabilityOfPrecipitation']}%"
    ]
    
    y_offset = 600
    for text in details:
        draw.text((100, y_offset), text, fill=COLOR_PRIMARY, font=font_medium)
        y_offset += 100

    # --- 右下趨勢圖 (未來 24 小時) ---
    chart_times = []
    chart_temps = []
    for item in temp_list[:8]:
        dt = datetime.strptime(item['DataTime'], '%Y-%m-%d %H:%M:%S')
        chart_times.append(dt.strftime('%I%p').lstrip('0'))
        chart_temps.append(float(item['ElementValue'][0]['Temperature']))

    plt.figure(figsize=(12, 7), dpi=100)
    x_indices = np.arange(len(chart_times))
    x_smooth = np.linspace(x_indices.min(), x_indices.max(), 300)
    spline = make_interp_spline(x_indices, chart_temps, k=3)
    y_smooth = spline(x_smooth)

    plt.plot(x_smooth, y_smooth, color=COLOR_CHART_LINE, linewidth=3, zorder=2)
    plt.scatter(x_indices, chart_temps, s=100, color='white', edgecolors=COLOR_CHART_LINE, linewidths=3, zorder=3)
    plt.fill_between(x_smooth, y_smooth, min(y_smooth)-2, color=COLOR_CHART_FILL, alpha=0.3, zorder=1)
    plt.grid(axis='y', linestyle='--', alpha=0.5, color='#CCCCCC')
    
    plt.xticks(ticks=x_indices, labels=chart_times, fontsize=24, color=COLOR_PRIMARY)
    plt.gca().yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{int(y)}°C"))
    plt.yticks(fontsize=24, color=COLOR_PRIMARY)
    
    ax = plt.gca()
    for spine in ['top', 'right']: ax.spines[spine].set_visible(False)
    
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    buf.seek(0)
    chart_img = Image.open(buf).convert("RGBA")
    img.paste(chart_img, (700, 650), chart_img)
    plt.close()

    # --- Footer ---
    update_str = local_time.strftime('%Y/%m/%d %H:%M:%S')
    draw.text((600, 1450), f"最後更新: {update_str} (CWA)", fill=COLOR_SECONDARY, font=font_small)

    img.save('weather.png')

if __name__ == "__main__":
    update_weather()
