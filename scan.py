# -*- coding: utf-8 -*-
import asyncio
import json
import os
import re
import shutil
import sqlite3
import zipfile
from datetime import datetime, timezone
from telethon import TelegramClient, utils

CONFIG_PATH = "conf.json"
SESS_NAME = (
	"scan" if os.path.exists("scan.session")
	else ("tl-scan" if os.path.exists("tl-scan.session") else "tl-ub")
)
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

is_win_py_sub = bool(
	os.name == "nt"
	and (
		scr_dir.lower().startswith(r"d:\misc\projects\python")
		or cur_dir.lower().startswith(r"d:\misc\projects\python")
	)
)

if is_termux and os.access("/sdcard", os.W_OK):
	db_dir = "/sdcard/ub4tg"
	os.makedirs(db_dir, exist_ok=True)
	txt_dir = db_dir
	CONFIG_PATH = os.path.join(db_dir, "conf.json")
elif is_win_py_sub:
	db_dir = r"D:\Misc\projects\Python"
	txt_dir = scr_dir
else:
	db_dir = scr_dir
	txt_dir = scr_dir

OUT_DB = os.path.join(db_dir, "0.sqlite")
OUT_ZIP = os.path.join(db_dir, "0.zip")
NOEB_PATH = os.path.join(db_dir, "noeb.json")
SCAN_CHAT_TXT = os.path.join(txt_dir, "scan_chat.txt")
SCAN_PM_TXT = os.path.join(txt_dir, "scan_pm.txt")

noeb = []
for cand_n in (NOEB_PATH, "noeb.json"):
	if os.path.exists(cand_n):
		try:
			with open(cand_n, "r", encoding="utf-8") as nf:
				raw_noeb = json.load(nf)
				if isinstance(raw_noeb, list):
					for x_id in raw_noeb:
						xi = int(x_id)
						if xi >= 100 and xi not in noeb:
							noeb.append(xi)
			break
		except Exception:
			pass

def add_noeb(bad_uid: int) -> bool:
	global noeb
	try:
		bad_uid = int(bad_uid)
	except Exception:
		return False
	
	if not (100 < bad_uid < 10000) or bad_uid in noeb:
		return False
	
	noeb.append(bad_uid)
	return True

def save_noeb(items=None):
	global noeb
	if not items:
		return
	
	added = 0
	for raw_x in items:
		try:
			xi = int(raw_x)
			if 100 < xi < 10000 and xi not in noeb:
				noeb.append(xi)
				added += 1
		except Exception:
			pass
	
	if added > 0:
		try:
			with open(NOEB_PATH, "w", encoding="utf-8") as nf:
				json.dump(noeb, nf, ensure_ascii=False, indent="\t")
		except Exception:
			pass

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

INFECT_VERBS_RE = re.compile(
	r'(?:infected|заразил[ао]?|подверг(?:ла|ся)?|йобнув|сикди|'
	r'насрал[ао]?|выебал[ао]?|атаковал[ао]?|инфицировал[ао]?|'
	r'напугал[ао]?|нокаутировал[ао]?|обманул[ао]?|оглушил[ао]?|'
	r'поставил[ао]?|рассмешил[ао]?|угостил[ао]?)',
	re.IGNORECASE
)
SKIP_MSG_RE = re.compile(
	r'(?s).*(?:Active\s+victims|Активные\s+жертвы|'
	r'(?:🧪\s*)?(?:Pathogens|Свободных патогенов)\s*:|'
	r'(?:👩🏻‍🔬|👨🏻‍🔬)\s*(?:Qualification|Квалификация)\s*:)',
	re.IGNORECASE
)
BIO_RE = re.compile(
	r'(?:Profit|Прибыль|Bio-experience gained|'
	r'верир|потери|приносит|корма):\s*'
	r'(?:<strong>)?\+?([\d\.,]+k?)(?:</strong>)?',
	re.IGNORECASE
)
DAYS_RE = re.compile(
	r'(?:Infection duration|Длительность заражения|'
	r'на|for|ещё)\s*:?\s*(\d{1,3})\s*(?:d|д)',
	re.IGNORECASE
)
VIR_RE = re.compile(r'[«“"]([^»”"\n]{2,180})[»”"]')
NO_LAB_RE = re.compile(
	r'(?:has\s+no\s+laboratory|has\s+not\s+registered|'
	r'cannot\s+infect|can\'t\s+infect|unable\s+to\s+infect|'
	r'player\s+not\s+found|user\s+not\s+found|invalid\s+target|'
	r'is\s+a\s+bot|юзер\s+не\s+знайдений|нет\s+лаборатории|'
	r'не\s+зарегистрирован|не\s+является\s+игроком|'
	r'нельзя\s+заразить|невозможно\s+заразить|'
	r'недоступен\s+для\s+заражения|игрок\s+не\s+найден|'
	r'пользователь\s+не\s+найден|объект\s+не\s+найден|'
	r'нельзя\s+заражать\s+ботов)',
	re.IGNORECASE
)

def parse_attack_info(html_txt: str, plain_txt: str, msg_ts: int):
	bio = 1
	bm = BIO_RE.search(html_txt)
	if bm:
		try:
			rb = bm.group(1).replace(',', '.')
			if rb.lower().endswith('k'):
				val = int(float(rb[:-1]) * 1000)
			else:
				val = int(float(rb))
			if val >= 1:
				bio = val
		except Exception:
			pass
	
	until_ts = RESTART_TS
	until_str = restart_date_str
	dm = DAYS_RE.search(plain_txt)
	if dm:
		try:
			d_val = int(dm.group(1))
			if 1 <= d_val <= 365:
				until_ts = msg_ts + (d_val * 86400)
				until_str = datetime.fromtimestamp(
					until_ts, tz=timezone.utc
				).strftime("%d.%m.%Y")
		except Exception:
			pass
	
	p_name = ''
	vm = VIR_RE.search(plain_txt)
	if vm:
		p_name = vm.group(1).strip()
	
	return bio, until_ts, until_str, p_name


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
				autocommit=True,
				cursorclass=pymysql.cursors.DictCursor
			)
			d = con.cursor()
			print("✅ Підключено до MySQL")
			d.execute("""CREATE TABLE IF NOT EXISTS `tg_bio_attack` (
				`date` int(11) unsigned NOT NULL DEFAULT '0',
				`who_id` bigint(20) unsigned NOT NULL DEFAULT '0',
				`p_name` varchar(200) CHARACTER SET utf8mb4
					NOT NULL DEFAULT '',
				`user_id` bigint(20) unsigned NOT NULL DEFAULT '0',
				`profit` int(11) unsigned NOT NULL DEFAULT '1',
				`until_int` int(11) unsigned NOT NULL DEFAULT '0',
				`until_str` varchar(11) NOT NULL DEFAULT '0',
				UNIQUE KEY `UNIQUE` (`who_id`,`user_id`)
			);""")
			con.commit()
			try:
				d.execute(
					"ALTER TABLE `tg_bio_attack` "
					"ADD `p_name` varchar(200) CHARACTER SET utf8mb4 "
					"NOT NULL DEFAULT '' AFTER `who_id`;"
				)
				con.commit()
			except Exception:
				pass
			
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
		print(f"📄 Логи: {SCAN_CHAT_TXT} | {SCAN_PM_TXT}")
		
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
		
		try:
			for chat_ref in CHATS_TO_SCAN:
				try:
					entity = await client.get_entity(chat_ref)
				except Exception as e:
					print(f"⚠️ Пропускаю {chat_ref}: {e}")
					continue

				is_pm_src = int(getattr(entity, "id", 0)) == BOT_ID
				cur_txt = SCAN_PM_TXT if is_pm_src else SCAN_CHAT_TXT
				with open(cur_txt, "w", encoding="utf-8-sig") as wf:
					wf.write("")
				wf = open(cur_txt, "a", encoding="utf-8")

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
						t = m.raw_text
						h = utils.sanitize_parse_mode("html").unparse(
							t, m.entities
						)
						
						dt_s = m.date.strftime("%d.%m.%Y %H:%M:%S")
						wf.write(
							f"=== [{title}] MSG {m.id} | {dt_s} UTC ===\n"
							f"{h}\n\n"
						)
						
						ids = [
							int(x) for x in id_re.findall(h)
							if int(x) >= 100
						]
						
						if NO_LAB_RE.search(t):
							t_low = t.lower()
							bad_ids = [x for x in ids if x != my_id]
							if (
								'самого себя' not in t_low
								and 'yourself' not in t_low
								and bad_ids
							):
								bad_uid = bad_ids[0]
								if bad_uid not in noeb:
									add_noeb(bad_uid)
									
								c.execute(
									"DELETE FROM avocado WHERE user_id = ?",
									(bad_uid,)
								)
								if db_pymysql and d:
									try:
										d.execute(
											"DELETE FROM `tg_bio_users` "
											"WHERE `user_id` = %s",
											(bad_uid,)
										)
										d.execute(
											"DELETE FROM `tg_bio_attack` "
											"WHERE `user_id` = %s",
											(bad_uid,)
										)
									except Exception as e:
										print(f"⚠️ MySQL err: {e}")
							continue
						
						for uid in ids:
							if uid in noeb:
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
								except Exception as e:
									print(f"⚠️ MySQL err: {e}")
						
						if (
							len(ids) >= 2
							and not SKIP_MSG_RE.search(t)
							and INFECT_VERBS_RE.search(t)
						):
							who_id = ids[0]
							victim_id = ids[1]
							if who_id != victim_id:
								bio, until_ts, until_str, p_name = (
									parse_attack_info(h, t, msg_ts)
								)
								if p_name:
									c.execute(
										"""UPDATE avocado
										SET p_name = ?, p_upd = ?
										WHERE user_id = ?
										AND (p_name = '' OR p_upd < ?)""",
										(p_name, msg_ts, who_id, msg_ts)
									)
									if db_pymysql and d:
										try:
											d.execute(
												"""INSERT INTO `tg_bio_users`
												(`user_id`, `when_int`,
												`profit`, `p_name`, `p_upd`)
												VALUES (%s, %s, 1, %s, %s)
												ON DUPLICATE KEY UPDATE
													p_name = IF(
														p_name = ''
														OR VALUES(p_upd) > p_upd,
														VALUES(p_name),
														p_name
													),
													p_upd = IF(
														p_name = ''
														OR VALUES(p_upd) > p_upd,
														VALUES(p_upd),
														p_upd
													)""",
												(who_id, msg_ts, p_name, msg_ts)
											)
										except Exception:
											pass
								if db_pymysql and d:
									try:
										d.execute(
											"""INSERT INTO `tg_bio_attack`
											(`date`, `who_id`, `p_name`,
											`user_id`, `profit`,
											`until_int`, `until_str`)
											VALUES (%s, %s, %s, %s, %s, %s, %s)
											ON DUPLICATE KEY UPDATE
												date = IF(VALUES(date) >= date,
													VALUES(date), date),
												p_name = IF(
													VALUES(p_name) != ''
													AND VALUES(date) >= date,
													VALUES(p_name), p_name
												),
												profit = IF(VALUES(date) >= date,
													VALUES(profit), profit),
												until_int = IF(
													VALUES(date) >= date,
													VALUES(until_int), until_int
												),
												until_str = IF(
													VALUES(date) >= date,
													VALUES(until_str), until_str
												)""",
											(
												msg_ts, who_id, p_name,
												victim_id, bio,
												until_ts, until_str
											)
										)
									except Exception as e:
										print(f"⚠️ MySQL err: {e}")
					
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
				wf.close()
				conn.commit()
				if db_pymysql and con:
					con.commit()
				total_added += added_chat
				print(
					f"✅ {title}: перевірено {checked}, "
					f"додано нових ID: {added_chat}"
				)

		finally:
			
			if wf and not wf.closed: 
				wf.flush(); 
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
		save_noeb()
		conn.commit()
		conn.close()
		
		if max_when > 0:
			set_file_dates(OUT_DB, max_when)
			set_file_dates(SCAN_CHAT_TXT, max_when)
			set_file_dates(SCAN_PM_TXT, max_when)
		
		with zipfile.ZipFile(
			OUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
		) as zf:
			zf.write(OUT_DB, arcname="0.sqlite")
		
		if max_when > 0:
			set_file_dates(OUT_ZIP, max_when)
		
		local_tg_dir = r"D:\Misc\projects\localhost\tg"
		if is_win_py_sub and os.path.isdir(local_tg_dir):
			dst_zip = os.path.join(local_tg_dir, "0.zip")
			try:
				shutil.copy2(OUT_ZIP, dst_zip)
				if max_when > 0:
					set_file_dates(dst_zip, max_when)
				print(f"📋 Скопійовано 0.zip у {local_tg_dir}")
			except Exception as e:
				print(f"⚠️ Не вдалося скопіювати 0.zip у {local_tg_dir}: {e}")
		
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
