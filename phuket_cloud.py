import requests
import os
from datetime import datetime

CHANNEL_TOKEN = os.environ.get("CHANNEL_TOKEN", "").strip().replace("\ufeff","")

if not CHANNEL_TOKEN or len(CHANNEL_TOKEN) < 100:
    print("❌ ไม่เจอ CHANNEL_TOKEN")
    exit(1)

print(f"Token length: {len(CHANNEL_TOKEN)} chars")

PHUKET_ZONES = {
    "เมืองภูเก็ต ถ.บางกอก/เยาวราช": (7.8845, 98.3923),
    "ฉลอง หน้าวัดใต้": (7.8450, 98.3365),
    "วิชิต หน้าวังถลาง": (7.8720, 98.3600),
    "กะทู้ ถ.พระภูเก็ตแก้ว": (7.9092, 98.3350),
    "ป่าตอง ซอยนาใน": (7.8978, 98.3045),
    "ราไวย์ สามแยกในหาน": (7.7765, 98.3210),
    "ถลาง ถ.เทพกระษัตรี": (8.0300, 98.3600),
}

def send_line(message):
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {CHANNEL_TOKEN}"}
    data = {"messages": [{"type": "text", "text": message}]}
    r = requests.post(url, headers=headers, json=data, timeout=15)
    print(f"LINE Status: {r.status_code} - {r.text[:300]}")
    return r.status_code == 200

def check_rain(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=precipitation&daily=precipitation_sum&timezone=Asia/Bangkok&forecast_days=2&past_days=1"
        d = requests.get(url, timeout=10).json()
        rain_3h = sum(d['hourly']['precipitation'][-3:])
        rain_today = d['daily']['precipitation_sum'][1]
        return rain_3h, rain_today
    except Exception as e:
        print(f"check error {e}")
        return 0,0

now = datetime.now()
print(f"เริ่มเช็ค {now.strftime('%H:%M %d/%m/%Y')} Asia/Bangkok")
is_manual = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"

alerts = []
summary_lines = []
for zone, (lat, lon) in PHUKET_ZONES.items():
    r3, rToday = check_rain(lat, lon)
    print(f"{zone}: 3ชม={r3:.0f}มม. วันนี้={rToday:.0f}มม.")
    summary_lines.append(f"• {zone}: {r3:.0f}มม./3ชม. วันนี้ {rToday:.0f}มม.")
    if r3 >= 40:
        alerts.append(f"🚨 {zone} ฝนหนัก {r3:.0f}มม./3ชม. วันนี้ {rToday:.0f}มม.")
    elif rToday >= 80:
        alerts.append(f"⚠️ {zone} ฝนสะสม {rToday:.0f}มม. เฝ้าระวัง")

if alerts:
    msg = "🚕 เตือนน้ำท่วมภูเก็ต (ระบบคลาวด์)\n" + "\n".join(alerts) + f"\nเวลา {now.strftime('%H:%M %d/%m')}"
    send_line(msg)
else:
    print("ฝนปกติ ไม่ต้องเตือน (แต่ถ้ากด Run มือจะส่งสรุปให้ดู)")
    # ถ้ากด Run ด้วยมือ ให้ส่งสรุปฝนปกติไปด้วย เพื่อให้รู้ว่าระบบทำงาน
    if is_manual:
        msg = f"✅ ระบบคลาวด์ภูเก็ตทำงานปกติ\nเวลา {now.strftime('%H:%M %d/%m')}\nฝนปกติทุกจุด:\n" + "\n".join(summary_lines[:6]) + "\n(จะเตือนอัตโนมัติเมื่อฝนหนักเกิน 40มม./3ชม.)"
        send_line(msg)
    elif now.hour == 0:  # 07:00 Bangkok = 00:00 UTC ส่งสรุปวันละครั้ง
        msg = f"✅ ระบบคลาวด์ยังทำงานปกติ {now.strftime('%d/%m %H:%M')} - ฝนภูเก็ตปกติทุกจุด"
        send_line(msg)
