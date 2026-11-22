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
BOT_ID = 6333102398
RESTART_TS = 1794601985  # 13.11.2026 20:33:05 UTC

# Список чатів/каналів для сканування (можеш дописувати свої)
CHATS_TO_SCAN = [
	"@avocado_group",
	"@bio_attacker_bot",
]

is_termux = bool(
	os.environ.get("TERMUX_APP__PACKAGE_NAME")
	or os.environ.get("TERMUX_APK_RELEASE")
)
scr_dir = os.path.dirname(os.path.abspath(__file__))
cur_dir = os.path.abspath(os.getcwd())

if is_termux and os.access("/sdcard", os.W_OK):
	db_dir = "/sdcard/ub4tg"
	os.makedirs(db_dir, exist_ok=True)
	txt_dir = db_dir
	CONFIG_PATH = os.path.join(db_dir, "conf.json")
elif os.name == "nt" and (
	scr_dir.lower().startswith(r"d:\misc\projects\python")
	or cur_dir.lower().startswith(r"d:\misc\projects\python")
):
	db_dir = r"D:\Misc\projects\Python"
	txt_dir = scr_dir
else:
	db_dir = scr_dir
	txt_dir = scr_dir

OUT_DB = os.path.join(db_dir, "0.sqlite")
OUT_ZIP = os.path.join(db_dir, "0.zip")
SCAN_TXT = os.path.join(txt_dir, "scan.txt")

def set_file_dates(filepath: str, ts: int):
	if not ts or not (ts > 0) or not os.path.exists(filepath):
		return
	try:
		os.utime(filepath, (ts, ts))
	except Exception:
		pass
	if os.name == "nt":
		try:
			import pywintypes
			import win32con
			import win32file
			wintime = pywintypes.Time(ts)
			handle = win32file.CreateFile(
				filepath,
				win32con.GENERIC_WRITE,
				win32con.FILE_SHARE_READ
				| win32con.FILE_SHARE_WRITE
				| win32con.FILE_SHARE_DELETE,
				None,
				win32con.OPEN_EXISTING,
				win32con.FILE_ATTRIBUTE_NORMAL,
				None
			)
			win32file.SetFileTime(handle, wintime, wintime, wintime)
			handle.close()
		except Exception:
			pass

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
	cfg = json.load(f)

api_id = int(cfg["api_id"])
api_hash = str(cfg["api_hash"])
db_pymysql = bool(cfg.get("db_pymysql", False))
mysql_conf = cfg.get("mysql") if isinstance(cfg.get("mysql"), dict) else {
	"host": "localhost",
	"user": "root",
	"password": "",
	"db": "db"
}
restart_date_str = datetime.fromtimestamp(
	RESTART_TS, tz=timezone.utc
).strftime("%d.%m.%Y")

async def run_scan():
	global db_pymysql
	con = None
	d = None
	if db_pymysql:
		try:
			import pymysql
			import pymysql.cursors
			con = pymysql.connect(
				host=str(mysql_conf.get("host", "localhost")),
				user=str(mysql_conf.get("user", "root")),
				password=str(mysql_conf.get("password", "")),
				db=str(mysql_conf.get("db", "db")),
				charset="utf8mb4",
				autocommit=False,
				cursorclass=pymysql.cursors.DictCursor
			)
			d = con.cursor()
			print("✅ Підключено до MySQL")
			d.execute("""CREATE TABLE IF NOT EXISTS `tg_bio_users` (
				`user_id` bigint(20) unsigned NOT NULL DEFAULT '0',
				`when_int` int(11) unsigned NOT NULL DEFAULT '0',
				`profit` int(11) unsigned NOT NULL DEFAULT '1',
				`p_name` varchar(200) CHARACTER SET utf8mb4
					NOT NULL DEFAULT '',
				`p_upd` int(11) unsigned NOT NULL DEFAULT '0',
				UNIQUE KEY `user_id` (`user_id`)
			);""")
			con.commit()
			try:
				d.execute(
					"ALTER TABLE `tg_bio_users` "
					"ADD `p_name` varchar(200) CHARACTER SET utf8mb4 "
					"NOT NULL DEFAULT '' AFTER `profit`, "
					"ADD `p_upd` int(11) unsigned NOT NULL DEFAULT '0' "
					"AFTER `p_name`;"
				)
				con.commit()
			except Exception:
				pass
		except Exception as e:
			print(f"⚠️ MySQL недоступний ({e}) — працюю на SQLite")
			db_pymysql = False
			con = None
			d = None
	
	async with TelegramClient(SESS_NAME, api_id, api_hash, timeout=300) as client:
		me = await client.get_me()
		my_id = int(me.id)
		print(f"✅ Підключено як {my_id}")
		print(f"🗄 База: {OUT_DB}")
		print(f"📄 Лог:  {SCAN_TXT}")
		
		conn = sqlite3.connect(OUT_DB)
		c = conn.cursor()
		c.execute("""CREATE TABLE IF NOT EXISTS avocado (
			user_id	INTEGER NOT NULL DEFAULT 0 UNIQUE,
			when_int	INTEGER NOT NULL DEFAULT 0,
			bio_int	INTEGER NOT NULL DEFAULT 1,
			expr_int	INTEGER NOT NULL DEFAULT {},
			expr_str	VARCHAR NOT NULL DEFAULT '{}',
			p_name	VARCHAR(200) NOT NULL DEFAULT '',
			p_upd	INTEGER NOT NULL DEFAULT 0
		)""".format(RESTART_TS, restart_date_str))
		conn.commit()
		try:
			c.execute(
				"ALTER TABLE avocado "
				"ADD COLUMN p_name VARCHAR(200) NOT NULL DEFAULT ''"
			)
			conn.commit()
		except Exception:
			pass
		try:
			c.execute(
				"ALTER TABLE avocado "
				"ADD COLUMN p_upd INTEGER NOT NULL DEFAULT 0"
			)
			conn.commit()
		except Exception:
			pass
		
		total_added = 0
		max_when = 0
		id_re = re.compile(r'tg://openmessage\?user_id=(\d+)')
		
		with open(SCAN_TXT, "w", encoding="utf-8-sig") as wf:
			wf.write("")
		
		wf = open(SCAN_TXT, "a", encoding="utf-8")
		try:
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
					if not (msg_ts >= RESTART_TS):
						break
					max_when = max(max_when, msg_ts)
					checked += 1
					
					if m.raw_text and m.entities:
						h = utils.sanitize_parse_mode("html").unparse(
							m.raw_text, m.entities
						)
						
						dt_s = m.date.strftime("%d.%m.%Y %H:%M:%S")
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
								(user_id, when_int, bio_int,
								expr_int, expr_str)
								VALUES (?, ?, 1, ?, ?)""",
								(uid, msg_ts, RESTART_TS, restart_date_str)
							)
							if c.rowcount > 0:
								added_chat += 1
							if db_pymysql and d:
								try:
									d.execute(
										"""INSERT IGNORE INTO `tg_bio_users`
										(`user_id`, `when_int`, `profit`)
										VALUES (%s, %s, 1)""",
										(uid, msg_ts)
									)
								except Exception:
									pass
					
					if checked % 100 == 0:
						wf.flush()
					if checked % 200 == 0:
						conn.commit()
						if db_pymysql and con:
							con.commit()
						print(
							f"  ...перевірено {checked} повід., "
							f"нових ID: {added_chat}"
						)
						await asyncio.sleep(0.4)
				
				wf.flush()
				conn.commit()
				if db_pymysql and con:
					con.commit()
				total_added += added_chat
				print(
					f"✅ {title}: перевірено {checked}, "
					f"додано нових ID: {added_chat}"
				)
		finally:
			wf.flush()
			wf.close()
			if con:
				try:
					con.close()
				except Exception:
					pass
		
		c.execute("SELECT MAX(when_int) FROM avocado")
		row_max = c.fetchone()
		if row_max and row_max[0]:
			max_when = max(max_when, int(row_max[0]))
		
		print("🗜️ Оптимізую та стискаю 0.sqlite...")
		c.execute("VACUUM")
		c.execute("PRAGMA optimize")
		conn.commit()
		conn.close()
		
		if max_when > 0:
			set_file_dates(OUT_DB, max_when)
			set_file_dates(SCAN_TXT, max_when)
		
		with zipfile.ZipFile(
			OUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
		) as zf:
			zf.write(OUT_DB, arcname="0.sqlite")
		
		if max_when > 0:
			set_file_dates(OUT_ZIP, max_when)
		
		dt_latest = (
			datetime.fromtimestamp(max_when, tz=timezone.utc).strftime(
				"%d.%m.%Y %H:%M:%S UTC"
			)
			if max_when > 0 else "—"
		)
		print(
			f"🎉 Готово! Додано в {OUT_DB}: {total_added} | "
			f"Дата файлів: {dt_latest}"
		)

if __name__ == "__main__":
	asyncio.run(run_scan())
