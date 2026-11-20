# -*- coding: utf-8 -*-
import asyncio
import json
import os
import re
import sqlite3
import zipfile
from datetime import datetime, timezone
from telethon import TelegramClient, utils

CONFIG_PATH = "conf.json"
SESS_NAME = "tl-ub"
OUT_DB = "0.sqlite"
BOT_ID = 6333102398
RESTART_TS = 1794601985  # 13.11.2026 20:33:05 UTC

# Список чатів/каналів для сканування (можеш дописувати свої)
CHATS_TO_SCAN = [
	"@avocado_group",
	"@bio_attacker_bot",
]

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
	cfg = json.load(f)

api_id = int(cfg["api_id"])
api_hash = str(cfg["api_hash"])
restart_date_str = datetime.fromtimestamp(
	RESTART_TS, tz=timezone.utc
).strftime("%d.%m.%Y")

async def run_scan():
	async with TelegramClient(SESS_NAME, api_id, api_hash, timeout=300) as client:
		me = await client.get_me()
		my_id = int(me.id)
		print(f"✅ Підключено як {my_id}")
		
		conn = sqlite3.connect(OUT_DB)
		c = conn.cursor()
		c.execute("""CREATE TABLE IF NOT EXISTS avocado (
			user_id	INTEGER NOT NULL DEFAULT 0 UNIQUE,
			when_int	INTEGER NOT NULL DEFAULT 0,
			bio_int	INTEGER NOT NULL DEFAULT 1,
			expr_int	INTEGER NOT NULL DEFAULT {},
			expr_str	VARCHAR NOT NULL DEFAULT '{}'
		)""".format(RESTART_TS, restart_date_str))
		conn.commit()
		
		total_added = 0
		id_re = re.compile(r'tg://openmessage\?user_id=(\d+)')
		
		win_scan_txt = None
		if os.name == "nt":
			base_win_dir = r"D:\Misc\projects\Python"
			scr_dir = os.path.dirname(os.path.abspath(__file__))
			if scr_dir.lower().startswith(r"d:\misc\projects\python"):
				win_scan_txt = os.path.join(scr_dir, "scan.txt")
				with open(win_scan_txt,"w",encoding="utf-8-sig") as wf:
					wf.write("")
		
		for chat_ref in CHATS_TO_SCAN:
			try:
				entity = await client.get_entity(chat_ref)
			except Exception as e:
				print(f"⚠️ Пропускаю {chat_ref}: {e}")
				continue
			
			title = getattr(entity, "title", None) or str(chat_ref)
			print(f"🔍 Сканую {title}...")
			checked = 0
			added_chat = 0
			
			async for m in client.iter_messages(entity, from_user=BOT_ID):
				msg_ts = int(m.date.timestamp())
				if msg_ts < RESTART_TS:
					break
				checked += 1
				
				if m.raw_text and m.entities:
					h = utils.sanitize_parse_mode("html").unparse(
						m.raw_text, m.entities
					)
					
					if win_scan_txt:
						dt_s = m.date.strftime("%d.%m.%Y %H:%M:%S")
						with open(win_scan_txt, "a", encoding="utf-8") as wf:
							wf.write(
								f"=== [{title}] MSG {m.id} | {dt_s} UTC ===\n"
								f"{h}\n\n"
							)
					
					for uid_s in id_re.findall(h):
						uid = int(uid_s)
						if uid in (my_id, BOT_ID, 1124824021):
							continue
						c.execute(
							"""INSERT OR IGNORE INTO avocado
							(user_id, when_int, bio_int, expr_int, expr_str)
							VALUES (?, ?, 1, ?, ?)""",
							(uid, msg_ts, RESTART_TS, restart_date_str)
						)
						if c.rowcount > 0:
							added_chat += 1
				
				if checked % 200 == 0:
					conn.commit()
					print(f"  ...перевірено {checked} повід., нових ID: {added_chat}")
					await asyncio.sleep(0.4)
				
			conn.commit()
			total_added += added_chat
			print(f"✅ {title}: перевірено {checked}, додано нових ID: {added_chat}")
			
		print("🗜️ Оптимізую та стискаю 0.sqlite...")
		c.execute("VACUUM")
		c.execute("PRAGMA optimize")
		conn.commit()
		conn.close()
		
		with zipfile.ZipFile("0.zip", "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
			zf.write(OUT_DB)
		
		print(f"🎉 Готово! Усього унікальних записів додано в {OUT_DB}: {total_added}")

if __name__ == "__main__":
	asyncio.run(run_scan())
