# -*- coding: utf-8 -*-

import asyncio
import calendar
import json
import os
import random
import re
import shutil
import sqlite3
import sys
import time
import typing
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient, events, functions, sync, types, utils

if os.name == 'nt':
	import win32api

sessdb = 'tl-ub' # назва бази сесії telethon
default_directory = ''		# "робоча папка" бота
MAINchatID = -1002236064671 # основний+резервний
CONFIG_PATH = "conf.json"	# main config file
chts_file = "chts.json"		# чати де дови+"чіти"+.send
dovs_file = "dovs.json"		# "дови" ("ДОВірені юзерИ")
mlab_file = "mlab.json"		# параметри моєї лаби (квала та макс. патогенів)
bio_0_url = "https://misc.pp.ua/files/0.zip" # <--- пряме посилання на 0.zip
inviteURL = "https://t.me/+kIo5ZwN0XesyMGEy" # <--- пряме посилання на ch_id
is_termux = os.environ.get('TERMUX_APP__PACKAGE_NAME') or os.environ.get('TERMUX_APK_RELEASE')

termux_api = False # там нижче буде перевизначено якщо is_termux == True

if is_termux:
	import sys
	print('Termux detected, checking permissions...')
	termux_api = os.system('termux-api-start') == 0 #	штука для сповіщеннь.
	if (os.environ.get('TERMUX_APP__APK_RELEASE') or os.environ.get('TERMUX_APK_RELEASE')) not in ('F_DROID', 'GITHUB'):
		print('You use not f-droid/github apk release, it may have problems...')
		print('F-droid termux release here: https://f-droid.org/packages/com.termux/')
		print('Github termux release here: https://github.com/termux/termux-app/releases')
	if float((os.environ.get('TERMUX_VERSION') or '0.119')[:5]) < 0.118:
		print('You use old version of termux, highly recommended that you update to v0.119.0 or higher ASAP')
	if termux_api:
		print('✅ termux API work')
	if os.access('/sdcard', os.W_OK):
		print('✅ дозвіл на запис')
		default_directory = '/sdcard/ub4tg'
		os.makedirs(default_directory, exist_ok=True)
		CONFIG_PATH = f'{default_directory}/conf.json'
	else:
		print('permission denied to write on internal storage')
		print('trying get permission...')
		os.system('termux-setup-storage')
		print('Restart termux [Press CTRL+D or command "exit"]')
		sys.exit(0)

config = {}

def save_config():
	ordered_config = {
		'api_id': int(config.get('api_id', 0)),
		'api_hash': str(config.get('api_hash', '')),
		'inviteURL': str(config.get('inviteURL') or inviteURL).strip(),
		'db_sqlite3': bool(config.get('db_sqlite3', True)),
		'db_pymysql': bool(config.get('db_pymysql', False)),
		'mysql': config.get('mysql') if isinstance(config.get('mysql'), dict) else {
			'host': 'localhost',
			'user': 'root',
			'password': 'V3rY$tR0NgPaS$Sw0Rd',
			'db': 'db'
		},
		'ch_id': int(config.get('ch_id', MAINchatID)),
		'wakelock': bool(config.get('wakelock', False)),
		'farm': bool(config.get('farm', True)),
		'mine': bool(config.get('mine', True))
	}
	# Дописуємо в кінець усі інші ключі, які вже були в конфігу (старі або кастомні)
	for k, v in config.items():
		if k not in ordered_config:
			ordered_config[k] = v
	with open(CONFIG_PATH, "w", encoding="utf-8") as write_file:
		json.dump(ordered_config, write_file, ensure_ascii=False, indent='\t')

if not os.path.exists(CONFIG_PATH):
	with open(CONFIG_PATH, "w", encoding="utf-8") as write_file:
		json.dump({
			"api_id": 123456,
			"api_hash": "your_api_hash",
			"inviteURL": inviteURL,
			"db_pymysql": False,
			"mysql": {
				"host": "localhost",
				"user": "root",
				"password": "V3rY$tR0NgPaS$Sw0Rd",
				"db": "db"
			},
			"ch_id": MAINchatID
		}, write_file, ensure_ascii=False, indent='\t')

with open(CONFIG_PATH, "r", encoding="utf-8") as configfile:
	#from types import SimpleNamespace
	config = json.load(configfile)
	print('✅ config loaded')

api_id = int(config['api_id'])
api_hash = config['api_hash']
ch_id = int(config.get('ch_id') or 0)
if ch_id > 0:
	ch_id = 0
	print('неправильний id чата')

db_sqlite3 = True
db_pymysql = bool(config.get('db_pymysql', False))
mysql_conf = config.get('mysql') if isinstance(config.get('mysql'), dict) else {
	'host': 'localhost',
	'user': 'root',
	'password': 'V3rY$tR0NgPaS$Sw0Rd',
	'db': 'db'
}
config['mysql'] = mysql_conf

farm = bool(config.get('farm', True))
mine = bool(config.get('mine', True))
f_run = False
m_run = False
bf_run = False
scn_run = False
need_restart = False
last_bz_time=0	# Коли дивились "бж"
ostalos_pt= 10	# поточні патогени (на старті припускаємо 10)
max_pt = 10     # макс. запас патогенів (оновиться з лаби)
kvala = 1       # рівень кваліфікації 1..60 (оновиться з лаби)
letal = 1       # рівень летальності = дні	(оновиться з лаби)
pt_time = int(time.time()) # час останньої фіксації патогенів
fever_until = 0 # timestamp закінчення гарячки (0 = здоровий)

save_config() # Вирівнює порядок ключів у файлі та прибирає зайве

################################################################################

irises = [707693258,5137994780,5226378684,5434504334,5443619563,8611067852]

################################################################################

chts = []
if ch_id < 0:
	chts.append(ch_id)
try:
	with open(chts_file, "r", encoding="utf-8") as read_file:
		chts = json.load(read_file)
except Exception:
	with open(chts_file, "w", encoding="utf-8") as write_file:
		json.dump(chts, write_file, ensure_ascii=False, indent='\t')

dovs = []
try:
	with open(dovs_file, "r", encoding="utf-8") as read_file:
		dovs = json.load(read_file)
except Exception:
	with open(dovs_file, "w", encoding="utf-8") as write_file:
		json.dump(dovs, write_file, ensure_ascii=False, indent='\t')

mlab = {"kvala": 1, "max_pt": 10, "letal": 1}
try:
	with open(mlab_file, "r", encoding="utf-8") as read_file:
		loaded_mlab = json.load(read_file)
		if isinstance(loaded_mlab, dict):
			kvala = max(1, min(60, int(loaded_mlab.get("kvala", 1))))
			max_pt = max(1, int(loaded_mlab.get("max_pt", 10)))
			letal = max(1, int(loaded_mlab.get("letal", 1)))
			ostalos_pt = max_pt
			mlab.update({"kvala": kvala, "max_pt": max_pt, "letal": letal})
except Exception:
	with open(mlab_file, "w", encoding="utf-8") as write_file:
		json.dump(mlab, write_file, ensure_ascii=False, indent='\t')

def save_mlab(updates: dict):
	if not updates:
		return
	try:
		current = {}
		if os.path.exists(mlab_file):
			with open(mlab_file, "r", encoding="utf-8") as read_file:
				data = json.load(read_file)
				if isinstance(data, dict):
					current = data
		current.update(updates)
		with open(mlab_file, "w", encoding="utf-8") as write_file:
			json.dump(current, write_file, ensure_ascii=False, indent='\t')
	except Exception as e:
		print(f'⚠️ Помилка збереження {mlab_file}: {e}')
################################################################################

async def main():
	global db_pymysql, ch_id, mine
	async with TelegramClient(sessdb, api_id, api_hash, timeout=300) as client:
		client.parse_mode="HTML"
		print('User-Bot started')
		me = await client.get_me()
		my_id = int(me.id)
		my_uz = me.username
		print(f'🆔 {my_id}')

		if os.name == 'nt':
			win32api.SetConsoleTitle(f'{my_id}')
		elif os.name == 'posix':
			print(f'\33]0;{my_id}\a', end='', flush=True)

		if is_termux and config.get("wakelock"):
			print('Prevent killing termux by android, getting wakelock...')
			os.system('termux-wake-lock')
			print('This can cause battery drain!')

		if ch_id == 0:
			ch_id = MAINchatID
			config['ch_id'] = ch_id
			save_config()
		
		def is_allowed_chat(event) -> bool:
			if event.is_private:
				return event.chat_id not in irises and event.chat_id not in (6333102398, 1124824021)
			return event.chat_id in (ch_id, MAINchatID)
		
		bio_bot_username = '@bio_attacker_bot'
		restart_timestamp = 1794601985 # 13.11.2026 20:33:05 UTC
		
		try:
			bio_bot = await client.get_entity(bio_bot_username)
			bio_attacker_bot_ID = int(bio_bot.id)
			# Перевіряємо, чи є вже повідомлення в ЛС із ботом
			msgs = await client.get_messages(bio_bot, limit=1)
			if not msgs:
				await client.send_message(bio_bot, '/start')
				print(f'👋 ЛС було порожнім — надіслано /start для {bio_bot_username}')
		except Exception as e:
			print(f'❌ Не вдалося знайти {bio_bot_username}: {e}')
			bio_attacker_bot_ID = 6333102398 # резервний ID
		
		if db_pymysql:
			try:
				import pymysql
				import pymysql.cursors
			except ImportError:
				print('❌ Бібліотека pymysql не встановлена. Вимикаю MySQL...')
				db_pymysql = False
				config['db_pymysql'] = False
				save_config()

		if db_pymysql:
			while True:
				try:
					con = pymysql.connect(
						host=str(mysql_conf.get('host', 'localhost')),
						user=str(mysql_conf.get('user', 'root')),
						password=str(mysql_conf.get('password', '')),
						db=str(mysql_conf.get('db', 'db')),
						charset='utf8mb4',
						autocommit=False,
						cursorclass=pymysql.cursors.DictCursor
					)
					d = con.cursor()
					print('✅ Підключено до MySQL')
					save_config()
					break
				except pymysql.err.OperationalError as e:
					err_code = e.args[0] if e.args else 0
					if err_code == 1045:
						print(f'⚠️ Невірний пароль для MySQL ({mysql_conf.get("user")}@{mysql_conf.get("host")}).')
						new_pass = input('Введіть правильний пароль (або натисніть Enter, щоб вимкнути MySQL): ').strip()
						if new_pass:
							mysql_conf['password'] = new_pass
							continue
					print(f'❌ MySQL вимкнено в конфігу (код {err_code}): {e}')
					db_pymysql = False
					config['db_pymysql'] = False
					save_config()
					break
				except Exception as e:
					print(f'❌ Невідома помилка MySQL: {e}')
					db_pymysql = False
					config['db_pymysql'] = False
					save_config()
					break

		if db_pymysql:
			d.execute('''CREATE TABLE IF NOT EXISTS `tg_bot_users` (
			`user_id` bigint(20) UNSIGNED NOT NULL DEFAULT '0',
			`reg_int` int(11) UNSIGNED NOT NULL DEFAULT '0',
			`f_name` text CHARACTER SET utf8mb4 NOT NULL DEFAULT '',
			`f_time` int(11) UNSIGNED NOT NULL DEFAULT '0',
			`m_time` int(11) UNSIGNED NOT NULL DEFAULT '0',
			PRIMARY KEY (`user_id`)
			);''');
			con.commit()
			# Таблиця атак (Тільки для СВОЇХ аків завдяки прапорцю `м`)
			d.execute('''CREATE TABLE IF NOT EXISTS `tg_bio_attack` (
			`date` int(11) unsigned NOT NULL DEFAULT '0',
			`who_id` bigint(20) unsigned NOT NULL DEFAULT '0',
			`user_id` bigint(20) unsigned NOT NULL DEFAULT '0',
			`profit` int(11) unsigned NOT NULL DEFAULT '0',
			`until_int` int(11) unsigned NOT NULL DEFAULT '0',
			`until_str` varchar(11) NOT NULL DEFAULT '0',
			UNIQUE KEY `UNIQUE` (`who_id`,`user_id`)
			);''');
			con.commit()
			# Оновлена таблиця користувачів БЕЗ virus,з полем коли (when_int)
			d.execute('''CREATE TABLE IF NOT EXISTS `tg_bio_users` (
			`user_id` bigint(20) unsigned NOT NULL DEFAULT '0',
			`when_int` int(11) unsigned NOT NULL DEFAULT '0',
			`profit` int(11) unsigned NOT NULL DEFAULT '0',
			UNIQUE KEY `user_id` (`user_id`)
			);''');
			con.commit()
			d.execute('''CREATE TABLE IF NOT EXISTS `tg_users_url` (
			`user_id` bigint(20) unsigned NOT NULL DEFAULT '0',
			`when_int` int(11) unsigned NOT NULL DEFAULT '0',
			`u_link` varchar(64) NOT NULL DEFAULT '',
			`f_name` text NOT NULL,
			PRIMARY KEY (`user_id`)
			);''');
			con.commit()
			try:
				d.execute('''INSERT INTO `tg_bot_users` 
				(`user_id`, `reg_int`, `f_name`) 
				VALUES (%s,%s,%s) 
				ON DUPLICATE KEY UPDATE 
				f_name=VALUES(f_name);''',
				(int(my_id),int(time.time()),str(me.first_name))); con.commit()
			except Exception as e:
				print(f'⚠️ Помилка запису в tg_bot_users: {e}')
			
			#restart_timestamp = 1794601985 # 13.11.2026 (перезапуск)
			
			# Зачистка старих записів у MySQL (крім tg_bot_users)
			d.execute('DELETE FROM `tg_bio_attack` WHERE `date` < %s', (restart_timestamp,))
			del_attack = d.rowcount
			
			d.execute('DELETE FROM `tg_bio_users` WHERE `when_int` < %s', (restart_timestamp,))
			del_users = d.rowcount
			
			d.execute('DELETE FROM `tg_users_url` WHERE `when_int` < %s', (restart_timestamp,))
			del_urls = d.rowcount
			
			d.execute('UPDATE `tg_bio_users` SET `profit`=0 WHERE `profit`=1')
			d.execute('DELETE FROM `tg_bio_attack` WHERE `user_id` < 100')
			d.execute('DELETE FROM `tg_bio_users` WHERE `user_id` < 100')
			
			con.commit()
			
			if del_attack or del_users or del_urls:
				print(f'🧹 MySQL очищено від старих записів (до {restart_timestamp}): атаки={del_attack}, юзери={del_users}, лінки={del_urls}')
		
		if db_sqlite3:
			sqlite_path = f"{my_id}.sqlite" # покласти базу рядом (перевизначимо)?
			
			if os.name == 'nt' and os.path.exists(r"D:\Misc\projects\Python"):
				sqlite_path = rf"D:\Misc\projects\Python\{my_id}.sqlite"
			elif is_termux:
				sqlite_path = f"{default_directory}/{my_id}.sqlite"
			
			conn = sqlite3.connect(sqlite_path)
			c = conn.cursor()
			
			c.execute('''CREATE TABLE IF NOT EXISTS avocado (
			user_id	INTEGER NOT NULL DEFAULT 0 UNIQUE,
			when_int	INTEGER NOT NULL DEFAULT 0,
			bio_int	INTEGER NOT NULL DEFAULT 0,
			expr_int	INTEGER NOT NULL DEFAULT 0,
			expr_str	VARCHAR NOT NULL DEFAULT 0
			)''');
			conn.commit()
			
			c.execute("""UPDATE avocado SET bio_int = 0 WHERE bio_int = 1 
			AND expr_int < %d""" % int(time.time()))
			conn.commit()
			
			# Зачистка старих записів та сміттєвих ID у SQLite
			c.execute('DELETE FROM avocado WHERE when_int < ? OR user_id<100', 
			(restart_timestamp,))
			del_sqlite = c.rowcount
			conn.commit()
			
			if del_sqlite > 0:
				print(
					f"🧹 SQLite (avocado): видалено {del_sqlite} записів.\n"
					"🗜️ Стискаю базу (VACUUM)..."
				)
				c.execute('VACUUM')
				conn.commit()
			
			# https://www.sqlite.org/pragma.html
			c.execute('PRAGMA optimize=0x10002')
			conn.commit()
			
			def optimize():
				try:
					c.execute('PRAGMA optimize')
					conn.commit()
				except Exception as e:
					print(f"err optimize: {e}")
			
			####################################################################
		
		########################################################################
		
		async def id_dov(u:int):
			if u==0 or u==my_id:
				return u
			global dovs
			try:
				dovs_file = "dovs.json"		# дови:
				with open(dovs_file, "r") as read_file:
					dovs = json.load(read_file)
			except Exception as wtf:
				#print(wtf)	# print
				pass
			if u in dovs:
				return u
			return False
		
		########################################################################
		
		async def sft(u: int = my_id, д: int=0):
			if д == 0:
				д = int(time.time())
			if db_pymysql:
				try:
					q="UPDATE tg_bot_users SET f_time = %s WHERE user_id = %s"
					await asyncio.sleep(random.uniform(1,2))
					d.execute(q,(f'{д}',u));con.commit()
				except Exception as Err:
					print(f'E:{Err} #sft')
				
			return
		
		async def smt(u: int = my_id, д: int=0):
			if д == 0:
				д = int(time.time())
			if db_pymysql:
				try:
					q="UPDATE tg_bot_users SET m_time = %s WHERE user_id = %s"
					await asyncio.sleep(random.uniform(1,2))
					d.execute(q,(f'{д}',u));con.commit()
				except Exception as Err:
					print(f'E:{Err} #smt')
				
			return
		
		########################################################################
		
		def get_pt() -> int:
			global ostalos_pt, pt_time
			now = int(time.time())
			if ostalos_pt >= max_pt:
				pt_time = now
				return ostalos_pt
			
			step_sec = max(60, (61 - kvala) * 60) # 1 лвл = 3600с, 60 лвл = 60с
			elapsed = now - pt_time
			if elapsed >= step_sec:
				regen = elapsed // step_sec
				ostalos_pt = min(max_pt, ostalos_pt + regen)
				if ostalos_pt >= max_pt:
					pt_time = now
				else:
					pt_time += regen * step_sec
			return ostalos_pt
		
		########################################################################
		
		async def message_q( # спизжено
				text: str,
				user_id: int,
				mark_read: bool = False,
				delete: bool = False,
		):
				"""Отправляет сообщение и возращает ответ"""
				async with client.conversation(user_id, exclusive=False) as conv:
						msg = await conv.send_message(text)
						response = await conv.get_response()
						if mark_read:
								await conv.mark_read()
						if delete:
								await msg.delete()
								#await response.delete()
						return response
		
		########################################################################
		
		async def реанимировать_жабу(chat: int):
			if chat>=0:
				return
			r=await message_q(
					text='Реанимировать жабу',
					user_id=chat,
					mark_read=True,
					delete=False)
			if r.text:
					t = r.raw_text
					if 'У тебя нет аптечек для реанимации жабы!' in t:
						if termux_api:
							os.system(
								f"termux-notification --title '{my_id}' --content '{t}'"
								)
						print(t)
						return 0
					Осталось= re.findall(r'Осталось аптечек: ([0-9]{1,})',t)
					if Осталось:
						print(t)
						Осталось=int(Осталось[0])
						if Осталось==0:
							return True # Принаймні реанімували хоча не осталось
						return Осталось # int
					if 'Твоя жаба жива' in t:
						return True # ok?
			return False
		
		########################################################################
		
		async def Mining(w: float = 0.9973):
			global m_run,mine
			if m_run:
				return
			m_run = True
			try:
				if int(w)>1:
					print(f'⏳ wait {w}')
				await asyncio.sleep(w)
				while mine:
					try:
						д = int(time.time())
						w = float(0.7777777)
						m = await message_q(
						text='/Mine',
						user_id=6333102398,
						mark_read=True,
						delete=False)
						if m.text:
							t = m.raw_text
							if m.date:
								д = int(datetime.timestamp(m.date))
							if ('not been created' in t
							or '🔒 Feature locked' in t
							or 'ещё не создана' in t):
								mine = False # force stop
								break # припинити виконання
							print(t) # показать в консолі текст відповіді
							if 'Successful mining' in t or 'Удачная попытка' in t:
								w = random.uniform(7200.0072,7227.7227)
								if db_pymysql:
									await smt(my_id, д)
							elif '👎🏻💔 No luck!' in t or '👎🏻💔 Неудача!' in t:
								w = random.uniform(2.5, 7.5) # невеликий запас
								H = re.findall(r'(\d+)\s*(?:h|ч)', t)
								M = re.findall(r'(\d{1,2})\s*(?:min|мин)', t)
								if H:
									w += int(H[0]) * 3600
								if M:
									w += int(M[0]) * 60
							else:
								# Якщо був якийсь інший??
								print(f'відповідь "{t}" не розпізнана')
								w = random.uniform(9,999)
						else:
							# Вобще нема ніякого текста
							w = random.uniform(111,999)
						print(f'⏳ wait {w}')
						await asyncio.sleep(w)
					except Exception as e:
						w = random.uniform(66,99) # random wait
						print(f"⚠️ Помилка під час майнінгу: {e}. Повтор через {w} сек...")
						await asyncio.sleep(w)  # Пауза перед наступною спробою, щоб не спамити
			finally:
				m_run = False  # навіть якщо станеться помилка чи break
		
		########################################################################
		
		async def ферма():
			global f_run
			if ch_id==0:
				return
			kuda=ch_id
			if f_run:
				return
			while config.get("farm"):
				f_run = True #	✅ погнали!
				w = random.uniform(1,14401)
				д = int(time.time())
				try:
					f = await message_q(
						text='Ферма',
						user_id=kuda,
						mark_read=True,
						delete=True)
				except asyncio.TimeoutError:
					w = random.uniform(300, 600)
					print(f'⚠️ Таймаут відповіді на Ферму. Повтор через {int(w)} сек...')
					await asyncio.sleep(w)
					continue
				except Exception as e:
					w = random.uniform(60, 180)
					print(f'⚠️ Помилка у Фермі: {e}. Повтор через {int(w)} сек...')
					await asyncio.sleep(w)
					continue
				s = f.sender_id
				if f.date:
					д = int(datetime.timestamp(f.date))
				if f.text:
					t = f.raw_text
				if s in irises:
					if '✅' in t or '🔑' in t:
						u = int(0)
						if f.entities:
							h= utils.sanitize_parse_mode('html').unparse(t,f.entities)
							r= re.findall(r'<a href="tg://user\?id=([0-9]+)">.+</a>',h)
							if r:
								u=int(r[0])
								if u==my_id:
									w=14401
									print(t)
									if db_pymysql:
										await sft(u,д)
					if 'Наступний прибуток через' in t:
						г= re.findall(r'([0-9]) годин.*',t)
						х= re.findall(r'([0-9]{1,2}) хв.*',t)
						с= re.findall(r'([0-9]{1,2}) сек.*',t)
						w= int(random.uniform(1,9)) # int(rnd)
						if г:
							г =int(г[0][0])
							w+=int(г *3600)
						if х:
							х = int(х[0])
							w+=int(х *60)
						if с:
							w+=int(с[0])
						try:
							await asyncio.sleep(random.uniform(2,4))
							await client.delete_messages(kuda,f.id)					
						except:
							pass
					if int(w)>0:
						w=int(w)
				print(f'⏳ wait {w}')
				await asyncio.sleep(w)
		
		########################################################################
		
		@client.on(events.NewMessage(incoming=True,from_users=irises,
		pattern=r'(✅|🔑) (ВДАЛО|ЗАЧЁТ|УСПІХ)'))
		async def ферма_ВДАЛО(event):
			m = event.message
			t = m.raw_text
			u = 0 # OR id
			д = int(time.time())
			if m.date:
				д = int(datetime.timestamp(m.date))
			if m.entities:
				h= utils.sanitize_parse_mode('html').unparse(t,m.entities)
				r= re.findall(r'<a href="tg://user\?id=([0-9]+)">.+</a>',h)
				if r:
					u=int(r[0])
					if db_pymysql and u>0:
						await sft(u,д)
			if m_run:
				return
			else:
				await Mining(1) # Тупо врубаємо майн після успішної ферми
		
		########################################################################
		
		@client.on(events.NewMessage(incoming=True,from_users=6333102398,
		pattern=r'🎉 New laboratory level'))
		async def New_level(event):
			t = event.message.raw_text
			print(t) # показать в консолі
			if '⛏️ Mining' in t:
				await Mining(1)
		
		@client.on(events.NewMessage(incoming=True,from_users=6333102398,
		pattern=r'👍🏻❤️ (Successful mining attempt|Удачная попытка майнинга)!'))
		async def Mine_ok(event):
			m = event.message
			if db_pymysql and m.date:
				await smt(my_id, int(datetime.timestamp(m.date)))
			if m_run:
				return
			else:
				#print(m.raw_text)
				await Mining(random.uniform(7200.0072,7227.7227))
		
		########################################################################
		
		Active_victims = r'.*(Active\s+victims|Активные\s+жертвы)'
		#import calendar # можна перенести на самий верх файлу до інших імпортів
		@client.on(events.NewMessage(incoming=True, pattern=Active_victims))
		@client.on(events.MessageEdited(incoming=True, pattern=Active_victims))
		async def ActiveVictims(event):
			m = event.message
			t = m.raw_text
			if m.fwd_from:
				s = m.fwd_from.from_id.user_id if isinstance(m.fwd_from.from_id, 
				types.PeerUser) else None
				msg_date = m.fwd_from.date
			else:
				s = m.sender_id
				msg_date = m.date
			
			if s != 6333102398 or int(msg_date.timestamp()) < restart_timestamp or not m.entities:
				return
			
			д = int(msg_date.timestamp())
			м = event.is_private and not m.fwd_from
			h = utils.sanitize_parse_mode('html').unparse(t, m.entities)
			
			if м:
				# Свій список у ЛС бота — парсимо точне біо та час антилу
				pattern = re.compile(
					r'href="(?:tg://openmessage\?user_id=|https?://t\.me/)(\d+)"[^>]*>[^<]+</a>'
					r'\s*.—\s*(?:<strong>)?(\d+)(?:</strong>)?\s*🧬\s*(?:until|до)\s+'
					r'(?:<code>)?(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})\s+UTC(?:</code>)?',
					re.IGNORECASE
				)
				for r in pattern.finditer(h):
					user_id = int(r.group(1))
					if user_id < 100:
						continue
					bio = int(r.group(2))
					date_str = r.group(3)
					until_str = date_str.split(" ")[0]
					dt = datetime.strptime(date_str, "%d.%m.%Y %H:%M")
					until_ts = int(calendar.timegm(dt.timetuple()))
					
					if until_ts < int(time.time()):
						until_ts = 0 # пишемо як не інфікованого
						until_str = "0"
					
					if db_sqlite3:
						try:
							c.execute("""INSERT INTO avocado 
							(user_id, when_int, bio_int, expr_int, expr_str)
							VALUES (?, ?, ?, ?, ?)
							ON CONFLICT(user_id) DO UPDATE SET
								when_int = excluded.when_int,
								bio_int = excluded.bio_int,
								expr_int = excluded.expr_int,
								expr_str = excluded.expr_str
							WHERE excluded.expr_int > avocado.expr_int 
							OR (avocado.expr_int = 0 AND excluded.when_int > avocado.when_int)""",
							(user_id, д, bio, until_ts, until_str))
						except Exception as Err:
							print(f'err: {Err} avocado')
					
					if db_pymysql:
						try:
							d.execute("""INSERT INTO `tg_bio_attack` 
							(`date`, `who_id`, `user_id`, `profit`, `until_int`, `until_str`) 
							VALUES (%s, %s, %s, %s, %s, %s)
							ON DUPLICATE KEY UPDATE 
								date = IF(VALUES(until_int) > until_int OR (until_int = 0 AND VALUES(date) > date), VALUES(date), date),
								profit = IF(VALUES(until_int) > until_int OR (until_int = 0 AND VALUES(date) > date), VALUES(profit), profit),
								until_str = IF(VALUES(until_int) > until_int OR (until_int = 0 AND VALUES(date) > date), VALUES(until_str), until_str),
								until_int = IF(VALUES(until_int) > until_int OR (until_int = 0 AND VALUES(date) > date), VALUES(until_int), until_int)""",
							(д, my_id, user_id, bio, until_ts, until_str))
							
							d.execute("""INSERT INTO `tg_bio_users` 
							(`user_id`, `when_int`, `profit`) 
							VALUES (%s, %s, %s) 
							ON DUPLICATE KEY UPDATE 
								profit = IF(VALUES(when_int) > when_int, VALUES(profit), profit),
								when_int = IF(VALUES(when_int) > when_int, VALUES(when_int), when_int)""",
							(user_id, д, bio))
						except Exception as Err:
							print(f'err: {Err} mysql my')
					
					print(f'@{user_id} +{bio} {until_ts} {until_str}')
			else:
				# Чужий список (група або переслане) — пишемо тільки нові ID як одинички
				raw_ids = re.findall(r'href="(?:tg://(?:openmessage\?user_id=|user\?id=)|https?://t\.me/)(\d+)"', h, re.IGNORECASE)
				for uid_str in set(raw_ids):
					user_id = int(uid_str)
					if user_id < 100 or user_id in (my_id, 6333102398, 1124824021):
						continue
					if db_sqlite3:
						try:
							c.execute("""INSERT OR IGNORE INTO avocado 
							(user_id, when_int, bio_int, expr_int, expr_str) 
							VALUES (?, ?, 0, 0, '0')""", (user_id, д))
						except Exception:
							pass
					if db_pymysql:
						try:
							d.execute("""INSERT IGNORE INTO `tg_bio_users` 
							(`user_id`, `when_int`, `profit`) 
							VALUES (%s, %s, 0)""",(user_id,д))
						except Exception:
							pass
			
			if db_sqlite3:
				try:
					conn.commit()
					optimize()
				except Exception as e:
					print(f"err final commit/optimize: {e}")
			
			if db_pymysql:
				try:
					con.commit()
				except Exception as e:
					print(f"err mysql final commit: {e}")
		
		########################################################################
		
		infect_verbs = (
			r'(?:infected|заразил[ао]?|подверг(?:ла|ся)?|йобнув|сикди|'
			r'насрал[ао]?|выебал[ао]?|атаковал[ао]?|инфицировал[ао]?|'
			r'напугал[ао]?|нокаутировал[ао]?|обманул[ао]?|оглушил[ао]?|'
			r'поставил[ао]?|рассмешил[ао]?|угостил[ао]?)'
		)
		skip_router_re = (
			r'(?s).*(?:Active\s+victims|Активные\s+жертвы|'
			r'🧪\s*(?:Pathogens|Свободных патогенов)|'
			r'👩🏻‍🔬\s*(?:Qualification|Квалификация))'
		)
		
		@client.on(events.NewMessage(incoming=True, from_users=6333102398))
		async def infect_router(event):
			global last_bz_time, ostalos_pt, pt_time, letal
			m = event.message
			when = int(m.date.timestamp())
			if when < restart_timestamp or not m.entities:
				return
			
			t = m.raw_text
			if re.search(skip_router_re, t, re.IGNORECASE):
				return
			
			h = utils.sanitize_parse_mode('html').unparse(t, m.entities)
			raw_ids = re.findall(r'tg://openmessage\?user_id=(\d+)', h)
			if not raw_ids:
				return
			
			ids = [
				int(x) for x in raw_ids
				if int(x) >= 100 and int(x) not in (6333102398, 1124824021)
			]
			if not ids:
				return
			
			is_pm = bool(event.is_private and not m.fwd_from)
			is_infect_msg = bool(re.search(infect_verbs, t, re.IGNORECASE))
			
			def parse_details(html_txt: str, plain_txt: str):
				p_bio = None
				p_days = None
				p_rem = None
				p_vir = ''
				try:
					bm = re.search(
						r'(?:Profit|Прибыль|Bio-experience gained|'
						r'верир|потери|приносит|корма):\s*'
						r'(?:<strong>)?\+?([\d\.,]+k?)(?:</strong>)?',
						html_txt, re.IGNORECASE
					)
					if bm:
						rb = bm.group(1).replace(',', '.')
						if rb.lower().endswith('k'):
							val = int(float(rb[:-1]) * 1000)
						else:
							val = int(float(rb))
						if val >= 1:
							p_bio = val
				except Exception:
					pass
				
				try:
					dm = re.search(
						r'(?:Infection duration|Длительность заражения|'
						r'на|for|ещё)\s*:?\s*(\d{1,3})\s*(?:d|д)',
						plain_txt, re.IGNORECASE
					)
					if dm:
						d_val = int(dm.group(1))
						if 1 <= d_val <= 365:
							p_days = d_val
				except Exception:
					pass
				
				try:
					rm = re.search(
						r'(?:Left|Осталось|Pathogens remaining|'
						r'Remaining):\s*(?:<strong>)?(\d+)(?:</strong>)?',
						html_txt, re.IGNORECASE
					)
					if rm:
						r_val = int(rm.group(1))
						if 0 <= r_val <= 500:
							p_rem = r_val
				except Exception:
					pass
				
				try:
					vm = re.search(r'[«“"]([^»”"\n]{2,40})[»”"]', plain_txt)
					if vm:
						p_vir = vm.group(1).strip()
				except Exception:
					pass
				
				return p_bio, p_days, p_rem, p_vir
			
			def save_unknown_victim(uid: int):
				if uid == my_id or uid < 100:
					return
				if db_sqlite3:
					try:
						c.execute(
							"""INSERT OR IGNORE INTO avocado
							(user_id, when_int, bio_int, expr_int, expr_str)
							VALUES (?, ?, 1, 0, '0')""",
							(uid, when)
						)
					except Exception:
						pass
				if db_pymysql:
					try:
						d.execute(
							"""INSERT IGNORE INTO `tg_bio_users`
							(`user_id`, `when_int`, `profit`)
							VALUES (%s, %s, 1)""",
							(uid, when)
						)
					except Exception:
						pass
			
			# ================================================================
			# ВАРІАНТ А: 2 і більше ID (нападник + жертва)
			# ================================================================
			if len(ids) >= 2:
				u1id = ids
				u2id = ids
				
				if not is_infect_msg:
					save_unknown_victim(u1id)
					save_unknown_victim(u2id)
					if db_sqlite3:
						conn.commit()
					if db_pymysql:
						con.commit()
					return
				
				if u2id == my_id and u1id != my_id:
					save_unknown_victim(u1id)
					if db_sqlite3:
						conn.commit()
					if db_pymysql:
						con.commit()
					print(f'➕ Мене заразив @{u1id} — додано в базу.')
					return
				
				if u1id == my_id:
					p_bio, p_days, p_rem, p_vir = parse_details(h, t)
					bio = p_bio if p_bio is not None else 1
					if p_days is not None:
						days = p_days
					else:
						days = letal if letal > 0 else 1
					if p_days and p_days > letal:
						letal = p_days
						save_mlab({"letal": letal})
					
					until_ts = when + (days * 86400)
					until_str = datetime.fromtimestamp(
						until_ts, tz=timezone.utc
					).strftime("%d.%m.%Y")
					
					need_bz = False
					if p_rem is not None:
						ostalos_pt = p_rem
						pt_time = when
						if ostalos_pt in (0, 1):
							need_bz = True
					
					if db_sqlite3:
						try:
							c.execute(
								"""INSERT INTO avocado
								(user_id, when_int, bio_int,
								expr_int, expr_str)
								VALUES (?, ?, ?, ?, ?)
								ON CONFLICT(user_id) DO UPDATE SET
									when_int = excluded.when_int,
									bio_int = excluded.bio_int,
									expr_int = excluded.expr_int,
									expr_str = excluded.expr_str
								WHERE excluded.when_int >= avocado.when_int""",
								(u2id, when, bio, until_ts, until_str)
							)
							conn.commit()
						except Exception as e:
							print(f'err: {e} (infect sqlite my)')
					
					if db_pymysql:
						try:
							d.execute(
								"""INSERT INTO `tg_bio_attack`
								(`date`, `who_id`, `user_id`, `profit`,
								`until_int`, `until_str`)
								VALUES (%s, %s, %s, %s, %s, %s)
								ON DUPLICATE KEY UPDATE
									date = IF(VALUES(date) >= date,
										VALUES(date), date),
									profit = IF(VALUES(date) >= date,
										VALUES(profit), profit),
									until_int = IF(VALUES(date) >= date,
										VALUES(until_int), until_int),
									until_str = IF(VALUES(date) >= date,
										VALUES(until_str), until_str)""",
								(when, my_id, u2id, bio, until_ts, until_str)
							)
							d.execute(
								"""INSERT INTO `tg_bio_users`
								(`user_id`, `when_int`, `profit`)
								VALUES (%s, %s, %s)
								ON DUPLICATE KEY UPDATE
									profit = IF(VALUES(when_int) >= when_int,
										VALUES(profit), profit),
									when_int = IF(VALUES(when_int) >= when_int,
										VALUES(when_int), when_int)""",
								(u2id, when, bio)
							)
							con.commit()
						except Exception as e:
							print(f'err: {e} (infect mysql my)')
					
					print(
						f'☣️ Заражено @{u2id} (+{bio}, {days}д) | '
						f'Патів: {ostalos_pt}/{max_pt}'
					)
					if need_bz and (time.time() - last_bz_time > 15):
						last_bz_time = time.time()
						await asyncio.sleep(random.uniform(1.5, 3.5))
						await client.send_message(6333102398, '/бж')
				else:
					save_unknown_victim(u1id)
					save_unknown_victim(u2id)
					if db_sqlite3:
						conn.commit()
					if db_pymysql:
						con.commit()
				return
			
			# ================================================================
			# ВАРІАНТ Б: Рівно 1 ID (нападник зі сповіщення або невідомий формат)
			# ================================================================
			uid_single = ids
			if uid_single == my_id:
				return
			
			save_unknown_victim(uid_single)
			
			if is_pm:
				p_bio, p_days, p_rem, p_vir = parse_details(h, t)
				if any(x is not None for x in (p_bio, p_days, p_rem)):
					bio = p_bio if p_bio is not None else 1
					if p_days is not None:
						days = p_days
					else:
						days = letal if letal > 0 else 1
					until_ts = when + (days * 86400)
					until_str = datetime.fromtimestamp(
						until_ts, tz=timezone.utc
					).strftime("%d.%m.%Y")
					
					if p_rem is not None:
						ostalos_pt = p_rem
						pt_time = when
					
					if db_sqlite3:
						try:
							c.execute(
								"""INSERT INTO avocado
								(user_id, when_int, bio_int,
								expr_int, expr_str)
								VALUES (?, ?, ?, ?, ?)
								ON CONFLICT(user_id) DO UPDATE SET
									when_int = excluded.when_int,
									bio_int = excluded.bio_int,
									expr_int = excluded.expr_int,
									expr_str = excluded.expr_str
								WHERE excluded.when_int >= avocado.when_int""",
								(uid_single, when, bio, until_ts, until_str)
							)
						except Exception:
							pass
					if db_pymysql:
						try:
							d.execute(
								"""INSERT INTO `tg_bio_attack`
								(`date`, `who_id`, `user_id`, `profit`,
								`until_int`, `until_str`)
								VALUES (%s, %s, %s, %s, %s, %s)
								ON DUPLICATE KEY UPDATE
									date = IF(VALUES(date) >= date,
										VALUES(date), date),
									profit = IF(VALUES(date) >= date,
										VALUES(profit), profit),
									until_int = IF(VALUES(date) >= date,
										VALUES(until_int), until_int),
									until_str = IF(VALUES(date) >= date,
										VALUES(until_str), until_str)""",
								(when, my_id, uid_single, bio, until_ts, until_str)
							)
							d.execute(
								"""INSERT INTO `tg_bio_users`
								(`user_id`, `when_int`, `profit`)
								VALUES (%s, %s, %s)
								ON DUPLICATE KEY UPDATE
									profit = IF(VALUES(when_int) >= when_int,
										VALUES(profit), profit),
									when_int = IF(VALUES(when_int) >= when_int,
										VALUES(when_int), when_int)""",
								(uid_single, when, bio)
							)
						except Exception:
							pass
					print(
						f'☣️ [1-ID PM] Заражено @{uid_single} '
						f'(+{bio}, {days}д) | Патів: {ostalos_pt}/{max_pt}'
					)
				else:
					print(f'➕ Зібрано гравця @{uid_single} в базу.')
			
			if db_sqlite3:
				conn.commit()
			if db_pymysql:
				con.commit()
		
		@client.on(events.NewMessage(incoming=True, from_users=6333102398,
		pattern=r'(?s).*(?:Organizer|Организатор)'))
		
		async def collect_attacker(event):
			m = event.message
			when = int(m.date.timestamp())
			if when < restart_timestamp or not m.entities:
				return
			
			h = utils.sanitize_parse_mode('html').unparse(m.raw_text, m.entities)
			att_match = re.search(r'tg://openmessage\?user_id=(\d+)', h)
			if not att_match:
				return
			
			att_id = int(att_match.group(1))
			
			if db_sqlite3:
				try:
					c.execute("""INSERT OR IGNORE INTO avocado 
					(user_id, when_int, bio_int, expr_int, expr_str) 
					VALUES (?, ?, 0, 0, '0')""", (att_id, when))
					conn.commit()
				except Exception:
					pass
			if db_pymysql:
				try:
					d.execute("""INSERT IGNORE INTO `tg_bio_users` 
					(`user_id`, `when_int`, `profit`) VALUES (%s, %s, 0)""", 
					(att_id, when))
					con.commit()
				except Exception:
					pass
			print(f'➕ Зібрано нападника @{att_id} в базу.')
		
		bz_aliases = r'^(?:[\./!]{1,2})?(?:victims?|бж|жертвы|био(?:ежа|жертвы|доход|зараженные))(?:\s+\d+)?$'
		@client.on(events.NewMessage(outgoing=True, pattern=re.compile(bz_aliases, re.IGNORECASE)))
		async def cmd_bz_out(event):
			global last_bz_time
			if event.chat_id == 6333102398:
				last_bz_time = time.time()
		
		########################################################################
		
		lab_pattern = r'(?s).*(?:🧪\s*(?:Pathogens|Свободных патогенов)|👩🏻‍🔬\s*(?:Qualification|Квалификация)|☠️\s*(?:Mortality|Летальность)):'
		@client.on(events.NewMessage(incoming=True, pattern=lab_pattern))
		@client.on(events.MessageEdited(incoming=True, pattern=lab_pattern))
		async def parse_my_lab(event):
			global ostalos_pt, max_pt, kvala, letal, pt_time, fever_until
			m = event.message
			if m.fwd_from:
				s = m.fwd_from.from_id.user_id if isinstance(m.fwd_from.from_id, types.PeerUser) else None
				msg_ts = int(m.fwd_from.date.timestamp())
			else:
				s = m.sender_id
				msg_ts = int(m.date.timestamp())
			
			if s != 6333102398 or msg_ts < restart_timestamp or not m.entities:
				return
			
			h = utils.sanitize_parse_mode('html').unparse(m.raw_text,m.entities)
			ids = re.findall(r'tg://openmessage\?user_id=(\d+)', h)
			if not ids or int(ids[0]) != my_id:
				return
			
			t = m.raw_text
			pt_m = re.search(r'🧪\s*(?:Pathogens|Свободных патогенов):\s*(\d+)\s*/\s*(\d+)', t)
			kv_m = re.search(r'👩🏻‍🔬\s*(?:Qualification|Квалификация):\s*(\d+)', t)
			lt_m = re.search(r'☠️\s*(?:Mortality|Летальность):\s*(\d+)', t)
			nx_m = re.search(r'⏳\s*(?:Next pathogen in|Следующий патоген через)\s*(\d+)\s*(?:min|мин)', t)
			fv_m = re.search(r'🌡\s*(?:You have a fever\. Time left:|У тебя горячка\. Осталось)\s*(\d+)\s*(?:min|мин)', t)
			fv_less = re.search(r'🌡.*(?:less than a minute|меньше минуты)', t, re.IGNORECASE)
			
			updates = {}
			
			if kv_m:
				kvala = max(1, min(60, int(kv_m.group(1))))
				updates["kvala"] = kvala
			
			if lt_m:
				letal = max(1, int(lt_m.group(1)))
				updates["letal"] = letal
			
			if pt_m:
				ostalos_pt = int(pt_m.group(1))
				max_pt = int(pt_m.group(2))
				updates["max_pt"] = max_pt
				
				step_sec = max(60, (61 - kvala) * 60)
				if nx_m and ostalos_pt < max_pt:
					mins_left = int(nx_m.group(1))
					pt_time = msg_ts - max(0, step_sec - mins_left * 60)
				else:
					pt_time = msg_ts
			
			if fv_m:
				fever_until = msg_ts + (int(fv_m.group(1)) + 1) * 60
			elif fv_less:
				fever_until = msg_ts + 90 # 1.5 хв запасу, якщо залишилось менше хвилини
			elif '🌡' not in t and event.is_private and not m.fwd_from:
				fever_until = 0
			
			if updates:
				save_mlab(updates)
				fv_info = f' | ⏳ Гарячка: {max(0, (fever_until - int(time.time())) // 60)} хв' if fever_until > time.time() else ''
				print(f'🔬 Лаба оновлена: {ostalos_pt}/{max_pt} патів | Квала: {kvala} ({61 - kvala} хв) | Летал: {letal} дн.{fv_info}')
		
		@client.on(events.NewMessage(incoming=True, from_users=6333102398,
		pattern=(
			r'(?s).*(?:🤒\s*(?:The laboratory is in fever|Лаборатория в горячке)|'
			r'💉\s*(?:Fever cured|Горячка вылечена)|'
			r'✅\s*(?:No fever detected|Горячки нет|Горячка не обнаружена)|'
			r'🧪\s*(?:No pathogens available|Нет доступных патогенов)|'
			r'👑\s*(?:The operation to infect|Операция по заражению))'
		)))
		
		async def track_fever(event):
			global fever_until, ostalos_pt, pt_time
			m = event.message
			if not event.is_private or m.fwd_from:
				return
			t = m.raw_text
			msg_ts = int(m.date.timestamp())
			
			if 'No pathogens available' in t or 'Нет доступных патогенов' in t:
				ostalos_pt = 0
				pt_time = msg_ts
				print('🛑 Патогени закінчились (0)! Зупиняю серію.')
				return
			
			if 'operation to infect' in t or 'Операция по заражению' in t:
				rem_m = re.search(r'(?:Left|Осталось):\s*(\d+)', t, re.IGNORECASE)
				if rem_m:
					ostalos_pt = int(rem_m.group(1))
					pt_time = msg_ts
					print(f'🛡️ Невдала атака! Залишилось патів: {ostalos_pt}/{max_pt}')
			
			if '🤒' in t:
				if re.search(r'(?:less than a minute|меньше минуты)', t, re.IGNORECASE):
					fever_until = msg_ts + 90
					print('🤒 Спіймали гарячку (менше хвилини)! Спимо ~1.5 хв.')
				else:
					mins_m = re.search(r'(\d+)\s*(?:min|мин)', t)
					mins_left = int(mins_m.group(1)) if mins_m else 10
					fever_until = msg_ts + (mins_left + 1) * 60
					print(f'🤒 Спіймали гарячку! Спимо ~{mins_left + 1} хв.')
			else:
				fever_until = 0
				#print('💉 Гарячки немає, можна працювати.')
		
		########################################################################
		
		@client.on(events.NewMessage(outgoing=True, 
		pattern=re.compile(r'^(?:\.п|[\./!]?мл)$', re.IGNORECASE)))
		async def cmd_mlab(event):
			if event.chat_id == 6333102398 or event.chat_id in irises:
				return
			
			try:
				async with client.conversation(6333102398, exclusive=False) as conv:
					await conv.send_message('/Lab')
					resp = await conv.get_response(timeout=15)
				
				if not resp or not resp.raw_text:
					await event.edit('❌ Не вдалося отримати дані лаби.')
					return
				
				t = resp.raw_text
				pt_m = re.search(r'🧪\s*(?:Pathogens|Свободных патогенов):\s*([^\n]+)', t)
				xp_m = re.search(r'☢️\s*(?:Bio-experience|Био-опыт):\s*([^\n]+)', t)
				res_m = re.search(r'🧬\s*(?:Bio-resource|Био-ресурс):\s*([^\n]+)', t)
				fv_m = re.search(r'🌡\s*(?:You have a fever\. Time left:|У тебя горячка\. Осталось)\s*(\d+)\s*(?:min|мин)', t)
				fv_less = re.search(r'🌡.*(?:less than a minute|меньше минуты)', t, re.IGNORECASE)
				
				lines = []
				if pt_m:
					lines.append(f'🧪 {pt_m.group(1).strip()}')
				if xp_m:
					lines.append(f'☣️ {xp_m.group(1).strip()}')
				if res_m:
					lines.append(f'🧬 {res_m.group(1).strip()}')
				
				if fv_m:
					lines.append(f'🌡 Гарячка: {fv_m.group(1)} хв')
				elif fv_less:
					lines.append('🌡 Гарячка: < 1 хв')
				else:
					lines.append('✅ ok')
				
				if not lines:
					await event.edit('❌ Не розпізнано формат лаби.')
					return
				
				await event.edit('\n'.join(lines))
			except asyncio.TimeoutError:
				await event.edit('⏳ Бот не відповів вчасно.')
			except Exception as e:
				await event.edit(f'❌ Помилка: {e}')
		
		########################################################################
		
		@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(?:bf_?stop|стоп)$'))
		async def cmd_bf_stop(event):
			if not is_allowed_chat(event):
				return
			global bf_run
			if bf_run:
				bf_run = False
				await event.edit('🛑 Зупиняю цикл жралки...')
			else:
				await event.edit('💤 Жралка і так не запущена.')
		
		@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(?:bf|biofuck|жрать)$'))
		async def cmd_bf_lite(event):
			if not is_allowed_chat(event):
				return
			global bf_run, last_bz_time, fever_until
			
			if not db_sqlite3:
				await event.edit('❌ SQLite вимкнено в конфігу.')
				return
			
			if bf_run:
				await event.edit('⏳ Цикл жралки вже працює... (зупинка: <code>.стоп</code>)')
				return
			
			bf_run = True
			await event.edit('♻️ Запущено циклічну жралку! (зупинка: <code>.стоп</code>)')
			
			try:
				while bf_run:
					now_ts = int(time.time())
					
					# 1. Якщо є гарячка — спимо до її завершення (+1 хв вже закладено у fever_until)
					if fever_until > now_ts:
						wait_fv = fever_until - now_ts
						print(f'🤒 Гарячка ще {wait_fv // 60} хв {wait_fv % 60} сек. Спимо...')
						await asyncio.sleep(min(wait_fv, 60)) # перевіряємо щохвилини
						continue
					
					# 2. Перевіряємо патогени. Якщо <= 1, чекаємо поки буде хоча б половина ємності
					target_threshold = max(2, max_pt // 2)
					cur_pt = get_pt()
					if cur_pt <= 1:
						print(f'⏳ Мало патів ({cur_pt}/{max_pt}). Чекаємо мінімум {target_threshold} шт. (перевірка раз на годину)...')
						while bf_run and get_pt() < target_threshold:
							await asyncio.sleep(3600)
						continue
					
					# 3. Оновлюємо список жертв (/бж), якщо не дивилися більше 5 хвилин
					if time.time() - last_bz_time > 300:
						last_bz_time = time.time()
						await client.send_message(6333102398, '/бж')
						await asyncio.sleep(random.uniform(2.5, 3.5))
					
					now_ts = int(time.time())
					need_targets = max(1, get_pt() - 1)
					
					c.execute("""
						SELECT user_id, bio_int FROM avocado 
						WHERE user_id >= 100
						AND user_id NOT IN (?, 6333102398, 1124824021) 
						AND (expr_int = 0 OR expr_int < ? OR bio_int < 5)
						ORDER BY when_int ASC 
						LIMIT ?
					""", (my_id, now_ts, need_targets))
					targets = c.fetchall()
					
					if not targets:
						print('🤷 Немає свіжих цілей без антилу в базі. Пауза 1 година...')
						await asyncio.sleep(3600)
						continue
					
					print(f'☣️ Серія атак: цілей {len(targets)} (патів: ~{get_pt()}/{max_pt})')
					sent_count = 0
					
					for target_id, bio_val in targets:
						if not bf_run:
							break
						# Якщо щойно спіймали гарячку — 
						if fever_until > int(time.time()):
							break
						if get_pt() <= 1:
							print(f'🛑 Зупинка серії: залишилось {ostalos_pt}/{max_pt} патогенів.')
							break
						
						cmd_text = f'.биоеб {target_id}'
						print(f'🎯 [{sent_count + 1}/{len(targets)}] Відправляю: {cmd_text}')
						await client.send_message(6333102398, cmd_text)
						sent_count += 1
						
						await asyncio.sleep(random.uniform(2.5, 4.5))
					
					if sent_count > 0 and (time.time() - last_bz_time > 15) and fever_until <= int(time.time()):
						last_bz_time = time.time()
						await asyncio.sleep(random.uniform(1.5, 2.5))
						await client.send_message(6333102398, '/бж')
					
					# Невелика пауза перед наступним витком циклу
					await asyncio.sleep(3)
					
			except Exception as e:
				print(f'⚠️ Помилка в циклі cmd_bf_lite: {e}')
			finally:
				bf_run = False
				print('🛑 Цикл жралки завершено.')
		
		########################################################################
		
		@client.on(events.NewMessage(outgoing=True, pattern=r'^\.btop$'))
		async def cmd_btop(event):
			if not is_allowed_chat(event):
				return
				
			global bf_run, last_bz_time
			
			if not db_sqlite3:
				await event.edit('❌ SQLite вимкнено в конфігу.')
				return
			if bf_run:
				await event.edit('⏳ Зараз працює циклічна жралка (<code>.стоп</code>).')
				return
			if fever_until > int(time.time()):
				await event.edit(f'🤒 Зараз гарячка ще ~{(fever_until - int(time.time())) // 60 + 1} хв.')
				return
			
			cur_pt = get_pt()
			if cur_pt <= 1:
				await event.edit(f'🛑 Мало патогенів ({cur_pt}/{max_pt} шт.).')
				return
			
			bf_run = True
			await event.edit('🔍 Збираю 1-шу та 2-гу сторінки Биоб...')
			
			try:
				pages_html = []
				async with client.conversation(6333102398, exclusive=False) as conv:
					await conv.send_message('Биоб')
					msg1 = await conv.get_response(timeout=15)
					if msg1 and msg1.raw_text:
						pages_html.append(utils.sanitize_parse_mode('html').unparse(msg1.raw_text, msg1.entities or []))
						
						# Переходимо на 2-гу сторінку по кнопці "2"
						if msg1.buttons:
							next_btn = None
							for row in msg1.buttons:
								for btn in row:
									if btn.text.strip() == '2':
										next_btn = btn
										break
								if next_btn:
									break
							if next_btn:
								await next_btn.click()
								await asyncio.sleep(random.uniform(1.2, 2.0))
								msg2 = await client.get_messages(6333102398, ids=msg1.id)
								if msg2 and msg2.raw_text:
									h2 = utils.sanitize_parse_mode('html').unparse(msg2.raw_text, msg2.entities or [])
									if h2 not in pages_html:
										pages_html.append(h2)
				
				if not pages_html:
					await event.edit('❌ Не вдалося отримати топ біо-досвіду.')
					return
				
				# Парсимо всі рядки з 1-ї та 2-ї сторінок по порядку
				row_pattern = re.compile(
					r'<a href="tg://openmessage\?user_id=(\d+)"[^>]*>[^<]+</a>\s*\|\s*[\d\s]+\s*\|\s*\+(\d+)',
					re.IGNORECASE
				)
				any_id_pattern = re.compile(r'tg://openmessage\?user_id=(\d+)', re.IGNORECASE)
				
				now_ts = int(time.time())
				candidates_ordered = [] # від 1-го до останнього місця
				seen_ids = set()
				
				for h_page in pages_html:
					for uid_s in any_id_pattern.findall(h_page):
						uid_i = int(uid_s)
						if uid_i >= 100:
							c.execute("""INSERT OR IGNORE INTO avocado 
							(user_id, when_int, bio_int, expr_int, expr_str) 
							VALUES (?, ?, 0, 0, '0')""", (uid_i, now_ts))
					
					# Відбираємо рядки без ⏳ і з активним +X
					for m_row in row_pattern.finditer(h_page):
						uid = int(m_row.group(1))
						plus_val = int(m_row.group(2))
						if uid in seen_ids or uid < 100 or uid == my_id:
							continue
						seen_ids.add(uid)
						candidates_ordered.append((uid, plus_val))
				
				conn.commit()
				
				# Розвертаємо список: спочатку низ 2-ї сторінки, потім низ 1-ї сторінки
				candidates_ordered.reverse()
				
				valid_targets = []
				need_limit = max(1, get_pt() - 1)
				
				for uid, plus_val in candidates_ordered:
					c.execute("SELECT bio_int, expr_int FROM avocado WHERE user_id = ?", (uid,))
					row_db = c.fetchone()
					if row_db:
						old_bio, expr_int = map(int, row_db)
						# Якщо активний наш антил — пропускаємо
						if expr_int > now_ts:
							continue
						# Якщо вже заражали раніше — б'ємо тільки якщо плюс у топі двозначний (>= 10)
						if old_bio > 1 and plus_val < 10:
							continue
					
					valid_targets.append((uid, plus_val))
					if len(valid_targets) >= need_limit:
						break
				
				if not valid_targets:
					await event.edit('🤷 У топі немає підходящих цілей (у всіх КД або менший профіт).')
					return
				
				await event.edit(f'🎯 Знайдено {len(valid_targets)} цілей знизу топу. Атакую...')
				sent_count = 0
				
				for uid, plus_val in valid_targets:
					if not bf_run or fever_until > int(time.time()) or get_pt() <= 1:
						break
					cmd_text = f'.биоеб {uid}'
					print(f'🏆 [Биоб {sent_count + 1}/{len(valid_targets)}] {cmd_text} (очікуємо +{plus_val})')
					await client.send_message(6333102398, cmd_text)
					sent_count += 1
					await asyncio.sleep(random.uniform(2.5, 4.5))
				
				if sent_count > 0 and (time.time() - last_bz_time > 15) and fever_until <= int(time.time()):
					last_bz_time = time.time()
					await asyncio.sleep(random.uniform(1.5, 2.5))
					await client.send_message(6333102398, '/бж')
				
				res_txt = f'✅ Простріл топу завершено! Атак: {sent_count} | Залишок патів: ~{get_pt()}/{max_pt}'
				print(res_txt)
				try:
					await event.edit(res_txt)
				except Exception:
					pass
				
			except Exception as e:
				print(f'⚠️ Помилка в cmd_btop: {e}')
				try:
					await event.edit(f'❌ Помилка: {e}')
				except Exception:
					pass
			finally:
				bf_run = False
		
		########################################################################
		
		@client.on(events.NewMessage(outgoing=True, pattern=r'^\.scn(?:\s+(.+))?$'))
		async def cmd_scn(event):
			if not is_allowed_chat(event):
				return
			global scn_run
			if scn_run:
				await event.edit('⏳ Скан уже триває...')
				return
			
			raw_arg = (event.pattern_match.group(1) or "@avocado_group").strip()
			
			save_txt = bool(re.search(r'(?:^|\s)\+txt(?:\s|$)', raw_arg, re.IGNORECASE))
			arg = re.sub(r'(?:^|\s)\+txt(?:\s|$)', ' ', raw_arg, flags=re.IGNORECASE).strip()
			if not arg:
				arg="@avocado_group"
			
			t_match = re.search(r'(?:https?://)?t\.me/([a-zA-Z0-9_]{4,})', arg)
			if t_match:
				target_ref = '@' + t_match.group(1)
			elif re.fullmatch(r'-?\d+', arg):
				num_id = int(arg)
				target_ref = -abs(num_id)
			else:
				target_ref = arg if arg.startswith('@') else '@' + arg
			
			try:
				target = await client.get_entity(target_ref)
			except Exception as e:
				await event.edit(f'❌ Не вдалося знайти чат <code>{arg}</code>: {e}', parse_mode='html')
				return
			
			if getattr(target, 'first_name', None) is not None and getattr(target, 'id', 0) != 6333102398:
				await event.edit('❌ Приватні чати з користувачами не скануються.')
				return
			
			scn_run = True
			title = getattr(target, 'title', None) or getattr(target, 'username', str(target.id))
			await event.edit(f'🔍 Сканую <b>{title}</b>...', parse_mode='html')
			
			found = set()
			checked = 0
			dump_lines = []
			try:
				async for m in client.iter_messages(target,from_user=6333102398):
					msg_ts = int(m.date.timestamp())
					if msg_ts < restart_timestamp:
						break
					checked += 1
					if m.raw_text:
						h = utils.sanitize_parse_mode('html').unparse(m.raw_text, m.entities or [])
						if save_txt:
							dump_lines.append(f"=== MSG ID: {m.id} | {m.date.strftime('%d.%m.%Y %H:%M:%S')} UTC ===\n{h}\n")
						for uid_s in re.findall(r'tg://openmessage\?user_id=(\d+)', h):
							u_id = int(uid_s)
							if u_id >= 100 and u_id not in (my_id, 6333102398, 1124824021):
								found.add(u_id)
								if db_sqlite3:
									c.execute("""INSERT OR IGNORE INTO avocado 
									(user_id, when_int, bio_int, expr_int, expr_str) 
									VALUES (?, ?, 0, 0, '0')""", (u_id, msg_ts))
								if db_pymysql:
									d.execute("""INSERT IGNORE INTO `tg_bio_users` 
									(`user_id`, `when_int`, `profit`) VALUES (%s, %s, 0)""", 
									(u_id, msg_ts))
					if checked % 100 == 0:
						if db_sqlite3:
							conn.commit()
						if db_pymysql:
							con.commit()
						await asyncio.sleep(0.5)
				if db_sqlite3:
					conn.commit()
				if db_pymysql:
					con.commit()
				
				res_msg = f'✅ Скан <b>{title}</b> завершено!\nПеревірено: {checked} | Нових ID: {len(found)}'
				if save_txt and dump_lines:
					work_dir = default_directory if (is_termux and default_directory) else '.'
					fname = os.path.join(work_dir, f"scan_{target.id}.txt")
					with open(fname, "w", encoding="utf-8") as tf:
						tf.write("\n".join(dump_lines))
					res_msg += f'\n💾 Дамп: <code>{fname}</code>'
				
				await event.edit(res_msg, parse_mode='html')
			except Exception as e:
				await event.edit(f'❌ Помилка скану: {e}')
			finally:
				scn_run = False
		
		########################################################################
		
		@client.on(events.NewMessage(incoming=True,from_users=irises,
		pattern=r'🗓 Ачивки.*')) # Дивляться в жабах, але пише й Іріс
		async def уже(event):
			c = event.chat_id
			m = event.message
			t = m.raw_text
			if 'Пока нет ни одной ачивки...' in t:
				try:
					await client.delete_messages(event.chat_id, m.id) # try del.
				except:
					pass
					#Можливо просто нема адмінки і/або повідомлення вже видалено
		
		########################################################################
		
		@client.on(events.NewMessage(incoming=True, pattern='⚡️ Алло, подъем,',
		from_users=1124824021))
		async def подъем(event):
			c = event.chat_id
			m = event.message
			t = m.raw_text
			if m.mentioned and 'Нашелся вражеский клан:' in t:
				print(t) # показать в консолі повідомлення
				w = random.uniform(3,6666) # скільки ждем?
				print(f'⏳ wait {w}')
				await asyncio.sleep(w)
				Осталось = int(await реанимировать_жабу(c))
				if Осталось:
					await asyncio.sleep(random.uniform(60,64)) # 1+m
					m = await client.send_message(c,'Напасть на клан')
					await asyncio.sleep(random.uniform(60,64)) # 1+m
					await client.send_message(c,'Реанимировать жабу')
		
		########################################################################
		
		@client.on(events.NewMessage(incoming=True, pattern='Боевая готовность',
		from_users=1124824021))
		async def готовность(event):
			c = event.chat_id
			m = event.message
			t = m.raw_text
			if m.mentioned and 'Не забудь совершить атаку на арене!' in t:
				await asyncio.sleep(random.uniform(61,111)) # 1+m
				Осталось = int(await реанимировать_жабу(c))
				if Осталось == 0:
					return # :(
				await asyncio.sleep(random.uniform(61,69)) # 1+m
				await client.send_message(c,'На арену')
		
		########################################################################
		
		@client.on(events.NewMessage(incoming=True, 
		pattern=r'(Нет ни одного участника забега|Первой к финишу пришла жабка)',
		from_users=1124824021))
		async def Гонка(event):
			c = event.chat_id
			m = event.message
			т = '@toadbot Гонка 50'
			if c in chts or c==-1001186908367:
				await client.send_message(c,т)
		
		########################################################################
		
		@client.on(events.NewMessage(incoming=True, from_users=1124824021,
		pattern='Можно завершить работу'))
		async def завершить_работу(event):
			c = event.chat_id
			m = event.message
			if c not in chts:
				return
			message = '@toadbot Завершить работу'
			if m.mentioned:
				m = await client.send_message(c,message)
		
		########################################################################
		
		@client.on(events.NewMessage(incoming=True, from_users=1124824021,
		pattern=r'(Ваша|Твоя) жабка нуждается в реанимации'))
		async def нуждается_в_реанимации(event):
			c = event.chat_id
			m = event.message
			if m.mentioned:
				now = datetime.now()
				hours = now.hour
				minutes = now.minute
				Осталось= 0 # потом
				Покормить = False
				if m.buttons:
					for row in m.buttons:
						for button in row:
							if 'аптечку' in button.text:
								await asyncio.sleep(random.uniform(1.234, 2.56))
								Осталось = int(await реанимировать_жабу(c))
							if 'Покормить' in button.text:
								await asyncio.sleep(random.uniform(1.234, 2.56))
								await client.send_message(c,'Покормить жабу')
								Покормить = True # Вважаємо що покормили
				else:
					await asyncio.sleep(random.uniform(1.234, 2.987))
					Осталось = int(await реанимировать_жабу(c))
				
				if int(Осталось)<1 and Покормить == False:
					return # думаю що пофіксив зациклювання
				
				await asyncio.sleep(random.uniform(1.234, 2.987))
				
				if hours == 23 or hours == 0:
					if c!=-1002671146796 or minutes < 11:
						await client.send_message(c, 'Жабу на тусу')
				elif 8 <= hours <= 22 and minutes < 49:
					await client.send_message(c, 'На арену')
					await asyncio.sleep(random.uniform(1,9))
					await client.send_message(c,'Реанимировать жабу')
				
		
		@client.on(events.NewMessage(incoming=True, 
		from_users=1124824021,
		pattern=r'.*(П|п)обед.*'))
		async def Побед(event):
			c = event.chat_id
			m = event.message
			t = m.raw_text
			if m.mentioned:
				now = datetime.now()
				hours=int(now.hour)
				minutes = now.minute
				if m.buttons:
					for row in m.buttons:
						for button in row:
							if 'аптечку' in button.text:
								await asyncio.sleep(random.uniform(1.234, 2.56))
								await client.send_message(c,'Реанимировать жабу')
							if 'топ' in button.text and hours>20:
								await asyncio.sleep(random.uniform(1,3.5))
								await client.send_message(c,'Сезон арены')
				if 'Банда получила критическое повреждение' in t:
					h = utils.sanitize_parse_mode('html').unparse(t,m.entities)
					r = re.findall(r'жабы <a href="tg://user\?id=([0-9]+)">',h)
					u = my_id
					print(t)
					if r:
						u = int(r[0])
						if u!=my_id:
							return
					await asyncio.sleep(random.uniform(1.23,3.5))
					await client.send_message(c,'Отдать леденец')
		
		########################################################################
		
		@client.on(events.NewMessage(incoming=True,from_users=1124824021,
		pattern=r'.*путь:.*'))
		async def путь(event):
			c = event.chat_id
			m = event.message
			t = m.raw_text
			h = utils.sanitize_parse_mode('html').unparse(t,m.entities)
			u = int(re.findall(r'путь: <a href="tg://user\?id=([0-9]+)">',h)[0])
			r = re.findall(r'Теперь <a href="tg://user\?id=([0-9]+)">',h)
			await asyncio.sleep(random.uniform(1.0001, 2.56))
			if r:
				r = int(r[0])# хто має?
			if m.mentioned or u==my_id:
				for row in m.buttons:
					for button in row:
						if 'аптечку' in button.text and r==my_id:
							Осталось =int(await реанимировать_жабу(c))
							await asyncio.sleep(random.uniform(1.1,2))
						if 'прямо' in button.text:
							result=await button.click()
							if result.message:
								print(result.message)
								#те що було далі вобще чомусь не працювало
								#я пока не поняв чому, тому покищо уберу.
							print(result)
							break
		
		########################################################################
		
		@client.on(events.NewMessage(incoming=True,from_users=1124824021,
		pattern=r'.*уже.*'))
		async def уже(event):
			c = event.chat_id
			m = event.message
			t = m.raw_text
			if c not in chts:
				return
			if 'Давай начнем работу' in t:
				if m.mentioned:
					m = await client.send_message(c,'Начать работу')
			
			return
		
		########################################################################
		
		@client.on(events.NewMessage(incoming=True,from_users=1968071106))
		# той бот пише рекламу. тому "слухаємо" все (без патерна)
		async def уже(event):
			c = event.chat_id
			m = event.message
			t = m.raw_text
			needdel=False
			if c not in chts:
				return
			# А що саме будемо видаляти перерахую нижче. пока "подарок":
			if 'Получен Подарок' in t:
				needdel=True # якщо параметрів буде більше це нам знадобиться.
				await client.delete_messages(event.chat_id, m.id) # try delete
		
		########################################################################
		
		@client.on(events.NewMessage(outgoing=True, pattern=r'.chts$'))
		async def sv_cheats(event):
			c = event.chat_id
			m = event.message
			t = m.raw_text
			global chts
			pong = '??'
			try:
				with open(chts_file, "r") as read_file:
					chts = json.load(read_file)
					need_save=False
			except Exception as Err:
				print(Err)
			if int(c) > 0:
				pong='Алоу це не чат!' #wtf?!
				await event.edit(pong) # ред.
				print(pong)
				return
			if ch_id < 0:
				if ch_id not in chts:
					chts.append(ch_id)
					need_save=True
			if t=='+chts' or t=='-chts':
				if '+' in t:
					if c not in chts:
						chts.append(c)
						need_save=True
					pong=f'✅ sv_cheats 1\n💬<code>{c}</code>'
				if '-' in t:
					if c in chts:
						chts.remove(c)
						need_save=True
					pong=f'❎ sv_cheats 0\n💬<code>{c}</code>'
				if need_save:
					with open(chts_file, "w", encoding="utf-8") as write_file:
						json.dump(chts,write_file,ensure_ascii=False,indent='	')
			else:
				if c in chts:
					pong=f'✅ sv_cheats 1\n💬<code>{c}</code>' # ok?!
				if c not in chts:
					pong=f'❎ sv_cheats 0\n💬<code>{c}</code>' # off!
			try:
				await event.edit(pong) # ред.
				print(pong)
			except:
				pass
		
		########################################################################
		
		@client.on(events.NewMessage(outgoing=True, pattern=r'.дов'))
		async def dovs(event):
			c = event.chat_id
			m = event.message
			t = m.raw_text
			u = 0 #user id
			global dovs
			
			try:
				with open(dovs_file, "r") as read_file:
					dovs = json.load(read_file)
					need_save=False
			except Exception as Err:
				print(Err)
			if my_id not in dovs:
				dovs.append(my_id)
				need_save=True
			if '+дов' in t or '-дов' in t:
				pong=False
				plus=False
				minus=False
				if '+' in t:
					plus=True
				if '-' in t:
					minus=True
				if '@' in t: # працює з @ якщо далі йде айді юзера
					u = int(re.findall(r'([0-9]+)',t)[0]) or False
				if "tg://openmessage?user_id=" in t or "tg://user?id=" in t:
					u = int(re.findall(r'id=([0-9]+)',t)[0])
				if u:# якщо отримали айді юзера
					if u not in dovs and plus:
						dovs.append(u)
						need_save=True
					if u in dovs and minus:
						dovs.remove(u)
						need_save=True
					if plus:
						pong=f'✅ +дов @{u}' # ok?!
					if minus:
						pong=f'❎ -дов @{u}' # ok?!
				if pong:
					try:
						await event.edit(pong)
						print(pong)	#	print
					except:
						pass
			if need_save:
				with open(dovs_file, "w", encoding="utf-8") as write_file:
					json.dump(dovs,write_file,ensure_ascii=False,indent='	')
		
		########################################################################
		
		@client.on(events.NewMessage(pattern=r'\.send'))
		async def cmd_send_in(event):
			c = event.chat_id
			m = event.message
			t = m.raw_text
			u = int(m.sender_id)
			д = await id_dov(u)
			т = str(re.findall(r"\.send .*",t)[0]) or False
			if t=='.send' or t=='.send ':
				т = 'А текст?' # .send т
			if т:
				т = str(re.sub(r"\.send ",'',т))
			if "ping" in t:
				#т = '𝐏𝐎𝐍𝐆' # 𝐏𝐎𝐍𝐆
				return # ібо нєхуй
			if c in chts and д and т:
				print(f'🆔 {u}: {t}')
				await asyncio.sleep(random.uniform(2,6))
				m = await client.send_message(c,т)#send.
				await asyncio.sleep(random.uniform(4,6))
				fordel = m.id
				if u==my_id:
					fordel=[event.id, m.id]
				await client.delete_messages(event.chat_id,fordel)
		
		########################################################################
		
		@client.on(events.NewMessage(outgoing=True, 
		pattern=r'.ква$'))
		async def cmd_к(event):
			# хелпа по жабам
			help_message = f'''
			<blockquote>🐸 ЖАБА:</blockquote>
			<code>Взять жабу</code> /take_toad
			<code>Дейлики</code> /daily_quests
			<code>Жаба инфо</code> /toad_info
			<blockquote>🐸 Арена / снаряга</blockquote>
			<code>На арену</code>
			<code>Рейд инфо</code>
			<code>Мое снаряжение</code>
			<blockquote>🐞 Букашки:</blockquote>
			<code>Где жаба</code>
			<code>Моя комната</code>
			<code>Покормить жабу</code>
			<blockquote>🐸 Клан / класс</blockquote>
			<code>Мой клан</code>
			<code>Война инфо</code>
			<code>Выбрать класс</code>
			<code>Сменить класс</code>
			<code>Напасть на клан</code>
			<code>Отправить карту</code>
			<code>Отправиться за картой</code>
			<blockquote>🐸 НАСТРОЙКИ:</blockquote>
			/battle_settings@toadbot
			/toad_notifications@toadbot
			'''
			try:
				await asyncio.sleep(random.uniform(0.3,1))
				await event.edit(help_message) # ред.
			except:
				pass
		
		########################################################################
		
		@client.on(events.NewMessage(outgoing=True, 
		pattern=r'^.(?:he?lp|хе?лпа?)$'))
		async def cmd_help(event):
			help_message = f'''
			<blockquote>📃 код і є документація 😈</blockquote>
			
			<code>.ping</code> – "pong!", del.
			<code>+chts</code> – ✅ sv_cheats 1	*
			<code>-chts</code> – ❎ sv_cheats 0	*
			<code>+дов @ід</code> – ✅ +дов @ід	**
			<code>-дов @ід</code> – ❎ -дов @ід	**
			<code>.send </code> – пише текст***
			
			<blockquote>🧬 Авокадо:</blockquote>
			<code>.bf</code> – атака цілей в ЛС
			<code>.scn</code> – скан чату в базу
			<code>.стоп</code> – вирубаємо .bf
			<code>.btop</code> – жрем биоб
			<code>.мл</code> – мікролаба
			
			<blockquote>🐸 Інше:</blockquote>
			<code>.ква</code> – шпаргалка по жабах
			<code>.help</code> – <u>you are here</u>
			
			*	впливає на <code>.ping</code> і <code>.send</code>
			**	+/-дов через @(ід_кого)
			***	якщо є дов і вкл. <code>+chts</code>
			
			<code>https://github.com/S1S13AF7/ub4tg</code> – <a 
			href="https://github.com/S1S13AF7/ub4tg">code</a>;
			'''
			try:
				await asyncio.sleep(random.uniform(0.3,1))
				await event.edit(help_message) # ред.
			except:
				pass
		
		########################################################################
		
		@client.on(events.NewMessage(pattern=r'^\.pull$'))
		async def cmd_pull(event):
			sender_id = int(event.sender_id or 0)
			if event.out:
				if not is_allowed_chat(event):
					return
			else:
				if event.chat_id not in (MAINchatID, ch_id) or not await id_dov(sender_id):
					return
			
			import subprocess
			if event.out:
				await event.edit('⏳ Підтягую git pull...')
			else:
				await asyncio.sleep(random.uniform(0.5, 3.0))
			
			repo_dir = os.path.dirname(os.path.abspath(__file__))
			try:
				loop = asyncio.get_running_loop()
				proc = await loop.run_in_executor(
					None,
					lambda: subprocess.run(
						['git', 'pull'],
						cwd=repo_dir,
						capture_output=True,
						text=True,
						timeout=30
					)
				)
			except Exception as e:
				print(f'[{my_id}] ❌ Помилка git pull: {e}')
				if event.out:
					await event.edit(f'❌ Помилка: {e}')
				return
			
			out_text = (proc.stdout or proc.stderr or '').strip()
			print(f'[{my_id}] git pull: {out_text}')
			if event.out:
				await event.edit(
					f'📥 <b>git pull:</b>\n<code>{out_text[:400]}</code>',
					parse_mode='html'
				)
		
		########################################################################
		
		@client.on(events.NewMessage(incoming=True, pattern='.ping'))
		async def cmd_ping_in(event):
			c = event.chat_id
			m = event.message
			s = m.sender_id
			pong='✅ 𝐏𝐎𝐍𝐆!'
			needsend=False
			if c in chts:
				if c==ch_id:
					needsend=True
				elif await id_dov(s):
					needsend=True
				else:
					needsend=False
			if needsend:
				# Say "𝐏𝐎𝐍𝐆!",del. message
				m = await event.reply(pong)
				await asyncio.sleep(random.uniform(2,8))
				await client.delete_messages(event.chat_id, m.id)
		
		########################################################################
		
		@client.on(events.NewMessage(outgoing=True, pattern='.ping'))
		async def cmd_ping(event):
			# print ('✅ 𝐏𝐎𝐍𝐆!')
			# Say "𝐏𝐎𝐍𝐆!",delete messages.
			m = await event.reply('𝐏𝐎𝐍𝐆!')
			await asyncio.sleep(random.uniform(4,8))
			await client.delete_messages(event.chat_id, [event.id, m.id])
		
		########################################################################
		
		if config.get("farm") and ch_id < 0:
			await ферма()
		
		########################################################################
		
		await client.run_until_disconnected()
		
		########################################################################
		
asyncio.run(main())
