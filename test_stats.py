import traceback
from database import db

try:
    print(db.get_stats())
except Exception as e:
    traceback.print_exc()
