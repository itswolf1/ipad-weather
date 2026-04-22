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
CITY_NAME = "臺北市" 
DISTRICT_NAME = "內湖區"

# 莫蘭迪配色定義
COLOR_BG = '#EAE7E1'      
COLOR_PRIMARY = '#4A5568'   
COLOR_SECONDARY = '#8F8981' 
COLOR_CHART_LINE = '#7C8A76' 
COLOR_CHART_FILL = '#B4BCB1' 

def get_cwa_icon(weather_code):
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

    # 1. 抓取當前天氣
    obs_url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001"
    obs_params = {
        "Authorization": CWA_API_KEY,
        "StationId": "466920", 
        "format": "JSON"
    }
    
    try:
        obs_data = requests.get(obs_url, params=obs_params).json()
        station_data = obs_data['records']['Station'][0]
        we = station_data.get('WeatherElement', {})
        
        temp = round(float(we.get('AirTemperature', 0)))
        humidity = we.get('RelativeHumidity', 0)
        wind = we.get('WindSpeed', 0)
        pressure = we.get('AirPressure', 0)
    except Exception as e:
        print(f"觀測站資料抓取失敗: {e}")
        return

    # 2. 抓取預報
    fc_url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-061"
    fc_params = {
        "Authorization": CWA_API_KEY,
        "format": "JSON"
    }
    
    try:
        fc_data = requests.get(fc_url, params=fc_params).json()
        locations_list = fc_data['records']['Locations'][0]['Location']
        
        fc_res = next((loc for loc in locations_list if loc.get('LocationName') == DISTRICT_NAME), locations_list[0])
        elements = fc_res.get('WeatherElement', [])
    except Exception as e:
        print(f"預報資料解析失敗: {e}")
        return

    # 防呆取值函式
    def find_weather_element(element_list, target_names):
        for e in element_list:
            name = e.get('ElementName', e.get('elementName'))
            if name in target_names:
                return e.get('Time', e.get('time', []))
        return []

    # 解析預報資料
    temp_list = find_weather_element(elements, ['T', '溫度', 'Temperature', 'MaxT'])
    desc_list = find_weather_element(elements, ['Wx', '天氣現象', 'WeatherCondition'])
    pop_list = find_weather_element(elements, ['PoP12h', '12小時降雨機率', 'PoP6h', 'PoP', '降雨機率'])
    min_t_list = find_weather_element(elements, ['MinT', '最低溫度'])
    max_t_list = find_weather_element(elements, ['MaxT', '最高溫度'])

    if not temp_list or not desc_list:
        print(f"找不到對應的 ElementName")
        return
    
    # 讀取天氣描述
    current_desc = "未知"
    val_list_desc = desc_list[0].get('ElementValue', desc_list[0].get('elementValue', []))
    if val_list_desc:
        current_desc = val_list_desc[0].get('Weather', val_list_desc[0].get('value', val_list_desc[0].get('WeatherDescription', '未知')))
    
    # 讀取降雨機率
    pop_value = "0"
    if pop_list:
        val_list_pop = pop_list[0].get('ElementValue', pop_list[0].get('elementValue', []))
        if val_list_pop:
            pop_value = val_list_pop[0].get('ProbabilityOfPrecipitation', val_list_pop[0].get('value', '0'))
            if not str(pop_value).strip():
                pop_value = "0"
    
    local_time = datetime.now()
    weekdays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]
    date_display = f"{local_time.strftime('%Y年%m月%d日')} {weekdays[int(local_time.strftime('%w'))]}"

    # Header 區塊
    draw.text((100, 80), f"{temp}°C", fill=COLOR_PRIMARY, font=font_huge)
    draw.text((100, 350), f"濕度 {humidity}%  |  {current_desc}", fill=COLOR_PRIMARY, font=font_large)
    draw.text((1100, 80), f"{CITY_NAME} {DISTRICT_NAME}", fill=COLOR_PRIMARY, font=font_large)
    draw.text((1100, 190), date_display, fill=COLOR_SECONDARY, font=font_medium)

    # 整理每日高低溫
    daily_extremes = {}
    
    for item in min_t_list:
        dt_str = item.get('DataTime', item.get('StartTime'))
        if not dt_str: continue
        d_str = datetime.fromisoformat(dt_str).strftime('%m/%d')
        val_list = item.get('ElementValue', item.get('elementValue', []))
        val = val_list[0].get('Temperature', val_list[0].get('value')) if val_list else None
        if val is not None:
            if d_str not in daily_extremes: daily_extremes[d_str] = {'min': [], 'max': []}
            daily_extremes[d_str]['min'].append(int(val))

    for item in max_t_list:
        dt_str = item.get('DataTime', item.get('StartTime'))
        if not dt_str: continue
        d_str = datetime.fromisoformat(dt_str).strftime('%m/%d')
        val_list = item.get('ElementValue', item.get('elementValue', []))
        val = val_list[0].get('Temperature', val_list[0].get('value')) if val_list else None
        if val is not None:
            if d_str not in daily_extremes: daily_extremes[d_str] = {'min': [], 'max': []}
            daily_extremes[d_str]['max'].append(int(val))

    # 五天預報區塊
    x_offset = 1000
    count = 0
    for d_str, extremes in daily_extremes.items():
        if count >= 5: break
        if not extremes['min'] or not extremes['max']: continue
        
        low = min(extremes['min'])
        high = max(extremes['max'])
        
        draw.text((x_offset, 310), d_str, fill=COLOR_SECONDARY, font=font_medium)
        draw.text((x_offset, 530), f"{low}°|{high}°", fill=COLOR_PRIMARY, font=font_small)
        x_offset += 180
        count += 1

    # 左下詳細指標區塊
    details = [
        f"風速: {wind} m/s",
        f"濕度: {humidity}%",
        f"氣壓: {pressure} hPa",
        f"降雨機率: {pop_value}%"
    ]
    
    y_offset = 600
    for text in details:
        draw.text((100, y_offset), text, fill=COLOR_PRIMARY, font=font_medium)
        y_offset += 100

    # 右下趨勢圖區塊
    chart_times = []
    chart_temps = []
    for item in temp_list[:8]:
        dt_str = item.get('DataTime', item.get('StartTime'))
        if not dt_str: continue
        dt = datetime.fromisoformat(dt_str)
        
        val_list_temp = item.get('ElementValue', item.get('elementValue', []))
        temp_val = val_list_temp[0].get('Temperature', val_list_temp[0].get('value', '0')) if val_list_temp else '0'
        
        try:
            chart_temps.append(float(temp_val))
            chart_times.append(dt.strftime('%I%p').lstrip('0'))
        except ValueError:
            continue

    if chart_temps:
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

    # Footer 區塊
    update_str = local_time.strftime('%Y/%m/%d %H:%M:%S')
    draw.text((600, 1450), f"最後更新: {update_str} (CWA)", fill=COLOR_SECONDARY, font=font_small)

    img.save('weather.png')
    print("圖片已成功存檔並更新！")

if __name__ == "__main__":
    update_weather()
