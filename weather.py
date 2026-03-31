import os
import requests
from PIL import Image, ImageDraw
from datetime import datetime

API_KEY = os.environ.get("OPENWEATHER_API_KEY")
CITY = "Taipei, TW"
URL = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric&lang=zh_tw"

def update_weather():
    try:
        res = requests.get(URL).json()
        temp = res['main']['temp']
        desc = res['weather'][0]['description']
        text = f"{temp} C, {desc}"
    except Exception:
        text = "Error fetching data"

    img = Image.new('RGB', (2048, 1536), color='white')
    draw = ImageDraw.Draw(img)
    time_str = datetime.now().strftime('%Y %m %d %H:%M:%S')
    
    draw.text((100, 100), text, fill='black')
    draw.text((100, 200), time_str, fill='black')
    
    img.save('weather.png')

if __name__ == "__main__":
    update_weather()
