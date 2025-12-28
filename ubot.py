# -*- coding: utf-8 -*-

import asyncio

from datetime import datetime, timedelta
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

sessdb = 'tl-ub' # назва бази сесії telethon
default_directory = '' # "робоча папка" бота
CONFIG_PATH = "conf.json"	# main config file
noeb_file = "noeb.json"		# кого ненада заражать айдішки

is_termux = os.environ.get('TERMUX_APP__PACKAGE_NAME') or os.environ.get('TERMUX_APK_RELEASE')

termux_api = False # там нижче буде перевизначено якщо is_termux == True

treat_as_true = ('true','1','t','y','yes','yeah','yup')# все інше False

if is_termux:
	import sys
	# майже все що для термукса я вкрав з форка бота.
	print('Termux detected, checking permissions...')
	termux_api = os.system('termux-api-start') == 0 #	штука для сповіщеннь.
	if (os.environ.get('TERMUX_APP__APK_RELEASE') or os.environ.get('TERMUX_APK_RELEASE')) not in ('F_DROID', 'GITHUB'):
		print('You use not f-droid/github apk release, it may have problems...')
		print('F-droid termux release here: https://f-droid.org/en/packages/com.termux/')
		print('Github termux release here: https://github.com/termux/termux-app/releases')
	if float(os.environ.get('TERMUX_VERSION')[:5]) < 0.118:
		print('You use old version of termux, highly recommended that you update to v0.119.0 or higher ASAP for various bug fixes, including a critical world-readable vulnerability')
	if termux_api:
		print('✅ termux API work')
	if os.access('/sdcard', os.W_OK):
		print('✅ дозвіл на запис')
		default_directory = '/sdcard/ub4tg'
		os.system(f'mkdir -p {default_directory}')
		CONFIG_PATH = f'{default_directory}/conf.json' # в доступну без рута
		noeb_file = f'{default_directory}/{noeb_file}' # в доступну без рута
	else:
		print('permission denied to write on internal storage')
		print('trying get permission...')
		os.system('termux-setup-storage')
		print('Restart termux [Press CTRL+D or command "exit"]')
		sys.exit(0)

if not os.path.exists(CONFIG_PATH):
	api_id = int(input('enter api_id from https://my.telegram.org/ :'))
	api_hash = input('enter api_hash from https://my.telegram.org/ :')
	
	a_h = input('enable automatic use medkit? [y/n]: ').lower() in treat_as_true
	a_404_p = input('enable automatic bioeb if victim not found or expired? It will be trigger on "Жертва не найдена" [y/n]: ').lower() in treat_as_true
	
	new_config = {
	'api_id': api_id,
	'api_hash': api_hash,
	'db_pymysql': False,
	'db_sqlite3': True,
	'wakelock': False,
	'a_404_p': a_404_p,
	'farm': False,
	'mine': False,
	'a_h': a_h,
	'ch_id': 0
	}
	# api_id & api_hash - обов'язкові параметри; 
	# db_pymysql - чи юзать MySQL? (default: False); 
	# a_404_p - автоматично сожрать пацієнта якщо не знайдено; 
	# ch_id - ід чата де відбувається магія. виставиться само якщо був 0; 
	# wakelock - чи юзать wakelock (у мене від нього нема толку); 
	with open(CONFIG_PATH, "w", encoding="utf-8") as configfile:
		json.dump(new_config, configfile,ensure_ascii=False, indent='	')

with open(CONFIG_PATH, "r", encoding="utf-8") as configfile:
	#from types import SimpleNamespace
	config = json.load(configfile)
	print('✅ config loaded')
	
	api_id = int(config['api_id'])
	api_hash = config['api_hash']
	
	db_pymysql = bool(config['db_pymysql'] or False)
	db_sqlite3 = bool(True) # Always true; або змініть.
	
	a_404_p = bool(config['a_404_p'] or False)
	ch_id = int(config['ch_id'] or 0)  # id чата
	mine= bool(config['mine'] or False)# вмикать майн?
	
	if ch_id > 0:
		ch_id=0
		save_config_key('ch_id',ch_id)

########################################################################

bf_mode='Normal'# dnt edit this. :Normal|Slow|Fast|Turbo # is beta...
bf_run = False	# dnt edit this. 

ostalos_pt=10	# осталось. буде мінятись. 
rs_min= 11	# інтервал. буде мінятись. 
rs_max=3600	# інтервал. буде мінятись. 

my_days=10	# свій летал. виставиться коли бот "побачить".

f_time = 0	# остання успішна ферма була коли? 
f_next = 0	# остання успішна ферма +кд +хз

irises = [707693258,5137994780,5226378684,5434504334,5443619563]

########################################################################

def bfrnm(p=None):
	if p is None:
		return p
	r=re.findall(r'([0-9]+)_victims_([0-9]+)_([0-9]+)\.json',p)
	if r:
		id=r[0][1]#	чій бекап
		fn=re.sub(f'{r[0][0]}_victims_{r[0][1]}_{r[0][2]}',id,p)
		if os.path.exists(fn):
			os.remove(fn)
		shutil.copy2(p, fn)
		os.remove(p)
		return fn
	return

########################################################################

def ffnof(p=None):
	#FixFuckingNamesOfFiles
	if p is None:
		return p
	sho = ' ()' # ті символи є в бекапах з інших ботів.
	fn=re.sub(sho,'_',p) # ну так то вже ок?!
	if os.path.exists(fn):
		os.remove(fn)
	shutil.copy2(p, fn)
	os.remove(p)
	return fn

########################################################################

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

########################################################################

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

########################################################################
chts=[]
try:
	chts_file = "chts.json"		# чати:
	with open(chts_file, "r") as read_file:
		chts = json.load(read_file)
except:
	with open(chts_file, "w", encoding="utf-8") as write_file:
		json.dump(chts, write_file,ensure_ascii=False, indent='	')
########################################################################
noeb=[707693258,5137994780,5226378684,5434504334,5443619563,6333102398,7959200286]
try:
	#noeb_file = "noeb.json"
	with open(noeb_file, "r") as read_file:
		noeb = json.load(read_file)
except:
	with open(noeb_file, "w", encoding="utf-8") as write_file:
		json.dump(noeb, write_file,ensure_ascii=False, indent='	')

########################################################################

async def main():
	async with TelegramClient(sessdb,api_id,api_hash,timeout=300) as client:
		client.parse_mode="HTML"
		print('User-Bot started')
		me= await client.get_me()
		my_id = int(me.id)
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

		if db_pymysql:
			
			import pymysql
			import pymysql.cursors
			
			con = pymysql.connect(host='localhost',
			user='root',
			password='V3rY$tR0NgPaS$Sw0Rd',
			db='db',
			charset='utf8mb4',
			cursorclass=pymysql.cursors.DictCursor)
			d = con.cursor()
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
			d.execute('''CREATE TABLE IF NOT EXISTS `tg_bio_users` (
			`user_id` bigint(20) unsigned NOT NULL DEFAULT '0',
			`profit` int(11) unsigned NOT NULL DEFAULT '1',
			`virus` varchar(200) NOT NULL DEFAULT '',
			UNIQUE KEY `user_id` (`user_id`)
			);''');
			con.commit()
			d.execute('''CREATE TABLE IF NOT EXISTS `tg_users_url` (
			`user_id` bigint(20) unsigned NOT NULL DEFAULT '0',
			`when_int` int(11) unsigned NOT NULL DEFAULT '0',
			`u_link` varchar(64) NOT NULL DEFAULT '',
			`f_name` text NOT NULL,
			PRIMARY KEY (`user_id`),
			UNIQUE KEY (`u_link`)
			);''');
			con.commit()
		
		if db_sqlite3:
			conn = sqlite3.connect(f"{my_id}.sqlite")#покласти базу рядом?
			#conn = sqlite3.connect(f"D:\\Misc\\projects\\Python\\ub4tg_db\\{my_id}.sqlite")# Або повністю
			
			if is_termux:
				conn = sqlite3.connect(f"{default_directory}/{my_id}.sqlite")
			
			c = conn.cursor()
			
			c.execute('''CREATE TABLE IF NOT EXISTS avocado	(
			user_id	INTEGER NOT NULL DEFAULT 0 UNIQUE,
			when_int	INTEGER NOT NULL DEFAULT 0,
			bio_int	INTEGER NOT NULL DEFAULT 1,
			expr_int	INTEGER NOT NULL DEFAULT 0,
			expr_str	VARCHAR NOT NULL DEFAULT 0
			)''');
			conn.commit()
			
			# https://www.sqlite.org/pragma.html
			c.execute('PRAGMA optimize=0x10002'); conn.commit()
			c.execute('VACUUM'); conn.commit()
			def optimize():
				c.execute('PRAGMA optimize'); conn.commit()
				c.execute('VACUUM'); conn.commit()
		
		####################################################################
		
		async def get_id(url):
			user_id = 0
			if "tg://openmessage?user_id=" in url or "tg://user?id=" in url:
				user_id = int(re.findall(r'id=([0-9]+)',url)[0])
				#print(user_id)# розкоментувать якщо нада бачить
				return user_id
			if "t.me/" in url:
				if db_pymysql:
					try:
						d.execute("SELECT * FROM `tg_users_url` WHERE `u_link` = '%s' ORDER BY `when_int` DESC" % str(url)); 
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
		
		####################################################################
		
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
		
		####################################################################
		
		async def ферма(w:int=0):
			d = int(time.time())
			kuda = int(ch_id)
			if kuda==0:
				return
			global f_time,f_next
			if d < f_next:
				w= f_next - d
			w+= random.uniform(0,1)
			if int(w)>1:
				w=int(w)
				print(f'⏳ wait {w}')
			await asyncio.sleep(w)
			f = await message_q(
				text='Ферма',
				user_id=kuda,
				mark_read=True,
				delete=True)
			d = int(datetime.timestamp(f.date))
			if f.text:
				t = f.raw_text
				s = f.sender_id
				if s in irises:
					if '✅' in t:
						u = int(0)
						if f.entities:
							h= utils.sanitize_parse_mode('html').unparse(t,f.entities)
							r= re.findall(r'<a href="tg://user\?id=([0-9]+)">.+</a>',h)
							if r:
								u=int(r[0])
								if u==my_id:
									f_time = int(datetime.timestamp(f.date))
									f_next = int(f_time+14401)	# коли далі
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
						f_next=int(d+w)
						w=int(f_next-d)
						print(f"⏳ wait {w}")	# ждать w секунд
						try:
							await asyncio.sleep(random.uniform(1,3))
							await client.delete_messages(kuda,f.id)						
						except:
							pass
						
			return f
		
		####################################################################
		
		@client.on(events.NewMessage(incoming=True,from_users=6333102398,pattern=
		r'.*(йобнув|подверг(ла)?|infected|сикди|атаковал|выебал|инфицировал|напугала|насрал|нокаутировал|обмануло|оглушил|поставила|рассмешил|угостила).*'))
		async def infect(event):
			# хто там кого того
			m = event.message
			t = m.raw_text
			when = int(datetime.timestamp(m.date))
			if m.sender_id ==6333102398:
				if m.entities:
					if len(m.entities) > 1:
						h= utils.sanitize_parse_mode('html').unparse(t,m.entities)
						r= re.findall(r'<a href="tg://openmessage\?user_id=([0-9]+)">.*</a>.+<a href="tg://openmessage\?user_id=([0-9]+)">',h)
						p= re.findall(r'«(.+)»',t)	#	патогеном
						if r:
							#print(h)
							exp_int=1
							experience=1
							u1id =int(r[0][0])
							u2id =int(r[0][1])
							when=int(datetime.timestamp(m.date))
							days=int(re.sub(r' ','',re.findall(r'([0-9]+) (д|d).*',t)[0][0]))
							a=datetime.fromtimestamp(when)+timedelta(days=int(days), hours=3)
							do_int=datetime.timestamp(a)
							do_txt=str(a.strftime("%d.%m.%Y"))
							
							try:
								experience=re.sub(' ','',re.findall(
								r" ([0-9\.\,k\ ]+).+ \| ([\+|\-]([0-9\ ]+)|хз)",t)[0][0])
								e=re.findall(r'([0-9]+)',experience)
								if e==experience:
									exp_int=int(e)
							except Exception as Err:
								print(f'Err: {Err} (experience)')
							
							if ',' in experience:
								experience=re.sub(r',', r'.',experience)
							if 'k' in experience:
								exp_int=int(float(re.sub('k', '',experience)) * 1000)
							else:
								exp_int=int(experience)
							
							if u1id > 0 and u2id > 0:
								if u1id==my_id:
									global ostalos_pt,my_days
									ostalos_pt=int(re.sub(r' ','',re.findall(r'(Осталось|Remaining): ([0-9\ ]+)',t)[0][1]))
									my_days=int(days)	# свій летал. для списків (там не пише на скільки д.)
								
								if p:
									p=str(p[0])
								else:
									p=''
								
								if db_sqlite3:
									
									if u1id==my_id:
										try:
											c.execute("INSERT OR REPLACE INTO avocado (user_id,when_int,bio_int,expr_int,expr_str) VALUES (?,?,?,?,?)",
											(int(u2id),int(when),int(exp_int),int(do_int),str(do_txt))); conn.commit()
										except Exception as Err:
											print(f'err: {Err} avocado')
									elif u2id!=my_id and u2id not in noeb:
										try:
											c.execute("INSERT INTO avocado(user_id,when_int,bio_int,expr_int) VALUES (?,?,?,?)", (int(u2id),int(when),int(exp_int),int(0))); conn.commit()# save not my pacients
										except:
											try:
												c.execute("UPDATE avocado SET when_int = :wh, bio_int = :xpi WHERE user_id = :z AND expr_int < :wh;", {"wh":int(when),"xpi":int(exp_int),"z":int(u2id)}); conn.commit()
											except Exception as Err:
												print(f'err: {Err} avocado upd not my')
												#pass
									
								if db_pymysql:
									try:
										# date 	who_id 	user_id 	profit 	until_int 	until_str
										d.execute("INSERT INTO `tg_bio_attack` (`who_id`, `user_id`, `date`, `profit`, `until_int`, `until_str`) VALUES (%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE date=VALUES(date),profit=VALUES(profit),until_int=VALUES(until_int),until_str=VALUES(until_str);",(int(u1id),int(u2id),int(when),int(exp_int),int(do_int),str(do_txt))); con.commit()
									except Exception as Err:
										print(f'err: {Err} (tg_bio_attack)')
										#pass
									try:
										# user_id	profit	virus
										d.execute("INSERT INTO `tg_bio_users` (`user_id`, `profit`) VALUES (%s,%s) ON DUPLICATE KEY UPDATE profit=VALUES (profit);", (int(u2id),str(experience))); con.commit()
									except Exception as Err:
										print(f'err: {Err} (tg_bio_users)')
										#pass
									if p:
										#print(p)
										try:
											d.execute('''INSERT INTO `tg_bio_users` 
											(`user_id`, `virus`) VALUES (%s,%s) 
											ON DUPLICATE KEY UPDATE virus=VALUES(virus)''', 
											(int(u1id),str(p))); con.commit()
										except Exception as Err:
											print(f'err: {Err} (tg_bio_users)')
								
								print(f'🥑 @{u1id} подверг(ла) @{u2id} +{experience}')	# показать
		
		####################################################################
		
		@client.on(events.MessageEdited(incoming=True,
		pattern=r'🔬 Лаборатория .+ подвергла .+ списком:',
		from_users=6333102398))	#	Авокадо
		async def infect_list(event):
			m = event.message
			t = m.raw_text
			if m.entities:
				if len(m.entities) > 1:
					w=int(datetime.timestamp(m.date))	#	when_int
					h=utils.sanitize_parse_mode('html').unparse(t,m.entities)
					u=int(re.findall(r'Лаборатория <a href="tg://openmessage\?user_id=([0-9]+)">',h)[0])	#	who
					r=re.findall(r'<code>([0-9]+)</code> \| \+([0-9,k]+) оп.',h) # list of infect
					if u==my_id:
						global ostalos_pt
						ostalos_pt=int(re.sub(r' ','',re.findall(r'Осталось: ([0-9\ ]+) шт.',t)[0]))	# Осталось:
					for v in r:
						uid=int(v[0])
						bio=str(v[1])
						if ',' in bio:
							bio=re.sub(r',', r'.',bio)
						if 'k' in bio:
							bio=int(float(re.sub('k', '',bio)) * 1000)
						else:
							bio=int(bio)
						a=datetime.fromtimestamp(w)+timedelta(days=int(my_days))
						do_int=int(datetime.timestamp(a))
						do_txt=str(a.strftime("%d.%m.%Y"))
						if db_sqlite3:
							if u==my_id:
								try:
									c.execute("INSERT OR REPLACE INTO avocado (user_id,when_int,bio_int,expr_int,expr_str) VALUES (?,?,?,?,?)",
									(int(uid),int(w),int(bio),int(do_int),str(do_txt))); conn.commit()
								except Exception as Err:
									print(f'err: {Err} avocado')
							elif uid!=my_id and uid not in noeb:
								try:
									c.execute("INSERT INTO avocado(user_id,when_int,bio_int,expr_int) VALUES (?,?,?,?)", (int(uid),int(w),int(bio),int(0))); conn.commit()# save not my pacients
								except:
									try:
										c.execute("UPDATE avocado SET when_int = :wh, bio_int = :xpi WHERE user_id = :z AND expr_int < :wh;", {"wh":int(w),"xpi":int(bio),"z":int(uid)}); conn.commit()
									except Exception as Err:
										print(f'err: {Err} avocado upd not my')
										#pass
									
						if db_pymysql:
							if u==my_id:
								try:
									d.execute("INSERT INTO `tg_bio_attack` (`who_id`, `user_id`, `date`, `profit`, `until_int`, `until_str`) VALUES (%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE date=VALUES(date),profit=VALUES(profit),until_int=VALUES(until_int),until_str=VALUES(until_str);",(int(u),int(uid),int(w),int(bio),int(do_int),str(do_txt))); con.commit()
								except Exception as Err:
									pass
							try:
								# user_id	profit	virus
								d.execute("INSERT INTO `tg_bio_users` (`user_id`, `profit`) VALUES (%s,%s) ON DUPLICATE KEY UPDATE profit=VALUES (profit);", (int(uid),int(bio))); con.commit()
							except Exception as Err:
								print(f'err: {Err} (tg_bio_users)')
								#pass
						if u==my_id:
							print(f'🆔 {uid} ➕{bio}') # показать в консолі
					if db_sqlite3:
						optimize()
		
		####################################################################
		
		@client.on(events.NewMessage(pattern='.+Резервная копия жертв'))
		async def bio_backup(event):
			m = event.message
			s = m.sender_id
			if m.fwd_from:
				s=m.fwd_from.from_id.user_id
			if s == 6333102398: #	from Авокадо
				file=bfrnm(await m.download_media(file=default_directory))
				if file is None:
					return
				print(f'📃 backup file saved:{file}') # невлізало в рядок
				global bf_run	# будемо ставить на паузу
				br=bf_run	# запам'ятає чи запущено?
				id=re.findall(r'([0-9]+)\.json',file)[0]
				wh=int(datetime.timestamp(m.date))
				my=event.chat_id==6333102398
				count=0
				added=0
				updtd=0
				mysql=0
				errrs=0
				victims = None
				raw_victims = None
				file_format = None
				with open(file, 'r') as backup:
					if file.lower().endswith('.json'):
						victims = json.load(backup)
						file_format = 'json'
						if br:
							bf_run = False
							#print('paused')
						for v in victims:
							count+=1
							u_id = int(v['user_id'])
							profit=int(v['profit'] or 1)
							when = int(v['from_infect'])
							expr = int(0) # для несвоїх
							if my: # якщо це свій бекап
								expr = int(v['until_infect'])
								a=datetime.fromtimestamp(expr)
								do=str(a.strftime("%d.%m.%Y"))
							else:
								do=''
							if db_sqlite3:
								try:
									c.execute("INSERT INTO avocado(user_id,when_int,bio_int,expr_int,expr_str) VALUES (?,?,?,?,?)",(int(u_id),int(when),int(profit),int(expr),str(do))); conn.commit()
									print(f'''[@{u_id}] +{profit}''')# показать
									added+=1
								except:
									try:
										c.execute("UPDATE avocado SET when_int = :wh, bio_int = :xpi, expr_int = :expr, expr_str = :exprs WHERE user_id = :z AND expr_int < :whxpr;", {"wh":int(when),"xpi":int(profit),"expr":int(expr),"exprs":str(do),"z":int(u_id),"whxpr":int(expr if my else wh)}); conn.commit()
										updtd+=1
									except Exception as Err:
										print(f'err: {Err} avocado backup')
										errrs+=1
										# pass
							if db_pymysql:
								try:
									d.execute("INSERT INTO `tg_bio_attack` (`who_id`, `user_id`, `date`, `profit`, `until_int`, `until_str`) VALUES (%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE date=VALUES (date),profit=VALUES (profit),until_int=VALUES (until_int),until_str = VALUES (until_str);", (int(id),int(u_id),int(when),str(profit), int(expr),str(do))); con.commit()
									mysql+=1
								except Exception as Err:
									print(f'err: {Err} (tg_bio_attack) (backup)')
									errrs+=1
								try:
									query=f"INSERT IGNORE `tg_bio_users`(`user_id`) VALUES ('{u_id}');"
									con.query(query)
								except Exception as Err:
									print(f'err: {Err} (tg_bio_users)')
									errrs+=1
						del victims# free memory
						
						if db_sqlite3:
							optimize()
						
						if br:
							bf_run = True
						
						info = ''
						if count > 0:
							info = f'count: {count}'
						if added > 0:
							info = f'{info}\nadded: {added}'
						if errrs > 0:
							info = f'{info}\nerrrs: {errrs}'
						print(info)
						if len (info) > 0:
							if not my:
								if added > 0:
									try:
										await event.reply(info)
									except:
										pass
							if termux_api:
								os.system(
								f"termux-notification --title '{my_id}' --content '{info}'"
								)
		
		####################################################################
		
		@client.on(events.NewMessage(outgoing=True, pattern=r'\.fromtxt$'))
		# крч я вже тупо всіх сожрав, переходимо на текстовички (beta)
		async def cmd_bio_steal_backup_fromtxt(event):
			m = event.message
			if event.reply_to:
				reply = await client.get_messages(event.peer_id, ids=event.reply_to.reply_to_msg_id)
				try:
					await event.edit('Downloading file...')
				except Exception as wtf:
					print(wtf)	#	print
				file=ffnof(await reply.download_media(file=default_directory))
				if file is None:
					e = '⚠️ file is None?! (WTF?)' # хз чому так буває, але бува.
					try:
						await event.edit(e)
					except Exception as wtf:
							print(wtf)	#	print
					print(e)
					return
				print(f'📃 saved:{file}') # кудя?
				global bf_run	# будемо ставить на паузу
				br=bf_run	# запам'ятає чи запущено?
				print(f'📃 saved:{file}')
				victims = None
				raw_victims = None
				file_format = None
				with open(file,"r",encoding="utf-8") as f:
					if file.lower().endswith('.txt'):
						raw_victims = f.readlines()
						file_format = 'txt'
						print('✅ ok.')
						if br:
							bf_run = False
							#print('paused')
						try:
							await event.edit('📝 Processing raw txt victims...')
						except Exception as wtf:
							print(wtf)	#	print
					else:
						try:
							await event.edit('⚠️ Format 𝙣𝙤𝙩 supported.')
						except Exception as wtf:
							print(wtf)	#	print
						print('⚠️ 𝙣𝙤𝙩 ok.')
						return
					count=0
					added=0
					errrs=0
					for raw_v in raw_victims:
						if raw_v == '':
							continue
						user_id = re.findall(r'(tg://openmessage\?user_id=|@)([0-9]{2,10})',raw_v)
						if not user_id:
							continue
						user_id = int(user_id[0][1])
						profit = 1 # Або більше.
						if user_id:
							print(raw_v)
							count +=1
							id_user = user_id
							bio_int = profit
							when_int= 0
							if db_sqlite3:
								try:
									c.execute("INSERT INTO avocado(user_id,when_int,bio_int,expr_int) VALUES (?,?,?,?)", (int(id_user),int(0),int(bio_int),int(0))); conn.commit()# save not my pacients
									added+=1
								except Exception as Err:
									pass
									#errrs+=1
									# швидше за все просто вже є, тому це не помилка навіть.
					#rof
					
					if db_sqlite3:
						optimize()
						
						if br:
							bf_run = True
						
						info = ''
						if count > 0:
							info = f'count: {count}'
						if added > 0:
							info = f'{info}\nadded: {added}'
						if errrs > 0:
							info = f'{info}\nerrrs: {errrs}'
						print(info)
						if len (info) > 0:
							try:
								await event.reply(info)
							except:
								pass
							if termux_api:
								os.system(
								f"termux-notification --title '{my_id}' --content '{info}'"
								)
					del victims  # free memory
					del raw_victims
		
		####################################################################
		
		@client.on(events.NewMessage(pattern='👺 Юзер не знайдений!'))
		async def avocado_404(event):
			m = event.message
			if m.sender_id == 6333102398:
				if event.reply_to:
					reply = await client.get_messages(event.peer_id, ids=event.reply_to.reply_to_msg_id)
					t= reply.raw_text
					if reply.entities:
						t=utils.sanitize_parse_mode('html').unparse(t,reply.entities)
					r= re.findall(r'([0-9]{1,})',t)
					if r:
						# є ід юзера якого невдалось
						id=int(r[0]) # ну власне ід.
						global noeb
						if id not in noeb:
							noeb.append(id)
						if db_pymysql:
							try:
								con.query(f"DELETE FROM `tg_bio_attack` WHERE `user_id` = {id};"); # нафіг.
							except Exception as Err:
								print(f'err: {Err} in DELETE FROM `tg_bio_attack` WHERE `user_id` = {id}')
							try:
								con.query(f"DELETE FROM `tg_bio_users` WHERE `user_id` = {id};"); # нафіг.
							except Exception as Err:
								print(f'err: {Err} in DELETE FROM `tg_bio_users` WHERE `user_id` = {id}')
							
							try:
								con.query(f"DELETE FROM `tg_users_url` WHERE `user_id` = {id};");
							except Exception as Err:
								print(f'err: {Err} in DELETE FROM `tg_users_url` WHERE `user_id` = {id}')
						
						if db_sqlite3:
							try:
								c.execute("DELETE FROM avocado WHERE user_id = %d" % int(id)); conn.commit()
							except Exception as Err:
								print(f'err: {Err} in DELETE FROM avocado WHERE `user_id` = {id}')
		
		####################################################################
		
		@client.on(events.NewMessage(outgoing=True, pattern=r'\.biofuck$'))
		async def cmd_bf(event):			# крч акуратно з цим,вдруг шо я нічо
			global ch_id, bf_mode, bf_run, ostalos_pt
			m = event.message
			text = m.raw_text
			when = int(datetime.timestamp(m.date))
			await asyncio.sleep(random.uniform(0.4567,1))	# ждем
			def get_some_patients(limit:int=1000,when:int=time.time()):
				query=f"SELECT * FROM `avocado` WHERE expr_int <= {when} OR bio_int<=9 ORDER BY expr_int ASC, when_int ASC LIMIT {limit}"
				users=list(c.execute(query).fetchall())
				return users
			if bf_run:
				pong='✅ вже працює...' # ok.
				await event.edit(pong) # ред.
			elif event.chat_id > 0:
				pong='Алоу це не чат!' #wtf?!
				await event.edit(pong) # ред.
			elif ch_id == -4202608983 or ch_id == -4228309319:
				pong='👺 НЕ ТУТ!' # для того, хто плутає чати. 
				await event.edit(pong) # ред.
				return
			else:
				bf_run = True
				sndmsgs= 0#++
				pong='✅ погнали...'
				try:
					await event.edit(pong) # ред.
				except Exception as wtf:
					print(wtf)	#	print
				if ch_id != event.chat_id:
					ch_id = event.chat_id
					save_config_key('ch_id',ch_id)
				while bf_run:
					#	✅ погнали?
					count=int(c.execute(f"SELECT COUNT(*) FROM `avocado` WHERE expr_int<{when} OR bio_int==1").fetchone()[0])
					if count< len(noeb)+2: # так як, теоретично, там можуть всі вони + свій айді, тому жрать нема
						await asyncio.sleep(random.uniform(0.567,2))	#	чуток ждем
						bf_run = False
						if sndmsgs==0:
							info = '🤷 нема'
						else:
							info = f'✅ {sndmsgs}'
						try:
							await event.edit(info)
						except Exception as wtf:
							print(wtf) #print why?
						if os.name == 'nt':
							win32api.SetConsoleTitle(f'{my_id}')	# заголовк: мій_ід.
						elif is_termux and termux_api:
							os.system(
							f"termux-toast -b black -c green '{my_id}, {info}'"
							)
						bf_run = False
						print(info)
						break
					print(f'📃 є {count} потенційних пацієнтів. Пробуєм сожрать')
					e_info=get_some_patients(limit=int(random.randint(100,1000)))
					random.shuffle(e_info)	# перетасувать?
					for row in e_info:
						if ostalos_pt < 7:
							rs_min = 1000	# якщо осталось мало хай підзбираються.
							rs_max = 3600	# if Влад забрал у тебя 49 патогенов...
							bf_mode='Slow'	# тепер це лише для заголовка консолі.
						if ostalos_pt > 6:
							rs_min = 11
							rs_max = 99
							bf_mode='Normal'
						if ostalos_pt > 60:
							bf_mode='Fast'
							rs_max = 33
						if ostalos_pt > 90:
							rs_min = 3.333
							rs_max = 9.999
							bf_mode='Turbo'
						if os.name == 'nt':
							win32api.SetConsoleTitle(f'{my_id}#{bf_mode}')
						if row[0] not in noeb and row[0]!=my_id:
							#	👺 Неможна йобнути бота!
							#	❌ Нельзя заразить самого себя
							rs = float(random.uniform(rs_min,rs_max))# random
							eb = f'Биоеб {row[0]}' # повідомлення.
							if ostalos_pt > 90 or bf_mode=='Turbo':#одне і те ж.
								eb = f'Биоеб 10 {row[0]}' # повідомлення.
							print(f'⏳ {eb} and wait {rs}')
							try:
								m=await event.reply(eb)
								sndmsgs+=1	# рахуємо к-сть (надісланих)
								await asyncio.sleep(random.uniform(2.0001, 3.3))
								await client.delete_messages(event.chat_id,m.id)
								await asyncio.sleep(rs)
							except Exception as wtf:
								print(wtf) #why?
					print(f'✅ {sndmsgs}') # how
					optimize()
		
		####################################################################
		
		@client.on(events.NewMessage(outgoing=True, 
		pattern=r'.biofuck_(r|p|m|plus|minus|random)$'))
		async def cmd_bfrpm(event):	
			global ch_id, bf_mode, bf_run, ostalos_pt
			m = event.message
			text = m.raw_text
			if bf_run:
				pong='✅ вже працює...' # ok.
				await event.edit(pong) # ред.
			elif event.chat_id > 0:
				pong='Алоу це не чат!' #wtf?!
				await event.edit(pong) # ред.
			elif ch_id == -4202608983 or ch_id == -4228309319:
				pong='👺 НЕ ТУТ!' # для того, хто плутає чати. 
				await event.edit(pong) # ред.
				return
			else:
				bf_run = True
				bioeb = 'Биоеб'# message
				if 'p' in text:# p,plus
					bioeb = 'Биоеб +'
				if 'm' in text:# m,minus
					bioeb = 'Биоеб -'
				pong = f'✅ {bioeb}'
				await event.edit(pong) # ред.
				if ch_id != event.chat_id:
					ch_id = event.chat_id
					save_config_key('ch_id',ch_id)
				while bf_run:
					#	✅ погнали...
					if ostalos_pt < 7:
						rs_min = 1000	# якщо осталось мало хай підзбираються.
						rs_max = 3600	# if Влад забрал у тебя 49 патогенов...
						bf_mode='Slow'	# тепер це лише для заголовка консолі.
					if ostalos_pt > 6:
						rs_min = 11
						rs_max = 99
						bf_mode='Normal'
					if ostalos_pt > 60:
						bf_mode='Fast'
						rs_max = 33
					if ostalos_pt > 90:
						rs_min = 3.333	# це низький інтервал, але якщо патів дофіга
						rs_max = 7.777	# це низький інтервал, але якщо патів дофіга
						bf_mode='Turbo'
					if os.name == 'nt':
						win32api.SetConsoleTitle(f'{my_id} {bf_mode}')
					rs = float(random.uniform(rs_min,rs_max))# random
					print(f'⏳ {bioeb} and wait {rs}')
					m=await client.send_message(ch_id,bioeb)# message
					await asyncio.sleep(random.uniform(2.0001, 3.3))
					await client.delete_messages(event.chat_id,m.id)
					await asyncio.sleep(rs)
		
		####################################################################
		
		@client.on(events.NewMessage(outgoing=True, 
		pattern=r'\.biofuck(_| )stop$'))
		async def stop_bioeb(event):
			global bf_run
			if bf_run:
				bf_run = False
				info = '⏹ stop.'
			else:
				info = 'Не запущено.'
			await event.edit(info)  # ред
		
		####################################################################
		
		@client.on(events.NewMessage(from_users=6333102398,
		pattern=r'.+(Була|Была|Спроба|(П|п)опыт(о)?к(а)?)'))
		# Була|Была|Спроба|Попытка выебать|обмануть|...
		async def try_eb(event):
			m = event.message
			t = m.raw_text
			if m.entities:
				h= utils.sanitize_parse_mode('html').unparse(t,m.entities)
				p= re.findall(r'«(.+)»',t)	#	патогеном
				r= re.findall(
				r'(Аферист|Злочинець|Организатор.*|Планировщик.*|Порноактер): <a href="tg://openmessage\?user_id=(\d+)">',h)
				if r:
					u_id=int(r[0][1])
					if u_id!=my_id:
						if p:
							p=str(p[0])
						if db_sqlite3:
							try:
								c.execute("INSERT INTO avocado(user_id) VALUES (?)", 
								(int(u_id))); conn.commit()	#	try save from try.
							except:
								# Але швидше за все у базі вже є
								pass
						if db_pymysql:
							query=f"INSERT IGNORE `tg_bio_users`(`user_id`) VALUES ('{u_id}');"
							if p:
								try:
									d.execute('''INSERT INTO `tg_bio_users` 
									(`user_id`, `virus`) VALUES (%s,%s) 
									ON DUPLICATE KEY UPDATE virus=VALUES(virus)''', 
									(int(u_id),str(p))); con.commit()
								except Exception as Err:
									print(f'err: {Err} (tg_bio_users)')
							else:
								con.query(query)
		
		####################################################################
		
		@client.on(events.NewMessage(
		from_users=6333102398,
		pattern=r'Болезни игрока'))
		async def infect_list(event):
			m = event.message
			t = m.raw_text
			if m.entities:
				if len(m.entities) > 1:
					w=int(datetime.timestamp(m.date))	#	when_int
					h=utils.sanitize_parse_mode('html').unparse(t,m.entities)
					r=re.findall(r'<a href="tg://openmessage\?user_id=([0-9]+)">(.+)</a> \|',h) # list of infect
					for v in r:
						u=int(v[0])
						p=str(v[1])
						if db_pymysql:
							query=f"INSERT IGNORE `tg_bio_users`(`user_id`) VALUES ('{u}');"
							if p!='Неизвестный патоген':
								try:
									d.execute('''INSERT INTO `tg_bio_users` 
									(`user_id`, `virus`) VALUES (%s,%s) 
									ON DUPLICATE KEY UPDATE virus=VALUES(virus)''', 
									(int(u),str(p))); con.commit()
								except Exception as Err:
									print(f'err: {Err} (tg_bio_users)')
							else:
								con.query(query)
						if db_sqlite3:
							try:
								c.execute("INSERT INTO avocado(user_id) VALUES (?)", 
								(int(u_id))); conn.commit()
							except:
								# Але швидше за все у базі вже є
								pass
		
		####################################################################
		
		@client.on(events.NewMessage(
		from_users=6333102398,
		pattern=r'🦠 Жертвы игрока'))
		async def victims_list(event):
			m = event.message
			t = m.raw_text
			if m.entities:
				w=int(datetime.timestamp(m.date))	#	when_int
				h=utils.sanitize_parse_mode('html').unparse(t,m.entities)
				u=int(re.findall(r'<strong>🦠 Жертвы игрока </strong><a href="tg://openmessage\?user_id=([0-9]+)">.+</a>',h)[0])
				r=re.findall(r'<a href="tg://openmessage\?user_id=([0-9]+)">.+</a> \| \+([0-9\ ]+) \| до ([0-9\.]+)',h) # v,b,d
				for v in r:
					z=int(v[0])
					a=str(v[2]) # date '31.12.2024'
					b=int(re.sub(' ','',str(v[1])))
					d=int(datetime.timestamp(datetime.strptime(a,"%d.%m.%Y")))
					
					if db_sqlite3:
						if u==my_id:
							try:
								c.execute("INSERT OR REPLACE INTO avocado (user_id,when_int,bio_int,expr_int,expr_str) VALUES (?,?,?,?,?)",
								(int(z),int(w),int(b),int(d),str(a))); conn.commit()
							except Exception as Err:
								print(f'err: {Err} avocado')
						elif z!=my_id and z not in noeb:
							try:
								c.execute("INSERT INTO avocado(user_id,when_int,bio_int,expr_int) VALUES (?,?,?,?)", (int(z),int(w),int(b),int(0))); conn.commit()# save not my pacients
							except:
								try:
									c.execute("UPDATE avocado SET when_int = :wh, bio_int = :xpi WHERE user_id = :z AND expr_int < :wh;", {"wh":int(w),"xpi":int(b),"z":int(z)}); conn.commit()
								except Exception as Err:
									print(f'err: {Err} avocado upd not my')
									#pass

					if db_pymysql:
						
						try:
							query=f"INSERT INTO `tg_bio_attack` (`date`, `who_id`, `user_id`, `profit`, `until_int`, `until_str`) VALUES ('{w}', '{u}', '{z}', '{b}', '{d}', '{a}') ON DUPLICATE KEY UPDATE date=VALUES(date),profit=VALUES(profit),until_int=VALUES(until_int),until_str=VALUES(until_str);"; 
							con.query(query)
						except Exception as Err:
							print(f'err: {Err} (tg_bio_attack)')
							#pass
						try:
							con.query(f"INSERT INTO `tg_bio_users` (`user_id`, `profit`) VALUES ('{z}', '{b}') ON DUPLICATE KEY UPDATE profit=VALUES (profit);")
						except Exception as Err:
							print(f'err: {Err} (tg_bio_users)')
							#pass
					
					if u==my_id:
						print(f'🆔 {z} ➕{b}') # показать в консолі
				
				if db_sqlite3:
					optimize()
		
		####################################################################
		
		@client.on(events.NewMessage(
		from_users=6333102398,
		pattern=
		r'.+(Слетевшие игроки лаборатории|Список последних слетевших игроков)'))
		async def infect_list(event):
			m = event.message
			t = m.raw_text
			if m.entities:
				if len(m.entities) > 1:
					w=int(datetime.timestamp(m.date))	#	when_int
					h=utils.sanitize_parse_mode('html').unparse(t,m.entities)
					r=re.findall(r'<a href="tg://openmessage\?user_id=([0-9]+)">.+</a> \| ([0-9\ ]+)',h) # v,
					u=int(re.findall(r'«</strong><a href="tg://openmessage\?user_id=([0-9]+)">.+</a>',h)[0])
					count=0
					added=0
					mysql=0
					errrs=0
				for v in r:
					count+=1
					z=int(v[0])
					#b=int(re.sub(' ','',str(v[1]))) # інфа вобще неактуальна
					if db_sqlite3 and z!=my_id and z not in noeb:
						try:
							c.execute("INSERT INTO avocado(user_id,when_int,bio_int,expr_int) VALUES (?,?,?,?)", (int(z),int(0),int(1),int(0))); conn.commit()# save pacients
							added+=1
						except:
							pass
				#rof
				info = ''
				if count > 0:
					info = f'count: {count}'
					if added > 0:
						info = f'{info}\added: {added}'
					print(info)
		
		####################################################################
		
		@client.on(events.NewMessage(pattern='⏱?🚫 Жертва'))
		async def infection_not_found(event):
			m = event.message
			if m.sender_id == 6333102398 and m.mentioned:
				if get_config_key("a_404_p"): # A_Click enabled?
					await asyncio.sleep(random.uniform(1.111,2.239))
					result = await client(functions.messages.GetBotCallbackAnswerRequest(
					# src https://tl.telethon.dev/methods/messages/get_bot_callback_answer.html
					peer=m.peer_id,
					msg_id=m.id,
					game=False,  # idk why it works only when it false... 0_o
					data=m.reply_markup.rows[0].buttons[0].data
					))
					print('trying eat patient')
					if result.message:
						print(f'avocado says: {result.message}')
		
		####################################################################
		
		@client.on(events.NewMessage(pattern='.+ ЗАБРАЛ у тебя'))
		async def ЗАБРАЛ(event):
			m = event.message
			if m.sender_id ==6333102398:
				if m.mentioned or m.chat_id == 6333102398:
					r= re.findall(r'([0-9]{1,})',m.raw_text)
					if r:
						global ostalos_pt
						#print(m.raw_text)
						ostalos_pt-=int(r[0])
		
		####################################################################
		
		@client.on(events.NewMessage(pattern='.+ подогнал тебе'))
		async def подогнал(event):
			m = event.message
			if m.sender_id ==6333102398:
				if m.mentioned or m.chat_id == 6333102398:
					r= re.findall(r'([0-9]{1,2})',m.raw_text)
					if r:
						global ostalos_pt
						#print(m.raw_text)
						ostalos_pt+=int(r[0])
		
		####################################################################
		
		@client.on(events.NewMessage(pattern='🌡 У вас горячка вызванная'))
		async def need_h(event):
			m = event.message
			if m.sender_id==6333102398: 
				if m.mentioned or m.chat_id == 6333102398:
					if get_config_key("a_h"): # читаємо із файла. 
						ah = await message_q(f"Хил",6333102398,mark_read=True)
						print(ah.raw_text)
					else:
						global ostalos_pt
						ostalos_pt=1 # => 'Slow'. <= тобто 'костиль', да.
		
		####################################################################
		
		@client.on(events.NewMessage(incoming=True,from_users=6333102398,pattern=
		r'(👺|📛|⏱) (Чекай нових патогенів|Жди новых патогенов|Wait for new pathogens|гиждыллах, патогенляр йохду бле)!'))
		async def need_p(event):
			m = event.message
			if m.sender_id == 6333102398:
				if m.mentioned or m.chat_id == 6333102398:
					global bf_mode,ostalos_pt
					print(m.raw_text)
					bf_mode = 'Slow'
					ostalos_pt=0
					optimize()
		
		####################################################################
		
		@client.on(events.NewMessage(
		incoming=True,from_users=6333102398,
		pattern='👎🏻💔 Неудача!'))
		async def Неудачнаяпопыткамайнинга(event):
			c = event.chat_id
			m = event.message
			t = m.raw_text
			if m.chat_id == 6333102398:	# крч від неудачних будем лише в лс бота
				r=re.findall(r'Следующая попытка через ([0-9]{1,3}) минут',t)
				mine=get_config_key("mine")
				if r and mine:
					print(t)
					if ch_id < 0:
						kuda = ch_id # слать в чат
					else:
						kuda = 6333102398 # if!ch_id
					m = (int(r[0]) +1)*60	# +1 м
					await asyncio.sleep(m)	# ждем
					await client.send_message(kuda,'Майн')
		
		####################################################################
		
		@client.on(events.NewMessage(incoming=True,pattern=r'.+Удачная попытка майнинга.+'))
		async def mine_ok(event):
			c = event.chat_id
			m = event.message
			mine=get_config_key("mine")
			if m.sender_id == 6333102398 and (c == 6333102398 or (c == ch_id and m.mentioned)) and mine:
				#save_config_key('mine',int(datetime.timestamp(m.date)))	# when
				if ch_id < 0:
					kuda = ch_id # слать в чат # навіть якщо удалось в лс бота. 
				else:
					kuda = 6333102398 # якщо чат не задано
				print(m.text) # показать в консолі текст
				rs=random.uniform(7201,7222)	# random
				await asyncio.sleep(rs)	# ждем rs секунд
				await client.send_message(kuda,'Майн')
		
		####################################################################
		
		@client.on(events.NewMessage(incoming=True,pattern=r'✅ (ВДАЛО|ЗАЧЁТ)'))
		async def ферма_ВДАЛО(event):
			m = event.message
			t = m.raw_text
			u = 0 # OR id
			global f_time,f_next
			if m.sender_id in irises:
				if ch_id < 0:
					kuda = ch_id
				elif m.chat_id in irises:
					kuda = m.chat_id
			else:
				return
			if m.entities:
				h= utils.sanitize_parse_mode('html').unparse(t,m.entities)
				r= re.findall(r'<a href="tg://user\?id=([0-9]+)">.+</a>',h)
				if r:
					u=int(r[0])
			else:
				h=t
				#return
			if u==my_id:
				print(m.raw_text)
				f_time = int(datetime.timestamp(m.date))
				f_next = int(f_time+14401)	# коли далі
				f=await ферма(14401)	#	ждем + шлем
		
		####################################################################
		
		@client.on(events.NewMessage(outgoing=True, pattern=r'.reset$'))
		async def cmd_reset(event):
			# обнуляємо дати (наприклад після трансферу)
			if db_sqlite3: # А вона у нас завжди True
				try:
					c.execute("UPDATE avocado SET when_int = 0, expr_int = 0;"); conn.commit()
					c.execute('PRAGMA optimize'); conn.commit()
					c.execute('VACUUM'); conn.commit()
					await asyncio.sleep(1)
					try:
						await event.edit('жмяк /backup щоб зберегти у базі')	#	ред.
					except Exception as err:
						print(err) # показать
					await asyncio.sleep(1)
				except Exception as Err:
					print(f'err: {Err} in reset')
					await event.edit(Err)	#	ред.
		
		####################################################################
		
		@client.on(events.NewMessage(outgoing=True, 
		pattern=r'.(h(e)?lp|х(е)?лп)$'))
		async def cmd_help(event):
			help_message = f'''
			<blockquote>📃 код і є документація 😈</blockquote>
			
			<code>.ping</code> – "pong!", del.
			<code>.biofuck</code> – run 'биоеб'
			<code>.biofuck_r</code> – run 'биоеб'
			<code>.biofuck_p</code> – run 'биоеб +'
			<code>.biofuck_m</code> – run 'биоеб -'
			<code>.fromtxt</code> – import ids.txt
			<code>.reset</code> – set dates as '0'
			<code>.help</code> – <u>you are here</u>
			
			<code>https://github.com/S1S13AF7/ub4tg</code> – <a 
			href="https://github.com/S1S13AF7/ub4tg">code</a>;
			
			💬 <u>@misc_games</u>
			💬 <u>@ub4tg</u>
			'''
			await asyncio.sleep(random.uniform(0.3,1))
			await event.edit(help_message) # ред.
		
		####################################################################
		
		@client.on(events.NewMessage(outgoing=True, pattern='.ping'))
		async def cmd_ping(event):
			# Say "pong!" whenever you send "!ping", then delete both messages
			m = await event.reply('pong!')
			await asyncio.sleep(5)
			await client.delete_messages(event.chat_id, [event.id, m.id])
		
		####################################################################
		
		if get_config_key("farm") and ch_id<0:
			await ферма()
		
		####################################################################
		
		await client.run_until_disconnected()
		
		####################################################################
		
asyncio.run(main())
