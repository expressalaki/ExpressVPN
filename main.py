import requests
from bs4 import BeautifulSoup
import re
import os
from datetime import datetime, timezone, timedelta

# =============================================================
#  تنظیمات اصلی
# =============================================================
EXPIRY_HOURS = 24      # کانفیگ‌ها بعد از 24 ساعت از فایل حذف شوند
SEARCH_LIMIT_HOURS = 1 # فقط پیام‌های 1 ساعت اخیر کانال بررسی شوند
# =============================================================

def get_messages_within_limit(channel_username):
    url = f"https://t.me/s/{channel_username}"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200: return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # پیدا کردن بلوک‌های پیام (شامل تاریخ و متن)
        message_wraps = soup.find_all('div', class_='tgme_widget_message_wrap')
        
        valid_configs = []
        
        # الگوی سخت‌گیرانه: فقط حروف انگلیسی، اعداد و علائم استاندارد URL
        # به محض رسیدن به فاصله یا حروف فارسی، متوقف می‌شود.
        pattern = r"(?:vless|vmess|trojan|ss|shadowsocks)://[a-zA-Z0-9\-_@.:?#%&=+]+"
        
        # زمان فعلی به صورت UTC (چون تلگرام زمان‌ها را UTC می‌زند)
        now_utc = datetime.now(timezone.utc)
        
        for wrap in message_wraps:
            try:
                # 1. استخراج زمان پیام
                time_tag = wrap.find('time')
                if not time_tag: continue
                
                # فرمت زمان تلگرام: 2023-10-25T10:30:00+00:00
                msg_time_str = time_tag['datetime']
                msg_time = datetime.fromisoformat(msg_time_str)
                
                # 2. بررسی شرط 1 ساعت (اگر پیام قدیمی است، رد شو)
                if (now_utc - msg_time).total_seconds() > (SEARCH_LIMIT_HOURS * 3600):
                    continue

                # 3. استخراج متن پیام
                msg_text_div = wrap.find('div', class_='tgme_widget_message_text')
                if not msg_text_div: continue

                # ترفند مهم: تبدیل <br> به فاصله برای جلوگیری از چسبیدن خطوط
                for br in msg_text_div.find_all('br'):
                    br.replace_with(' ')
                
                text = msg_text_div.get_text()
                
                # 4. استخراج کانفیگ‌ها با الگوی جدید
                found = re.findall(pattern, text)
                for item in found:
                    clean_config = item.strip()
                    # فیلتر نهایی برای اطمینان از سالم بودن لینک
                    if len(clean_config) > 10 and clean_config not in valid_configs:
                        valid_configs.append(clean_config)
                        
            except Exception as e:
                continue
                
        return valid_configs

    except Exception as e:
        print(f"Error scraping {channel_username}: {e}")
        return []

def run():
    if not os.path.exists('channels.txt'):
        return

    with open('channels.txt', 'r') as f:
        channels = [line.strip() for line in f if line.strip()]

    # خواندن دیتابیس موقت
    existing_data = []
    if os.path.exists('data.temp'):
        with open('data.temp', 'r') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) == 2:
                    existing_data.append(parts)

    all_known_configs = [d[1] for d in existing_data]
    new_entries = []
    now = datetime.now().timestamp()

    # فقط پیام‌های جدیدِ 1 ساعت اخیر بررسی می‌شوند
    for ch in channels:
        found = get_messages_within_limit(ch)
        for c in found:
            if c not in all_known_configs:
                new_entries.insert(0, [str(now), c])
                all_known_configs.append(c)

    # ترکیب و حذف موارد قدیمی‌تر از 24 ساعت
    combined = new_entries + existing_data
    final_data = []
    
    for ts, cfg in combined:
        # محاسبه عمر کانفیگ
        if now - float(ts) < (EXPIRY_HOURS * 3600):
            final_data.append([ts, cfg])

    # ذخیره فایل نهایی تمیز
    with open('configs.txt', 'w', encoding='utf-8') as f:
        for _, cfg in final_data:
            f.write(cfg)
            f.write("\n\n") # دو خط فاصله واقعی

    # آپدیت دیتابیس
    with open('data.temp', 'w', encoding='utf-8') as f:
        for ts, cfg in final_data:
            f.write(f"{ts}|{cfg}\n")

if __name__ == "__main__":
    run()
