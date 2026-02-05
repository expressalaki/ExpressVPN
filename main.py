import requests
from bs4 import BeautifulSoup
import re
import os
from datetime import datetime, timedelta

# =============================================================
#  بخش تنظیمات
# =============================================================
EXPIRY_HOURS = 24  # زمان انقضا به ساعت
# =============================================================

def extract_configs_from_url(channel_username):
    url = f"https://t.me/s/{channel_username}"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200: return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        # پیدا کردن بخش‌های متنی پیام‌ها
        messages = soup.find_all('div', class_='tgme_widget_message_text')
        
        extracted_configs = []
        # الگو: شروع با پروتکل، ادامه با کاراکترهای مجاز (بدون اسپیس و تگ <)
        # این الگو باعث می‌شود متن‌های فارسی و اسپیس‌های بین کانفیگ‌ها حذف شوند
        pattern = r"(?:vless|vmess|trojan|ss|shadowsocks)://[^\s<]+"
        
        for msg in messages:
            # متن خام پیام را می‌گیریم
            text = msg.get_text(separator=" ") 
            # جستجوی دقیق برای پیدا کردن تمام موارد منطبق
            found = re.findall(pattern, text)
            for item in found:
                clean_config = item.strip()
                # جلوگیری از ورود موارد ناقص یا تکراری در یک پیام
                if clean_config and clean_config not in extracted_configs:
                    extracted_configs.append(clean_config)
        
        return extracted_configs
    except Exception as e:
        print(f"Error scraping {channel_username}: {e}")
        return []

def run():
    if not os.path.exists('channels.txt'):
        print("File channels.txt not found!")
        return

    with open('channels.txt', 'r') as f:
        channels = [line.strip() for line in f if line.strip()]

    existing_data = []
    if os.path.exists('data.temp'):
        with open('data.temp', 'r') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) == 2:
                    existing_data.append(parts)

    all_known_configs = [d[1] for d in existing_data]
    new_entries = []
    now = datetime.now()

    for ch in channels:
        found = extract_configs_from_url(ch)
        for c in found:
            # فقط اگر این کانفیگ قبلاً در دیتابیس نبود
            if c not in all_known_configs:
                # اضافه کردن به ابتدای لیست (جدیدترین‌ها اول بیایند)
                new_entries.insert(0, [str(now.timestamp()), c])
                all_known_configs.append(c)

    # ترکیب و اعمال قانون حذف 24 ساعته
    combined = new_entries + existing_data
    final_data = []
    for ts, cfg in combined:
        if now.timestamp() - float(ts) < (EXPIRY_HOURS * 3600):
            # بررسی دوباره برای حذف هرگونه متن اضافه احتمالی
            if "://" in cfg:
                final_data.append([ts, cfg])

    # ذخیره در configs.txt با یک خط فاصله کامل و واقعی
    with open('configs.txt', 'w', encoding='utf-8') as f:
        for i, (ts, cfg) in enumerate(final_data):
            f.write(cfg)
            # بعد از هر کانفیگ دو عدد اینتر می‌زند تا خط خالی ایجاد شود
            f.write("\n\n")

    # ذخیره دیتای سیستمی
    with open('data.temp', 'w', encoding='utf-8') as f:
        for ts, cfg in final_data:
            f.write(f"{ts}|{cfg}\n")

if __name__ == "__main__":
    run()
