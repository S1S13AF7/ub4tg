# -*- coding: utf-8 -*-

import asyncio

from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events, functions, types, utils

import os
import re
import random
import time
import json

import sqlite3

import shutil
import typing

if os.name == 'nt':
	import win32api

import calendar

sessdb = 'tl-ub' # назва бази сесії telethon
default_directory = '' # "робоча папка" бота
CONFIG_PATH = "conf.json"	# main config file
chts_file = "chts.json"		# чати де працюватимуть "чіти"
dovs_file = "dovs.json"		# "дови" ("ДОВірені юзерИ")
bio_0_url = "https://misc.pp.ua/files/0.zip" # <--- пряме посилання на 0.zip
is_termux = os.environ.get('TERMUX_APP__PACKAGE_NAME') or os.environ.get('TERMUX_APK_RELEASE')

termux_api = False # там нижче буде перевизначено якщо is_termux == True

if is_termux:
	import sys
	# майже все що для термукса я вкрав з форка бота.
	print('Termux detected, checking permissions...')
	termux_api = os.system('termux-api-start') == 0 #	штука для сповіщеннь.
	if (os.environ.get('TERMUX_APP__APK_RELEASE') or os.environ.get('TERMUX_APK_RELEASE')) not in ('F_DROID', 'GITHUB'):
		print('You use not f-droid/github apk release, it may have problems...')
		print('F-droid termux release here: https://f-droid.org/packages/com.termux/')
		print('Github termux release here: https://github.com/termux/termux-app/releases')
	if float((os.environ.get('TERMUX_VERSION') or '0.119')[:5]) < 0.118:
		print('You use old version of termux, highly recommended that you update to v0.119.0 or higher ASAP for various bug fixes, including a critical world-readable vulnerability')
	if termux_api:
		print('✅ termux API work')
	if os.access('/sdcard', os.W_OK):
		print('✅ дозвіл на запис')
		default_directory = '/sdcard/ub4tg'
		os.system(f'mkdir -p {default_directory}')
		CONFIG_PATH = f'{default_directory}/conf.json' # в доступну без рута
		#chts_file = f'{default_directory}/{chts_file}' # в доступну без рута
		#dovs_file = f'{default_directory}/{dovs_file}' # в доступну без рута
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
		'ch_id': int(config.get('ch_id', -1002236064671)),
		'db_sqlite3': bool(config.get('db_sqlite3', True)),
		'db_pymysql': bool(config.get('db_pymysql', False)),
		'mysql': config.get('mysql') if isinstance(config.get('mysql'), dict) else {
			'host': 'localhost',
			'user': 'root',
			'password': 'V3rY$tR0NgPaS$Sw0Rd',
			'db': 'db'
		},
		'wakelock': bool(config.get('wakelock', False)),
		'farm': bool(config.get('farm', True)),
		'mine': bool(config.get('mine', True))
	}
	# Дописуємо в кінець усі інші ключі, які вже були в конфігу (старі або кастомні)
	for k, v in config.items():
		if k not in ordered_config:
			ordered_config[k] = v
			
	config.clear()
	config.update(ordered_config)
	with open(CONFIG_PATH, "w", encoding="utf-8") as f:
		json.dump(config, f, ensure_ascii=False, indent='\t')

if not os.path.exists(CONFIG_PATH):
	config = {
		'api_id': int(input('enter api_id from https://telegram.org :')),
		'api_hash': input('enter api_hash from https://telegram.org :').strip(),
		'ch_id': 0
	}
	save_config()

with open(CONFIG_PATH, "r", encoding="utf-8") as configfile:
	#from types import SimpleNamespace
	config = json.load(configfile)
	print('✅ config loaded')

api_id = int(config['api_id'])
api_hash = config['api_hash']
ch_id = int(config.get('ch_id') or -1002236064671)

if ch_id >= 0:
	ch_id = -1002236064671
	config['ch_id'] = ch_id
	print('неправильний id чата; пробуємо "стандартний" * якщо ти є там?')

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
mine = True
f_run = False
m_run = False
bf_run = False
scn_run = False
last_bz_time=0# Коли дивились "бж"
ostalos_pt=10 # осталось. буде мінятись. 
save_config() # Вирівнює порядок ключів у файлі та прибирає зайве

################################################################################

irises = [707693258,5137994780,5226378684,5434504334,5443619563,8611067852]

################################################################################

def get_config_key(key: str) -> typing.Union[str, bool]:
	"""
	Parse and return key from config
	:param key: Key name in config
	:return: Value of config key or `False`, if it doesn't exist
	"""
	try:
		with open(CONFIG_PATH, "r", encoding="utf-8") as f:
			config = json.load(f)

		return config.get(key, False)
	except FileNotFoundError:
		return False

################################################################################

def save_config_key(key: str, value: str) -> bool:
	"""
	Save `key` with `value` to config
	:param key: Key name in config
	:param value: Desired value in config
	:return: `True` on success, otherwise `False`
	"""
	try:
		# Try to open our newly created json config
		with open(CONFIG_PATH, "r", encoding="utf-8") as f:
			config = json.load(f)
	except FileNotFoundError:
		# If it doesn't exist, just default config to none
		# It won't cause problems, bc after new save
		# we will create new one
		config = {}
	
	# Assign config value
	config[key] = value
	
	# And save config
	with open(CONFIG_PATH, "w", encoding="utf-8") as f:
		json.dump(config, f,ensure_ascii=False, indent='	')
	
	return True

################################################################################
chts=[]
if ch_id < 0:
	chts.append(ch_id)
try:
	chts_file = "chts.json"		# чати:
	with open(chts_file, "r") as read_file:
		chts = json.load(read_file)
except:
	with open(chts_file, "w", encoding="utf-8") as write_file:
		json.dump(chts, write_file,ensure_ascii=False, indent='	')
################################################################################
dovs=[]
try:
	dovs_file = "dovs.json"		# дови:
	with open(dovs_file, "r") as read_file:
		dovs = json.load(read_file)
except:
	with open(dovs_file, "w", encoding="utf-8") as write_file:
		json.dump(dovs, write_file,ensure_ascii=False, indent='	')
################################################################################

async def main():
	global db_pymysql
	async with TelegramClient(sessdb,api_id,api_hash,timeout=300) as client:
		client.parse_mode="HTML"
		print('User-Bot started')
		me= await client.get_me()
		my_id = int(me.id)
		my_uz = me.username
		print(f'🆔 {my_id}')
		
		if os.name == 'nt':
			win32api.SetConsoleTitle(f'{my_id}')
		elif os.name == 'posix':
			print(f'\33]0;{my_id}\a', end='', flush=True)
		
		if is_termux:
			if get_config_key("wakelock"):
				# якщо у конфіґу "wakelock": true,
				print('Prevent killing termux by android, getting wakelock...')
				os.system('termux-wake-lock')
				print('This can cause battery drain!')
		
		bio_bot_username = '@bio_attacker_bot' # <--- правильний юзернейм
		restart_timestamp = 1794601985 # 13.11.2026 20:33:05 UTC (перезапуск гри)
		
		try:
			bio_bot = await client.get_entity(bio_bot_username)
			bio_attacker_bot_ID = int(bio_bot.id)
			#print(f'🤖 Знайдено бота {bio_attacker_bot_ID}')
			
			# Перевіряємо, чи є вже повідомлення в ЛС із ботом
			msgs = await client.get_messages(bio_bot, limit=1)
			if not msgs:
				await client.send_message(bio_bot, '/start')
				print(f'👋 ЛС було порожнім — надіслано /start для {bio_bot_username}')
		except Exception as e:
			print(f'❌ Не вдалося знайти {bio_bot_username}: {e}')
			bio_attacker_bot_ID = 6333102398 # резервний ID, якщо виникла помилка
		
		if db_pymysql:
			try:
				import pymysql
				import pymysql.cursors
			except ImportError:
				print('❌ Бібліотека pymysql не встановлена. Вимикаю MySQL...')
				db_pymysql = False
				save_config_key('db_pymysql', False)
		
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
					save_config_key('mysql', mysql_conf)
					break
				
				except pymysql.err.OperationalError as e:
					err_code = e.args[0] if e.args else 0
					
					if err_code == 1045:
						print(f'⚠️ Невірний пароль для MySQL ({mysql_conf.get("user")}@{mysql_conf.get("host")}).')
						new_pass = input('Введіть правильний пароль (або натисніть Enter, щоб вимкнути MySQL): ').strip()
						if new_pass:
							mysql_conf['password'] = new_pass
							continue
						else:
							print('🚫 MySQL вимкнено для цієї та наступних сесій.')
							db_pymysql = False
							save_config_key('db_pymysql', False)
							break
					else:
						print(f'❌ Не вдалося підключитися до MySQL (код {err_code}): {e}')
						print('🚫 MySQL автоматично вимкнено в конфігу. Бот працюватиме на SQLite.')
						db_pymysql = False
						save_config_key('db_pymysql', False)
						break
				
				except Exception as e:
					print(f'❌ Невідома помилка MySQL: {e}')
					db_pymysql = False
					save_config_key('db_pymysql', False)
					break
		
		# Окремий блок: виконується ТІЛЬКИ якщо підключення вище пройшло успішно
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
			`profit` int(11) unsigned NOT NULL DEFAULT '1',
			`until_int` int(11) unsigned NOT NULL DEFAULT '0',
			`until_str` varchar(11) NOT NULL DEFAULT '0',
			UNIQUE KEY `UNIQUE` (`who_id`,`user_id`)
			);''');
			con.commit()
			# Оновлена таблиця користувачів БЕЗ virus,з полем коли (when_int)
			d.execute('''CREATE TABLE IF NOT EXISTS `tg_bio_users` (
			`user_id` bigint(20) unsigned NOT NULL DEFAULT '0',
			`when_int` int(11) unsigned NOT NULL DEFAULT '0',
			`profit` int(11) unsigned NOT NULL DEFAULT '1',
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
			
			# Видаляємо сміттєві ID (< 100000)
			d.execute('DELETE FROM `tg_bio_attack` WHERE `user_id` < 100000')
			d.execute('DELETE FROM `tg_bio_users` WHERE `user_id` < 100000')
			
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
			bio_int	INTEGER NOT NULL DEFAULT 1,
			expr_int	INTEGER NOT NULL DEFAULT 0,
			expr_str	VARCHAR NOT NULL DEFAULT 0
			)''');
			conn.commit()
			
			# Зачистка старих записів та сміттєвих ID у SQLite
			c.execute('DELETE FROM avocado WHERE when_int < ? OR user_id<100000', 
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
		
		async def get_id(url):
			user_id = 0
			if "tg://openmessage?user_id=" in url or "tg://user?id=" in url:
				user_id = int(re.findall(r'id=([0-9]+)',url)[0])
				#print(user_id)# розкоментувать якщо нада бачить
				return user_id
			if "t.me/" in url:
				if db_pymysql:
					try:
						d.execute("""SELECT * FROM `tg_users_url` 
						WHERE `u_link` = %s ORDER BY `when_int` DESC""",
						(str(url),))
						user = d.fetchone();
						if user is None:
							pass
						else:
							user_id = int(user['user_id'])
							print(f'{url} in db: @{user_id}')
					except:
							pass
				if user_id==0:
					#return user_id # fucking limit # розкоментуйте щоб не резолв.
					try:
						user_entity = await client.get_entity(url)
						if user_entity.id:
							user_id = int(user_entity.id)
							user_fn = user_entity.first_name or ''
							print(f'✅ ok: {url} @{user_id}')
							if db_pymysql:
								try:
									d.execute("INSERT INTO `tg_users_url` (`when_int`,`user_id`,`u_link`,`f_name`) VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE user_id = VALUES (user_id),u_link = VALUES (u_link),f_name = VALUES (f_name),when_int = VALUES (when_int);", (int(time.time()),int(user_id),str(url),str(user_fn))); con.commit()
								except Exception as Err:
									print(f'E:{Err}')
					except Exception as Err:
						print(f'E:{Err}')
						#pass
			return user_id
		
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
				print(wtf)	# print
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
			while (get_config_key("farm")):
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
				print(m.raw_text)
				await Mining(random.uniform(7200.0072,7227.7227))
		
		########################################################################
		
		Active_victims = r'.*(Active\s+victims|Активные\s+жертвы)'
		#import calendar # можна перенести на самий верх файлу до інших імпортів
		@client.on(events.NewMessage(incoming=True, pattern=Active_victims))
		@client.on(events.MessageEdited(incoming=True, pattern=Active_victims))
		async def ActiveVictims(event):
			m = event.message # повідомлення
			s = m.sender_id # відправник
			t = m.raw_text # сам текст
			д = m.date # поточна дата
			# 1. ПЕРЕСЛАНІ
			if m.fwd_from:
				# Отримуємо ID того, ХТО створив оригінал
				# Бот — це користувач, тому перевіряємо isinstance
				if isinstance(m.fwd_from.from_id, types.PeerUser):
					s = m.fwd_from.from_id.user_id
				else:
					s = None
				msg_date = m.fwd_from.date # ДАТА ОРИГІНАЛЬНОГО ПОВІДОМЛЕННЯ
			else:
				s = m.sender_id # відправник поточного повідомлення
				msg_date = m.date # поточна дата
			# 2. ФІЛЬТР ПО БОТУ
			if s != 6333102398:
				return
				
			# 3. ФІЛЬТР ВІД СТАРОЇ ФІГНІ (використовується глобальний restart_timestamp)
			if int(msg_date.timestamp()) < restart_timestamp:
				return  # Повідомлення згенероване ДО перезапуску гри — ігноруєм
			д = int(msg_date.timestamp()) # Дата самого повідомлення від бота
			м = event.is_private and s == 6333102398 and not m.fwd_from # МОЄ
			
			if m.entities:
				h = utils.sanitize_parse_mode('html').unparse(t, m.entities)
				pattern = re.compile(
				r"""
				href="
				(?:tg://openmessage\?user_id=|https?://t\.me/)  # 1. Посилання
				(\d+)                                           # ID користувача (Група 1)
				"[^>]*>                                         # Закриття тегу <a>
				[^<]+                                           # Ім'я користувача
				</a>                                            # Закриваючий тег посилання
				\s*.—\s*                                        # Крапка і тире
				(?:<strong>)?                                    # 2. Можливий тег <strong>
				(\d+)                                           # Кількість (Група 2)
				(?:</strong>)?                                   # Закриття тегу <strong>
				\s*🧬\s*(?:until|до)\s+                          # Емодзі та слово "until/до"
				(?:<code>)?                                     # 3. Тег <code> навколо дати
				(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})             # Дата та час (Група 3)
				\s+UTC
				(?:</code>)?                                    # Закриття тегу <code>
				""",
				re.IGNORECASE | re.VERBOSE
				)
				
				for r in pattern.finditer(h):
					user_id = int(r.group(1))
					if user_id < 100000:
						continue
					bio = int(r.group(2))
					date_str = r.group(3)
					until_str = date_str.split(" ")[0] # Отримуємо "27.11.2026"
					
					# Конвертуємо в чистий UTC UNIX timestamp
					dt = datetime.strptime(date_str, "%d.%m.%Y %H:%M")
					until_ts = int(calendar.timegm(dt.timetuple()))
					
					# 🛡️ ПЕРЕВІРКА АНТІЛУ: якщо час дії жертви ВЖЕ МИНУВ
					if until_ts < int(time.time()):
						until_ts = 0 # пишемо як не інфікованого
						until_str = "0"
					
					if db_sqlite3:
						if м:
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
								OR (avocado.expr_int = 0 
								AND excluded.when_int > avocado.when_int)""", 
								(int(user_id), int(д), int(bio), int(until_ts), 
								str(until_str))); #conn.commit()
							except Exception as Err:
								print(f'err: {Err} avocado')
						elif user_id != my_id:
							try:
								# Вставляєм нового чужого пацієнта, або оновлюєм:
								c.execute("""INSERT INTO avocado 
								(user_id, when_int, bio_int, expr_int, expr_str)
								VALUES (?, ?, ?, 0, '0')
								ON CONFLICT(user_id) DO UPDATE SET
								when_int = excluded.when_int,
								bio_int = excluded.bio_int
								WHERE avocado.expr_int = 0 
								AND excluded.when_int > avocado.when_int""", 
								(int(user_id), int(д), int(bio)));#conn.commit()
							except Exception as Err:
								print(f'err: {Err} avocado not my')
					
					# 💾 ЗБЕРЕЖЕННЯ В MySQL (База на ноутбуці / Мультиакаунт)
					if db_pymysql:
						if м:
							try:
								d.execute("""INSERT INTO `tg_bio_attack` 
								(`date`, `who_id`, `user_id`, `profit`, 
								`until_int`, `until_str`) 
								VALUES (%s, %s, %s, %s, %s, %s)
								ON DUPLICATE KEY UPDATE 
								date = IF(VALUES(until_int) > until_int 
								OR (until_int = 0 AND VALUES(date) > date),
								VALUES(date), date),
								profit = IF(VALUES(until_int) > until_int 
								OR (until_int = 0 AND VALUES(date) > date), 
								VALUES(profit), profit),
								until_str = IF(VALUES(until_int) > until_int 
								OR (until_int = 0 AND VALUES(date) > date), 
								VALUES(until_str), until_str),
								until_int = IF(VALUES(until_int) > until_int 
								OR (until_int = 0 AND VALUES(date) > date), 
								VALUES(until_int), until_int)""",
								(int(д), int(my_id), int(user_id), int(bio), 
								int(until_ts), str(until_str)))
							except Exception as Err:
								print(f'err: {Err} (tg_bio_attack my)')
						
						# 🔵 ЗАГАЛЬНА ТАБЛИЦЯ КОРИСТУВАЧІВ (Усі пацієнти: і свої, і чужі)
						# Оновлюємо profit та when_int ТІЛЬКИ якщо дата (д) більша наявної
						try:
							d.execute("""INSERT INTO `tg_bio_users` 
							(`user_id`, `when_int`, `profit`) 
							VALUES (%s, %s, %s) 
							ON DUPLICATE KEY UPDATE 
							profit = IF(VALUES(when_int) > when_int, 
							VALUES(profit), profit),
							when_int = IF(VALUES(when_int) > when_int, 
							VALUES(when_int), when_int)""",
							(int(user_id), int(д), int(bio)))
						except Exception as Err:
							print(f'err: {Err} (tg_bio_users)')
					
					if м:
						print(f'@{user_id} +{bio} {until_ts} {until_str}')
				
				# ⚡ ЗБЕРІГАЄМО ВСЕ НА ДИСК ОДНИМ МАХОМ ДЛЯ ОБОХ БАЗ
				if db_sqlite3:
					try:
						conn.commit()  # Один комміт на весь список користувачів!
						optimize()     # Швидка оптимізація індексів
					except Exception as e:
						print(f"err final commit/optimize: {e}")
				
				if db_pymysql:
					try:
						con.commit()
					except Exception as e:
						print(f"err mysql final commit: {e}")
		
		########################################################################
		
		@client.on(events.NewMessage(incoming=True, from_users=6333102398,
		pattern=r'☣️\s*(Infection successful|Заражение успешно)'))
		async def infect(event):
			global last_bz_time
			m = event.message
			t = m.raw_text
			when = int(m.date.timestamp())
			
			# Перевірка на перезапуск гри
			if when < restart_timestamp:
				return
			
			if not m.entities:
				return
				
			h = utils.sanitize_parse_mode('html').unparse(t, m.entities)
			
			# 1. Витягуємо ID жертви (u2id) з блоку Target / Цель
			target_match = re.search(
				r'(?:Target|Цель):\s*<a href="(?:tg://openmessage\?user_id=|https?://t\.me/)(\d+)"',
				h, re.IGNORECASE
			)
			if not target_match:
				return
			u2id = int(target_match.group(1))
			if u2id < 100000:
				return
			
			# 2. Витягуємо отриманий біо-досвід (bio)
			bio_match = re.search(
				r'(?:Bio-experience gained|Получено био-опыта):\s*(?:<strong>)?\+?(\d+)(?:</strong>)?',
				h, re.IGNORECASE
			)
			bio = int(bio_match.group(1)) if bio_match else 1
			
			# Своїм вважаємо ТІЛЬКИ те, що прийшло в ЛС бота (не переслане)
			is_my = bool(event.is_private and not m.fwd_from)
			need_check_victims = False
			
			# Якщо це в ЛС бота — перевіряємо залишок патогенів
			if is_my:
				rem_match = re.search(
					r'(?:Pathogens remaining|Осталось патогенов):\s*(?:<strong>)?(\d+)(?:</strong>)?',
					h, re.IGNORECASE
				)
				if rem_match:
					global ostalos_pt
					ostalos_pt = int(rem_match.group(1))
					if ostalos_pt in (0, 1):
						need_check_victims = True
			
			# 3. ЗБЕРЕЖЕННЯ В SQLite (avocado)
			if db_sqlite3:
				if is_my:
					try:
						# Свій пацієнт (в ЛС): оновлюємо дату і біо, зберігаючи expr_int якщо він вже є
						c.execute("""INSERT INTO avocado 
						(user_id, when_int, bio_int, expr_int, expr_str)
						VALUES (?, ?, ?, 0, '0')
						ON CONFLICT(user_id) DO UPDATE SET
						when_int = excluded.when_int,
						bio_int = excluded.bio_int
						WHERE excluded.when_int >= avocado.when_int""",
						(u2id, when, bio))
						conn.commit()
					except Exception as Err:
						print(f'err: {Err} (infect sqlite my)')
				elif u2id != my_id:
					try:
						# Чужий пацієнт (усі з чатів): оновлюємо тільки якщо немає активного антилу
						c.execute("""INSERT INTO avocado 
						(user_id, when_int, bio_int, expr_int, expr_str)
						VALUES (?, ?, ?, 0, '0')
						ON CONFLICT(user_id) DO UPDATE SET
						when_int = excluded.when_int,
						bio_int = excluded.bio_int
						WHERE (avocado.expr_int = 0 OR avocado.expr_int < excluded.when_int)
						AND excluded.when_int >= avocado.when_int""",
						(u2id, when, bio))
						conn.commit()
					except Exception as Err:
						print(f'err: {Err} (infect sqlite other)')
			
			# 4. ЗБЕРЕЖЕННЯ В MySQL
			if db_pymysql:
				# А) В особисту таблицю атак — ТІЛЬКИ якщо це в ЛС бота
				if is_my:
					try:
						d.execute("""INSERT INTO `tg_bio_attack` 
						(`date`, `who_id`, `user_id`, `profit`, `until_int`, `until_str`) 
						VALUES (%s, %s, %s, %s, 0, '0')
						ON DUPLICATE KEY UPDATE 
						date = IF(VALUES(date) >= date, VALUES(date), date),
						profit = IF(VALUES(date) >= date, VALUES(profit), profit)""",
						(when, my_id, u2id, bio))
					except Exception as Err:
						print(f'err: {Err} (infect tg_bio_attack)')
				
				# Б) У загальну таблицю юзерів — пишемо всіх з реальним біо та свіжою датою
				try:
					d.execute("""INSERT INTO `tg_bio_users` 
					(`user_id`, `when_int`, `profit`) 
					VALUES (%s, %s, %s) 
					ON DUPLICATE KEY UPDATE 
					profit = IF(VALUES(when_int) >= when_int, VALUES(profit), profit),
					when_int = IF(VALUES(when_int) >= when_int, VALUES(when_int), when_int)""",
					(u2id, when, bio))
				except Exception as Err:
					print(f'err: {Err} (infect tg_bio_users target)')
				
				try:
					con.commit()
				except Exception as Err:
					print(f'err: {Err} (infect mysql commit)')
			
			if is_my:
				print(f'☣️ Заражено @{u2id} (+{bio})')
			
			# 5. Якщо залишилось 0 або 1 патогенів — запитуємо /бж в ЛС бота
			if need_check_victims and (time.time() - last_bz_time > 15):
				last_bz_time = time.time()
				await asyncio.sleep(random.uniform(1.5, 3.5))
				await client.send_message(6333102398, '/бж')
		
		bz_aliases = r'^(?:[\./!]{1,2})?(?:victims?|бж|жертвы|био(?:ежа|жертвы|доход|зараженные))(?:\s+\d+)?$'
		@client.on(events.NewMessage(outgoing=True, pattern=re.compile(bz_aliases, re.IGNORECASE)))
		async def cmd_bz_out(event):
			global last_bz_time
			if event.chat_id == 6333102398:
				last_bz_time = time.time()
		
		########################################################################
		
		@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(?:bf|biofuck|жрать)$'))
		async def cmd_bf_lite(event):
			
			global bf_run, ostalos_pt, last_bz_time
			
			if not db_sqlite3:
				await event.edit('❌ SQLite вимкнено в конфігу.')
				return
			
			if bf_run:
				await event.edit('⏳ Жралка вже працює...')
				return
			
			if ostalos_pt <= 1:
				await event.edit(f'🛑 Мало патогенів ({ostalos_pt} шт.). Відбій.')
				return
			
			bf_run = True
			
			try:
				# Якщо давно (> 5 хв) не оновлювали список активних жертв — спершу запитуємо /бж
				if time.time() - last_bz_time > 300:
					last_bz_time = time.time()
					await event.edit('🔄 Оновлюю список жертв (/бж) перед атакою...')
					await client.send_message(6333102398, '/бж')
					await asyncio.sleep(random.uniform(2.5, 3.5)) # Чекаємо ...
				
				now_ts = int(time.time())
				
				# Беремо 10 найстаріших пацієнтів без активного антилу або з біо < 5
				c.execute("""
					SELECT user_id, bio_int FROM avocado 
					WHERE user_id >= 100000
					AND user_id NOT IN (?, 6333102398, 1124824021) 
					AND (expr_int = 0 OR expr_int < ? OR bio_int < 5)
					ORDER BY when_int ASC 
					LIMIT 10
				""", (my_id, now_ts))
				targets = c.fetchall()
				
				if not targets:
					await event.edit('🤷 Немає свіжих цілей без антилу в базі.')
					return
				
				await event.edit(f'☣️ Знайдено цілей: {len(targets)}. Починаю в ЛС бота...')
				sent_count = 0
				
				for target_id, bio_val in targets:
					# Зупиняємось, якщо залишився 1 (або 0) патоген
					if ostalos_pt <= 1:
						print(f'🛑 Зупинка: залишилось {ostalos_pt} патогенів.')
						break
					
					cmd_text = f'.биоеб {target_id}'
					print(f'🎯 [{sent_count + 1}/{len(targets)}] Відправляю: {cmd_text}')
					await client.send_message(6333102398, cmd_text)
					sent_count += 1
					
					# Чекаємо, щоб бот відповів і хендлер infect оновив ostalos_pt
					await asyncio.sleep(random.uniform(2.5, 4.5))
				
				# Якщо хендлер infect ще не викликав /бж робимо це самі
				if sent_count > 0 and (time.time() - last_bz_time > 15):
					last_bz_time = time.time()
					await asyncio.sleep(random.uniform(1.5, 2.5))
					await client.send_message(6333102398, '/бж')
					
				res_text = f"""✅ Відправлено атак: {sent_count} | 
				Залишок патогенів: ~{ostalos_pt}"""
				print(res_text)
				try:
					await event.edit(res_text)
				except Exception:
					pass
					
			except Exception as e:
				print(f'⚠️ Помилка в cmd_bf_lite: {e}')
			finally:
				bf_run = False
		
		########################################################################
		
		@client.on(events.NewMessage(outgoing=True, pattern=r'^\.scn(?:\s+(.+))?$'))
		async def cmd_scn(event):
			global scn_run
			
			if not db_sqlite3 and not db_pymysql:
				await event.edit('❌ Обидві бази даних вимкнено в конфігу.')
				return
				
			if scn_run:
				await event.edit('⏳ Сканування вже запущено...')
				return
			
			scn_run = True
			
			# Якщо вказали чат після команди (.scn @chat) — беремо його;
			# якщо написали в групі — скануємо поточну групу;
			# якщо в ЛС / Збереженому — беремо офіційний чат @avocado_group
			arg = event.pattern_match.group(1)
			if arg:
				target_chat = arg.strip()
			elif event.is_group or event.is_channel:
				target_chat = event.chat_id
			else:
				target_chat = '@avocado_group'
			
			await event.edit(f'🔍 Починаю лайт-сканування `{target_chat}` до дати перезапуску...')
			
			# Регулярка для списків жертв з точним БІО
			victims_pattern = re.compile(
				r"""
				href="
				(?:tg://openmessage\?user_id=|https?://t\.me/)
				(\d+)
				"[^>]*>
				[^<]+
				</a>
				\s*.—\s*
				(?:<strong>)?
				(\d+)
				(?:</strong>)?
				\s*🧬\s*(?:until|до)\s+
				(?:<code>)?
				(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})
				\s+UTC
				(?:</code>)?
				""",
				re.IGNORECASE | re.VERBOSE
			)
			
			# Регулярка для будь-яких згадок ID
			any_id_pattern = re.compile(
				r'href="(?:tg://(?:openmessage\?user_id=|user\?id=)|https?://t\.me/)(\d+)"',
				re.IGNORECASE
			)
			
			stop_dt = datetime.fromtimestamp(restart_timestamp, tz=timezone.utc)
			scanned_msgs = 0
			added_sqlite = 0
			unique_users = set()
			
			try:
				async for m in client.iter_messages(target_chat, from_user=6333102398):
					if m.date < stop_dt:
						break
						
					scanned_msgs += 1
					msg_ts = int(m.date.timestamp())
					
					if m.raw_text and m.entities:
						html_text = utils.sanitize_parse_mode('html').unparse(m.raw_text, m.entities)
						
						raw_ids = any_id_pattern.findall(html_text)
						valid_ids = [
							int(uid) for uid in raw_ids 
							if int(uid) >= 100000 and int(uid) not in (my_id, 6333102398, 1124824021)
						]
						
						if not valid_ids:
							continue
							
						unique_users.update(valid_ids)
						parsed_bio_ids = set()
						
						# 1. Записи з відомим БІО
						for r in victims_pattern.finditer(html_text):
							u_id = int(r.group(1))
							if u_id < 100000 or u_id in (my_id, 6333102398, 1124824021):
								continue
							bio = int(r.group(2))
							parsed_bio_ids.add(u_id)
							
							if db_sqlite3:
								try:
									c.execute("""
										INSERT INTO avocado (user_id, when_int, bio_int, expr_int, expr_str)
										VALUES (?, ?, ?, 0, '0')
										ON CONFLICT(user_id) DO UPDATE SET
											when_int = excluded.when_int,
											bio_int = excluded.bio_int
										WHERE avocado.expr_int = 0 
											AND (avocado.bio_int = 1 AND excluded.bio_int > 1)
									""", (u_id, msg_ts, bio))
									if c.rowcount > 0:
										added_sqlite += 1
								except Exception:
									pass
									
							if db_pymysql:
								try:
									d.execute("""
										INSERT INTO `tg_bio_users` (`user_id`, `when_int`, `profit`)
										VALUES (%s, %s, %s)
										ON DUPLICATE KEY UPDATE
											when_int = IF(profit = 1 AND VALUES(profit) > 1, VALUES(when_int), when_int),
											profit = IF(profit = 1 AND VALUES(profit) > 1, VALUES(profit), profit)
									""", (u_id, msg_ts, bio))
								except Exception:
									pass
						
						# 2. Решта знайдених ID (пишемо як одинички)
						for u_id in set(valid_ids):
							if u_id in parsed_bio_ids:
								continue
								
							if db_sqlite3:
								try:
									c.execute("""
										INSERT OR IGNORE INTO avocado (user_id, when_int, bio_int, expr_int, expr_str)
										VALUES (?, ?, 1, 0, '0')
									""", (u_id, msg_ts))
									if c.rowcount > 0:
										added_sqlite += 1
								except Exception:
									pass
									
							if db_pymysql:
								try:
									d.execute("""
										INSERT IGNORE INTO `tg_bio_users` (`user_id`, `when_int`, `profit`)
										VALUES (%s, %s, 1)
									""", (u_id, msg_ts))
								except Exception:
									pass
					
					# Раз на 200 повідомлень фіксуємо транзакцію та оновлюємо прогрес у повідомленні
					if scanned_msgs % 200 == 0:
						if db_sqlite3:
							conn.commit()
						if db_pymysql:
							con.commit()
						try:
							await event.edit(
								f'🔍 Сканую `{target_chat}`...\n'
								f'📨 Перевірено: {scanned_msgs} | 👥 Знайдено: {len(unique_users)}'
							)
						except Exception:
							pass
						await asyncio.sleep(0.5)
				
				# Фінальний коміт і оптимізація
				if db_sqlite3:
					conn.commit()
					optimize()
				if db_pymysql:
					con.commit()
				
				res_msg = (
					f'✅ Лайт-скан завершено!\n'
					f'💬 Чат: `{target_chat}`\n'
					f'📨 Перевірено повідомлень: {scanned_msgs}\n'
					f'👥 Унікальних гравців: {len(unique_users)}\n'
					f'🆕 Додано / оновлено в SQLite: {added_sqlite}'
				)
				print(res_msg)
				try:
					await event.edit(res_msg)
				except Exception:
					pass
					
			except Exception as e:
				err_msg = f'❌ Помилка під час сканування `{target_chat}`: {e}'
				print(err_msg)
				try:
					await event.edit(err_msg)
				except Exception:
					pass
			finally:
				scn_run = False
		
		########################################################################
		
		@client.on(events.NewMessage(outgoing=True, pattern=r'^\.upd$'))
		async def cmd_upd(event):
			import urllib.request
			import urllib.error
			import zipfile
			import socket
			
			if not db_sqlite3:
				await event.edit('❌ SQLite вимкнено в конфігу.')
				return
			
			# Визначаємо папку: для Termux туди ж де конфіг, для інших — поруч
			work_dir = default_directory if (is_termux and default_directory) else '.'
			zip_path = os.path.join(work_dir, '0.zip')
			db0_path = os.path.join(work_dir, '0.sqlite')
			
			# Попередньо видаляємо старий 0.zip, якщо він уже є
			if os.path.exists(zip_path):
				try:
					os.remove(zip_path)
				except Exception as e:
					await event.edit(f'❌ Не вдалося видалити старий 0.zip: {e}')
					return
			
			await event.edit('⏳ Завантажую 0.zip...')
			
			# Функція завантаження для запуску без блокування бота
			def download_zip():
				req = urllib.request.Request(
					bio_0_url,
					headers={'User-Agent': 'Mozilla/5.0'}
				)
				with urllib.request.urlopen(req, timeout=20) as resp, open(zip_path, 'wb') as out_f:
					shutil.copyfileobj(resp, out_f)
			
			try:
				loop = asyncio.get_running_loop()
				await loop.run_in_executor(None, download_zip)
			except urllib.error.HTTPError as e:
				if e.code == 404:
					await event.edit('❌ Файл 0.zip не знайдено на сервері (404).')
				else:
					await event.edit(f'❌ Помилка сервера HTTP {e.code}: {e.reason}')
				return
			except urllib.error.URLError as e:
				await event.edit(f'❌ Хост недоступний або немає з\'єднання: {e.reason}')
				return
			except (socket.timeout, TimeoutError):
				await event.edit('❌ Хост не відповідає (перевищено час очікування).')
				return
			except Exception as e:
				await event.edit(f'❌ Помилка завантаження: {e}')
				return
			
			await event.edit('📦 Розпаковую 0.sqlite...')
			
			try:
				with zipfile.ZipFile(zip_path, 'r') as zf:
					if '0.sqlite' not in zf.namelist():
						await event.edit('❌ Усередині архіву 0.zip немає файлу 0.sqlite.')
						return
					# Розпаковуємо з заміною існуючого 0.sqlite
					with zf.open('0.sqlite') as src_f, open(db0_path, 'wb') as dst_f:
						shutil.copyfileobj(src_f, dst_f)
			except zipfile.BadZipFile:
				await event.edit('❌ Завантажений 0.zip пошкоджений або не є архівом.')
				return
			except Exception as e:
				await event.edit(f'❌ Помилка розпакування: {e}')
				return
			
			await event.edit('🔄 Імпортую нових пацієнтів у базу...')
			
			added_sqlite = 0
			total_in_zero = 0
			
			try:
				src_conn = sqlite3.connect(db0_path)
				src_cur = src_conn.cursor()
				src_cur.execute(
					"SELECT user_id, when_int, bio_int FROM avocado WHERE user_id >= 100000 AND when_int >= ?",
					(restart_timestamp,)
				)
				rows = src_cur.fetchall()
				src_conn.close()
				total_in_zero = len(rows)
				
				for u_id, w_int, b_int in rows:
					u_id = int(u_id)
					w_int = int(w_int)
					b_int = int(b_int)
					
					if u_id == my_id or u_id in (6333102398, 1124824021):
						continue
					
					# Додаємо як чужого (expr_int = 0). Якщо юзер вже є як чужий — оновлюємо свіжішою датою або реальним біо
					c.execute("""
						INSERT INTO avocado (user_id, when_int, bio_int, expr_int, expr_str)
						VALUES (?, ?, ?, 0, '0')
						ON CONFLICT(user_id) DO UPDATE SET
							when_int = excluded.when_int,
							bio_int = excluded.bio_int
						WHERE avocado.expr_int = 0
							AND (excluded.when_int > avocado.when_int OR (avocado.bio_int = 1 AND excluded.bio_int > 1))
					""", (u_id, w_int, b_int))
					
					if c.rowcount > 0:
						added_sqlite += 1
					
					# Паралельно підливаємо в загальну таблицю MySQL, якщо увімкнено
					if db_pymysql:
						try:
							d.execute("""
								INSERT INTO `tg_bio_users` (`user_id`, `when_int`, `profit`)
								VALUES (%s, %s, %s)
								ON DUPLICATE KEY UPDATE
									profit = IF(VALUES(when_int) > when_int OR (profit = 1 AND VALUES(profit) > 1), VALUES(profit), profit),
									when_int = IF(VALUES(when_int) > when_int OR (profit = 1 AND VALUES(profit) > 1), VALUES(when_int), when_int)
							""", (u_id, w_int, b_int))
						except Exception:
							pass
				
				conn.commit()
				optimize()
				if db_pymysql:
					con.commit()
					
			except Exception as e:
				await event.edit(f'❌ Помилка читання/імпорту з 0.sqlite: {e}')
				return
			
			res_msg = (
				f'✅ Базу успішно оновлено!\n'
				f'📥 Записів у 0.sqlite: {total_in_zero}\n'
				f'🆕 Додано / оновлено в базі: {added_sqlite}'
			)
			print(res_msg)
			try:
				await event.edit(res_msg)
			except Exception:
				pass
		
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
			<code>.bf</code> – атака 10 цілей в ЛС
			<code>.scn</code> – скан чату в базу
			<code>.upd</code> – додати в базу +1
			
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
			print ('✅ 𝐏𝐎𝐍𝐆!')
			# Say "𝐏𝐎𝐍𝐆!",delete messages.
			m = await event.reply('𝐏𝐎𝐍𝐆!')
			await asyncio.sleep(random.uniform(4,8))
			await client.delete_messages(event.chat_id, [event.id, m.id])
		
		########################################################################
		
		if get_config_key("farm") and ch_id<0:
			await ферма()
		
		########################################################################
		
		await client.run_until_disconnected()
		
		########################################################################
		
asyncio.run(main())
