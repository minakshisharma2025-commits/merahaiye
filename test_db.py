from database import Database, DownloadLog
import json

db = Database('bollyflix_data.json')
count = db.get_today_download_count(1651746145)
is_prem = db.is_premium_user(1651746145)

print(f"Today count: {count}")
print(f"Is premium: {is_prem}")
