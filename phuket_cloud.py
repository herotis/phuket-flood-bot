import requests
import os
from datetime import datetime, timedelta, timezone

CHANNEL_TOKEN = os.environ.get("CHANNEL_TOKEN", "").strip().replace("\ufeff","")
GROUP_ID = os.environ.get("GROUP_ID", "").strip()  # C639ec5a7366a2410ebb506d68a6b8c2a

if not CHANNEL_TOKEN or len(CHANNEL_TOKEN) < 100:
    print("❌ ไม่เจอ CHANNEL_TOKEN")
    exit(1)

print(f"Token length: {len(CHANNEL_TOKEN)} chars")
if GROUP_ID:
    print(f"Group ID: {GROUP_ID}")

THAI_TZ = timezone(timedelta(hours=7))
now_utc = datetime.now(timezone.utc)
now_thai = now_utc.astimezone(THAI_TZ)

PHUKET_ZONES = {
    "เมืองภูเก็ต ถ.บางกอก/เยาวราช": (7.8845, 98.3923),
    "ฉลอง หน้าวัดใต้": (7.8450, 98.3365),
    "วิชิต หน้าวังถลาง": (7.8720, 98.3600),
    "กะทู้ ถ.พระภูเก็ตแก้ว": (7.9092, 98.3350),
    "ป่าตอง ซอยนาใน": (7.8978, 98.3045),
    "ราไวย์ สามแยกในหาน": (7.7765, 98.3210),
    "ถลาง ถ.เทพกระษัตรี": (8.0300, 98.3600),
}

def send_line(message, to_group=None):
    # ถ้ามี group_id ให้ส่งเข้ากลุ่มด้วย push
    targets = []
    if to_group:
        targets.append(("push to group", to_group))
    else:
        # ถ้าไม่มี group ก็ broadcast ให้เพื่อนทุกคน (แบบเดิม)
        targets.append(("broadcast", None))

    for mode, target in targets:
        try:
            if mode == "push to group":
                url = "https://api.line.me/v2/bot/message/push"
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {CHANNEL_TOKEN}"}
                data = {"to": target, "messages": [{"type": "text", "text": message}]}
            else:
                url = "https://api.line.me/v2/bot/message/broadcast"
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {CHANNEL_TOKEN}"}
                data = {"messages": [{"type": "text", "text": message}]}
            
            r = requests.post(url, headers=headers, json=data, timeout=15)
            print(f"LINE {mode}: {r.status_code} - {r.text[:200]}")
        except Exception as e:
            print(f"LINE {mode} error: {e}")

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

time_str_thai = now_thai.strftime('%H:%M น. %d/%m/%y')

# ส่งไปที่ไหน: ถ้ามี GROUP_ID ให้ส่งเข้ากลุ่มนั้นเป็นหลัก
send_target = GROUP_ID if GROUP_ID else None

if alerts:
    msg = f"🚕 เตือนน้ำท่วมภูเก็ต (คลาวด์)\n" + "\n".join(alerts) + f"\nเวลา {time_str_thai}"
    send_line(msg, to_group=send_target)
else:
    print("ฝนปกติ ไม่ต้องเตือน")
    if is_manual:
        msg = f"✅ ระบบคลาวด์ภูเก็ตทำงานปกติ\nเวลา {time_str_thai} (เวลาไทย)\nฝนปกติทุกจุด:\n" + "\n".join(summary_lines[:6]) + "\n(จะเตือนอัตโนมัติเมื่อฝนหนักเกิน 40มม./3ชม.)"
        send_line(msg, to_group=send_target)
    elif now_thai.hour == 7:
        msg = f"✅ ระบบคลาวด์ยังทำงานปกติ {time_str_thai} - ฝนภูเก็ตปกติทุกจุด"
        send_line(msg, to_group=send_target)
