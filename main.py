import requests
from bs4 import BeautifulSoup
import re
import os
import html
from datetime import datetime, timezone

# =============================================================
#  بخش تنظیمات (Settings)
# =============================================================
PINNED_CONFIGS = [
    "ss://bm9uZTpmOGY3YUN6Y1BLYnNGOHAz@lil:360#%F0%9F%91%91%20%40express_alaki",
]

EXPIRY_HOURS = 12       
SEARCH_LIMIT_HOURS = 1  
ROTATION_LIMIT = 65      # تعداد کانفیگ برای فایل configs.txt
ROTATION_LIMIT_2 = 500   # تعداد کانفیگ برای فایل configs2.txt
# =============================================================

def extract_configs_logic(msg_div):
    for img in msg_div.find_all("img"):
        if 'emoji' in img.get('class', []) and img.get('alt'):
            img.replace_with(img['alt'])
    
    for br in msg_div.find_all("br"):
        br.replace_with("\n")
    
    full_text = html.unescape(msg_div.get_text())
    # لیست پروتکل‌ها (قابل ویرایش توسط شما)
    protocols = ['vless://', 'vmess://', 'trojan://', 'hysteria2://', 'hy2://']
    extracted = []
    
    lines = full_text.split('\n')
    for line in lines:
        starts = []
        for proto in protocols:
            for m in re.finditer(re.escape(proto), line):
                starts.append((m.start(), proto))
        
        starts.sort(key=lambda x: x[0])
        
        for i in range(len(starts)):
            start_pos, current_proto = starts[i]
            
            if i + 1 < len(starts):
                end_pos = starts[i+1][0]
                candidate = line[start_pos:end_pos]
            else:
                candidate = line[start_pos:]
            
            if '   ' in candidate:
                candidate = candidate.split('   ')[0]
            
            final_cfg = candidate.strip()
            if any(final_cfg.startswith(p) for p in protocols) and len(final_cfg) > 10:
                extracted.append(final_cfg)
    return extracted

def get_messages_within_limit(channel_username):
    url = f"https://t.me/s/{channel_username}"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200: return []
        soup = BeautifulSoup(response.text, 'html.parser')
        message_wraps = soup.find_all('div', class_='tgme_widget_message_wrap')
        valid_configs = []
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
                configs = extract_configs_logic(msg_text_div)
                for c in configs:
                    if c not in valid_configs:
                        valid_configs.append(c)
            except: continue
        return valid_configs
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
            if c not in all_known_configs and c not in PINNED_CONFIGS:
                new_entries.append([str(now), c])
                all_known_configs.append(c)

    combined = existing_data + new_entries
    valid_db_data = [item for item in combined if now - float(item[0]) < (EXPIRY_HOURS * 3600)]

    current_index = 0
    if os.path.exists('pointer.txt'):
        try:
            with open('pointer.txt', 'r') as f:
                current_index = int(f.read().strip())
        except: current_index = 0

    total_configs = len(valid_db_data)
    
    # منطق استخراج برای فایل اول (configs.txt)
    selected_1 = []
    next_index = 0
    if total_configs > 0:
        if current_index >= total_configs: current_index = 0
        end_index = current_index + ROTATION_LIMIT
        if end_index <= total_configs:
            selected_1 = [item[1] for item in valid_db_data[current_index : end_index]]
            next_index = end_index
        else:
            selected_1 = [item[1] for item in valid_db_data[current_index:] + valid_db_data[:ROTATION_LIMIT - (total_configs - current_index)]]
            next_index = ROTATION_LIMIT - (total_configs - current_index)

    # منطق استخراج برای فایل دوم (configs2.txt) - دقیقاً از همان مکان شروع
    selected_2 = []
    if total_configs > 0:
        end_index_2 = current_index + ROTATION_LIMIT_2
        if end_index_2 <= total_configs:
            selected_2 = [item[1] for item in valid_db_data[current_index : end_index_2]]
        else:
            selected_2 = [item[1] for item in valid_db_data[current_index:] + valid_db_data[:ROTATION_LIMIT_2 - (total_configs - current_index)]]

    # تابع داخلی برای حذف تکراری و نوشتن فایل
    def save_file(filename, config_list):
        final_list = []
        seen = set(PINNED_CONFIGS)
        for cfg in config_list:
            if cfg not in seen:
                final_list.append(cfg)
                seen.add(cfg)
        with open(filename, 'w', encoding='utf-8') as f:
            for pin in PINNED_CONFIGS: f.write(pin + "\n\n")
            for cfg in final_list: f.write(cfg + "\n\n")

    # ذخیره هر دو فایل
    save_file('configs.txt', selected_1)
    save_file('configs2.txt', selected_2)

    # ذخیره دیتابیس و پوینتر (پوینتر بر اساس فایل اول حرکت می‌کند تا هماهنگی حفظ شود)
    with open('data.temp', 'w', encoding='utf-8') as f:
        for ts, cfg in valid_db_data:
            if cfg not in PINNED_CONFIGS: f.write(f"{ts}|{cfg}\n")
    with open('pointer.txt', 'w', encoding='utf-8') as f:
        f.write(str(next_index))

if __name__ == "__main__":
    run()
