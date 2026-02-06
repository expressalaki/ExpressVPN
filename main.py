import requests
from bs4 import BeautifulSoup
import re
import os
from datetime import datetime, timezone

# =============================================================
#  بخش تنظیمات
# =============================================================
EXPIRY_HOURS = 24      # زمان حذف کانفیگ‌های قدیمی (ساعت)
SEARCH_LIMIT_HOURS = 1 # بررسی پیام‌های X ساعت اخیر کانال
# =============================================================

def extract_configs_smart(msg_text_div):
    """
    استخراج هوشمند با جایگزینی ایموجی‌ها و اعمال قوانین توقف
    """
    # 1. تبدیل تگ‌های ایموجی تلگرام به متن واقعی (برای جلوگیری از قطع شدن کانفیگ)
    for img in msg_text_div.find_all('img', class_='emoji'):
        if img.has_attr('alt'):
            img.replace_with(img['alt'])
    
    # 2. دریافت متن با حفظ ساختار خطوط
    text = msg_text_div.get_text(separator="\n")
    
    configs = []
    protocols = ['vless://', 'vmess://', 'ss://', 'trojan://', 'shadowsocks://']
    
    # جدا کردن بر اساس خط (شرط: توقف در خط بعد)
    lines = text.split('\n')
    
    for line in lines:
        # پیدا کردن تمام نقاط شروع پروتکل‌ها در این خط
        starts = []
        for proto in protocols:
            for m in re.finditer(re.escape(proto), line):
                starts.append(m.start())
        starts.sort()
        
        for i in range(len(starts)):
            start_pos = starts[i]
            
            # شرط: توقف در صورت شروع پروتکل جدید در همان خط
            if i + 1 < len(starts):
                end_pos = starts[i+1]
                chunk = line[start_pos:end_pos]
            else:
                # شرط: توقف در اتمام سطر یا اتمام پیام
                chunk = line[start_pos:]
            
            # شرط: توقف در صورت مشاهده 3 فاصله پشت سر هم
            if '   ' in chunk:
                chunk = chunk.split('   ')[0]
            
            clean_cfg = chunk.strip()
            # فیلتر برای اطمینان از اینکه حداقل طول یک کانفیگ را دارد (مثلاً ss://a)
            if len(clean_cfg) > 7:
                configs.append(clean_cfg)
                
    return configs

def get_messages_within_limit(channel_username):
    url = f"https://t.me/s/{channel_username}"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200: return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        message_wraps = soup.find_all('div', class_='tgme_widget_message_wrap')
        
        extracted_configs = []
        now_utc = datetime.now(timezone.utc)
        
        for wrap in message_wraps:
            try:
                time_tag = wrap.find('time')
                if not time_tag: continue
                msg_time = datetime.fromisoformat(time_tag['datetime'])
                if (now_utc - msg_time).total_seconds() > (SEARCH_LIMIT_HOURS * 3600):
                    continue

                msg_text_div = wrap.find('div', class_='tgme_widget_message_text')
                if not msg_text_div: continue

                # فراخوانی تابع استخراج هوشمند با پاس دادن کل المنت HTML
                configs = extract_configs_smart(msg_text_div)
                for c in configs:
                    if c not in extracted_configs:
                        extracted_configs.append(c)
                        
            except: continue
        return extracted_configs
    except: return []

def run():
    if not os.path.exists('channels.txt'): return
    with open('channels.txt', 'r') as f:
        channels = [line.strip() for line in f if line.strip()]

    existing_data = []
    if os.path.exists('data.temp'):
        with open('data.temp', 'r') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) == 2: existing_data.append(parts)

    all_known_configs = [d[1] for d in existing_data]
    new_entries = []
    now = datetime.now().timestamp()

    for ch in channels:
        found = get_messages_within_limit(ch)
        for c in found:
            if c not in all_known_configs:
                new_entries.insert(0, [str(now), c])
                all_known_configs.append(c)

    combined = new_entries + existing_data
    final_data = [item for item in combined if now - float(item[0]) < (EXPIRY_HOURS * 3600)]

    with open('configs.txt', 'w', encoding='utf-8') as f:
        for _, cfg in final_data:
            f.write(cfg + "\n\n")

    with open('data.temp', 'w', encoding='utf-8') as f:
        for ts, cfg in final_data:
            f.write(f"{ts}|{cfg}\n")

if __name__ == "__main__":
    run()
