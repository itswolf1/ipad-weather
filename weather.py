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

# 設定 API Keys
CWA_API_KEY = os.environ.get("CWA_API_KEY")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY") 

CITY_NAME = "臺北市" 
DISTRICT_NAME = "內湖區"
OW_CITY = "Taipei, TW" 

# 莫蘭迪配色定義
COLOR_BG = '#EAE7E1'      
COLOR_PRIMARY = '#4A5568'   
COLOR_SECONDARY = '#8F8981' 
COLOR_CHART_LINE = '#7C8A76' 
COLOR_CHART_FILL = '#B4BCB1' 

def get_cwa_icon(weather_code):
    return None

def get_icon(icon_code, size=2):
    """從 OpenWeather 下載天氣圖示"""
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

    img = Image.new('RGB', (2048, 1536), color=COLOR_BG)
    draw = ImageDraw.Draw(img)

    # ==========================================
    # 1. 抓取當前天氣與預報 (CWA 氣象署)
    # ==========================================
    obs_url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001"
    obs_params = {"Authorization": CWA_API_KEY, "StationId": "466920", "format": "JSON"}
    
    fc_url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-061"
    fc_params = {"Authorization": CWA_API_KEY, "format": "JSON"}
    
    try:
        obs_data = requests.get(obs_url, params=obs_params).json()
        we = obs_data['records']['Station'][0].get('WeatherElement', {})
        temp = round(float(we.get('AirTemperature', 0)))
        humidity = we.get('RelativeHumidity', 0)
        wind = we.get('WindSpeed', 0)
        pressure = we.get('AirPressure', 0)

        fc_data = requests.get(fc_url, params=fc_params).json()
        locations_list = fc_data['records']['Locations'][0]['Location']
        fc_res = next((loc for loc in locations_list if loc.get('LocationName') == DISTRICT_NAME), locations_list[0])
        elements = fc_res.get('WeatherElement', [])
    except Exception as e:
        print(f"CWA 資料抓取失敗: {e}")
        return

    # ==========================================
    # 2. 抓取圖示與日出日落 (OpenWeather)
    # ==========================================
    ow_icons = {}
    cur_icon_code = None
    sunrise, sunset = "--:--", "--:--"
    try:
        # 當前天氣 (取日出落與當前圖示)
        ow_cur_url = f"http://api.openweathermap.org/data/2.5/weather?q={OW_CITY}&appid={OPENWEATHER_API_KEY}"
        ow_cur = requests.get(ow_cur_url).json()
        tz_offset = timedelta(seconds=ow_cur['timezone'])
        sunrise = (datetime.utcfromtimestamp(ow_cur['sys']['sunrise']) + tz_offset).strftime('%H:%M')
        sunset = (datetime.utcfromtimestamp(ow_cur['sys']['sunset']) + tz_offset).strftime('%H:%M')
        cur_icon_code = ow_cur['weather'][0]['icon']

        # 預報天氣 (取未來五天圖示)
        ow_fc_url = f"http://api.openweathermap.org/data/2.5/forecast?q={OW_CITY}&appid={OPENWEATHER_API_KEY}"
        ow_fc = requests.get(ow_fc_url).json()
        
        for item in ow_fc['list']:
            dt = datetime.utcfromtimestamp(item['dt']) + tz_offset
            d_str = dt.strftime('%m/%d')
            icon = item['weather'][0]['icon']
            # 優先保留白天 ('d') 的圖示
            if d_str not in ow_icons:
                ow_icons[d_str] = icon
            elif 'd' in icon and 'n' in ow_icons[d_str]: 
                ow_icons[d_str] = icon
    except Exception as e:
        print(f"OpenWeather 資料抓取失敗: {e}")

    # ==========================================
    # 3. 解析 CWA 預報資料
    # ==========================================
    def find_weather_element(element_list, target_names):
        for e in element_list:
            if e.get('ElementName', e.get('elementName')) in target_names:
                return e.get('Time', e.get('time', []))
        return []

    temp_list = find_weather_element(elements, ['T', '溫度', 'Temperature', 'MaxT'])
    desc_list = find_weather_element(elements, ['Wx', '天氣現象', 'WeatherCondition'])
    pop_list = find_weather_element(elements, ['PoP12h', '12小時降雨機率', 'PoP6h', 'PoP', '降雨機率'])

    if not temp_list or not desc_list: return
    
    current_desc = "未知"
    val_list_desc = desc_list[0].get('ElementValue', desc_list[0].get('elementValue', []))
    if val_list_desc:
        current_desc = val_list_desc[0].get('Weather', val_list_desc[0].get('value', '未知'))
    
    pop_value = "0"
    if pop_list:
        val_list_pop = pop_list[0].get('ElementValue', pop_list[0].get('elementValue', []))
        if val_list_pop:
            pop_value = val_list_pop[0].get('ProbabilityOfPrecipitation', val_list_pop[0].get('value', '0'))
            if not str(pop_value).strip(): pop_value = "0"
    
    local_time = datetime.now()
    weekdays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]
    date_display = f"{local_time.strftime('%Y年%m月%d日')} {weekdays[int(local_time.strftime('%w'))]}"

    daily_data = {}
    for item in temp_list:
        dt_str = item.get('DataTime', item.get('StartTime'))
        if not dt_str: continue
        d_str = datetime.fromisoformat(dt_str).strftime('%m/%d')
        val_list = item.get('ElementValue', item.get('elementValue', []))
        val = val_list[0].get('Temperature', val_list[0].get('value')) if val_list else None
        if val is not None:
            if d_str not in daily_data: daily_data[d_str] = []
            daily_data[d_str].append(int(val))

    # ==========================================
    # 4. 繪製區塊
    # ==========================================
    # --- Header (當前天氣與圖示) ---
    draw.text((100, 80), f"{temp}°C", fill=COLOR_PRIMARY, font=font_huge)
    draw.text((100, 350), f"濕度 {humidity}%  |  {current_desc}", fill=COLOR_PRIMARY, font=font_large)
    draw.text((1100, 80), f"{CITY_NAME} {DISTRICT_NAME}", fill=COLOR_PRIMARY, font=font_large)
    draw.text((1100, 190), date_display, fill=COLOR_SECONDARY, font=font_medium)

    if cur_icon_code:
        icon_img = get_icon(cur_icon_code, size=4)
        if icon_img:
            icon_img = icon_img.resize((300, 300))
            img.paste(icon_img, (500, 80), icon_img) # 第三個參數是 Alpha 遮罩

    # --- 五天預報 (含圖示) ---
    x_offset = 1000
    count = 0
    for d_str, temps in daily_data.items():
        if count >= 5: break
        if not temps: continue
        
        low = min(temps)
        high = max(temps)
        
        draw.text((x_offset, 310), d_str, fill=COLOR_SECONDARY, font=font_medium)
        
        # 貼上 OpenWeather 預報圖示
        f_icon_code = ow_icons.get(d_str)
        if f_icon_code:
            f_icon = get_icon(f_icon_code, size=2)
            if f_icon:
                f_icon = f_icon.resize((150, 150))
                img.paste(f_icon, (x_offset - 20, 370), f_icon)
                
        draw.text((x_offset, 530), f"{low}°|{high}°", fill=COLOR_PRIMARY, font=font_small)
        x_offset += 180
        count += 1

    # --- 左下詳細指標 ---
    details = [
        f"日出: {sunrise}", f"日落: {sunset}",
        f"風速: {wind} m/s", f"濕度: {humidity}%",
        f"氣壓: {pressure} hPa", f"降雨機率: {pop_value}%"
    ]
    y_offset = 600
    for text in details:
        draw.text((100, y_offset), text, fill=COLOR_PRIMARY, font=font_medium)
        y_offset += 100

    # --- 右下趨勢圖 ---
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

    # --- Footer ---
    update_str = local_time.strftime('%Y/%m/%d %H:%M:%S')
    draw.text((600, 1450), f"最後更新: {update_str} (CWA & OW)", fill=COLOR_SECONDARY, font=font_small)

    img.save('weather.png')
    print("圖片已成功存檔並更新！")

if __name__ == "__main__":
    update_weather()
