#!/usr/bin/env python3
"""
Clear Telegram Update Queue
Removes all pending messages so the bot doesn't spam when it starts
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv('TELEGRAM_BOT_TOKEN')

if not token:
    print("❌ TELEGRAM_BOT_TOKEN not found in .env")
    exit(1)

print("🧹 Clearing Telegram update queue...")
print("=" * 60)

url = f"https://api.telegram.org/bot{token}/getUpdates"

try:
    # Get all pending updates
    response = requests.get(url, timeout=5)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('ok'):
            updates = data.get('result', [])
            
            if not updates:
                print("✅ Queue is already clean! No pending messages.")
            else:
                print(f"Found {len(updates)} pending messages")
                
                # Get the ID of the last update
                last_update_id = updates[-1].get('update_id', 0)
                
                # Call getUpdates with offset to acknowledge all messages
                clear_response = requests.get(
                    url,
                    params={"offset": last_update_id + 1},
                    timeout=5
                )
                
                if clear_response.status_code == 200:
                    print(f"✅ Successfully cleared {len(updates)} messages from queue")
                    print(f"   Next update_id will be: {last_update_id + 1}")
                else:
                    print("❌ Failed to clear queue")
        else:
            print("❌ Telegram API returned error")
            print(data)
    else:
        print(f"❌ HTTP Error: {response.status_code}")

except requests.Timeout:
    print("❌ Request timeout")
except Exception as e:
    print(f"❌ Error: {e}")

print("=" * 60)
