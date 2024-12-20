# -*- coding: utf-8 -*-
# https://docs-python.ru/packages/telegram-klient-telethon-python/	<-info

import asyncio

from datetime import datetime, timedelta
# from telethon.sync import TelegramClient
from telethon import TelegramClient, events, functions, types, utils

import os
import re
import random
import time
import json

#import pymysql
#import pymysql.cursors

import sqlite3

import typing

if os.name == 'nt':
	import win32api

sessdb = 'tl-ub' # назва бази сесії telethon
default_directory = '' # "робоча папка" бота
CONFIG_PATH = "conf.json"	# main config file
noeb_file = "noeb.json"		# кого ненада заражать айдішки

is_termux = os.environ.get('TERMUX_APP__PACKAGE_NAME') or os.environ.get('TERMUX_APK_RELEASE')

treat_as_true = ('true','1','t','y','yes','yeah','yup')# все інше False

if is_termux:
	import sys
	# майже все що для термукса я вкрав з форка бота.
	print('Termux detected, checking permissions...')
	print('Prevent killing termux by android, getting wakelock...')
	os.system('termux-wake-lock')
	print('This can cause battery drain!')
	if (os.environ.get('TERMUX_APP__APK_RELEASE') or os.environ.get('TERMUX_APK_RELEASE')) not in ('F_DROID', 'GITHUB'):
		print('You use not f-droid/github apk release, it may have problems...')
		print('F-droid termux release here: https://f-droid.org/en/packages/com.termux/')
		print('Github termux release here: https://github.com/termux/termux-app/releases')
	if float(os.environ.get('TERMUX_VERSION')[:5]) < 0.118:
		print('You use old version of termux, highly recommended that you update to v0.119.0 or higher ASAP for various bug fixes, including a critical world-readable vulnerability')
	if os.access('/sdcard', os.W_OK):
		print('✅ дозвіл на запис надано')
		default_directory = '/sdcard/ub4tg'
		os.system(f'mkdir -p {default_directory}')
		CONFIG_PATH = f'{default_directory}/conf.json' # положить файл в доступну без рута теку.
		noeb_file = f'{default_directory}/{noeb_file}' # положить файл в доступну без рута теку.
		#sessdb = f'{default_directory}/{sessdb}' # * спершу я думав просто положить в доступну, 
		#Але тоді буде проблемно запускать кілька копій бота з телефону з різними авторизаціями, 
		#В тому плані, що прийшлось би редагувать код, але тоді мінус оновлення через git pull, 
		#Тому хай валяється рядом з ботом. так можна просто копіювать і не редагуючи код запуск
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
	'a_404_p': a_404_p,
	'farm': False,
	'mine': False,
	'i2a': False,
	'a_h': a_h,
	'ch_id': 0
	}
	
	with open(CONFIG_PATH, "w", encoding="utf-8") as configfile:
		json.dump(new_config, configfile,ensure_ascii=False, indent='	')

with open(CONFIG_PATH, "r", encoding="utf-8") as configfile:
	#from types import SimpleNamespace
	config = json.load(configfile)
	print('✅ config loaded')
	
	api_id = int(config['api_id'])
	api_hash = config['api_hash']
	
	db_pymysql = bool(config['db_pymysql'] or False)
	db_sqlite3 = bool(config['db_sqlite3'] or True)
	
	a_404_p = bool(config['a_404_p'] or False)
	ch_id = int(config['ch_id'] or 0)  # id чата
	mine= bool(config['mine'] or False)# вмикать майн?

########################################################################

bf_mode='Normal'# dnt edit this. :Normal|Slow|Fast|Turbo # is beta...
bf_run = False	# dnt edit this. 

ostalos_pt=10	# осталось. буде мінятись. 
rs_min= 11	# інтервал. буде мінятись. 
rs_max=3600	# інтервал. буде мінятись. 

irises = [707693258,5137994780,5226378684,5443619563,5434504334]

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

try:
	#noeb_file = "noeb.json"
	with open(noeb_file, "r") as read_file:
		noeb = json.load(read_file)
except:
	noeb =[707693258,5137994780,5226378684,5443619563,5434504334,6333102398]
	with open(noeb_file, "w", encoding="utf-8") as write_file:
		json.dump(noeb, write_file,ensure_ascii=False, indent='	')

########################################################################

async def main():
	async with TelegramClient(sessdb,api_id,api_hash,timeout=300) as client:
		client.parse_mode="HTML"
		print('User-Bot started')
		me= await client.get_me()
		my_id = int(me.id)
		my_fn = me.first_name
		print(my_id)
		
		if os.name == 'nt':
			win32api.SetConsoleTitle(f'{my_id}')
		
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
			d.execute('''CREATE TABLE IF NOT EXISTS `tg_iris_zarazy` (
			`when_int` int(11) unsigned NOT NULL DEFAULT '0',
			`who_id` bigint(20) unsigned NOT NULL DEFAULT '0',
			`user_id` bigint(20) unsigned NOT NULL DEFAULT '0',
			`u_link` varchar(500) NOT NULL DEFAULT '',
			`bio_str` varchar(11) NOT NULL DEFAULT '1',
			`bio_int` int(11) unsigned NOT NULL DEFAULT '1',
			`expr_int` int(11) unsigned NOT NULL DEFAULT '0',
			`expr_str` varchar(11) NOT NULL DEFAULT '0',
			UNIQUE KEY `UNIQUE` (`who_id`,`user_id`)
			);''');
			con.commit()
			d.execute('''CREATE TABLE IF NOT EXISTS `tg_bio_attack` (
			`from_infect` int(11) unsigned NOT NULL DEFAULT '0',
			`who_id` bigint(20) unsigned NOT NULL DEFAULT '0',
			`user_id` bigint(20) unsigned NOT NULL DEFAULT '0',
			`profit` int(11) unsigned NOT NULL DEFAULT '1',
			`until_infect` int(11) unsigned NOT NULL DEFAULT '0',
			`until_str` varchar(11) NOT NULL DEFAULT '0',
			UNIQUE KEY `UNIQUE` (`who_id`,`user_id`)
			);''');
			con.commit()
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
			c.execute('''CREATE TABLE IF NOT EXISTS zarazy	(
			user_id	INTEGER NOT NULL DEFAULT 0 UNIQUE,
			when_int	INTEGER NOT NULL DEFAULT 0,
			bio_str	VARCHAR NOT NULL DEFAULT 1,
			bio_int	INTEGER NOT NULL DEFAULT 1,
			expr_int	INTEGER NOT NULL DEFAULT 0,
			expr_str	VARCHAR NOT NULL DEFAULT 0
			)''');
			conn.commit()
			c.execute('''CREATE TABLE IF NOT EXISTS avocado	(
			user_id	INTEGER NOT NULL DEFAULT 0 UNIQUE,
			when_int	INTEGER NOT NULL DEFAULT 0,
			bio_int	INTEGER NOT NULL DEFAULT 1,
			expr_int	INTEGER NOT NULL DEFAULT 0,
			expr_str	VARCHAR NOT NULL DEFAULT 0
			)''');
			conn.commit()
		
		if mine:
			await client.send_message(6333102398,'Майн')
		
		####################################################################
		
		async def get_id(url):
			user_id = 0
			if "tg://openmessage?user_id=" in url:
				user_id = int(re.findall(r'user_id=([0-9]+)',url)[0])
				#print(user_id)# А тут розкоментувать якщо нада бачить
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
					try:
						user_entity = await client.get_entity(url)
						if user_entity.id:
							user_id = int(user_entity.id)
							user_fn = user_entity.first_name or ''
							print(f'ok:{url}/@{user_id}')
							if db_pymysql:
								try:
									d.execute("INSERT INTO `tg_users_url` (`when_int`,`user_id`,`u_link`,`f_name`) VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE user_id = VALUES (user_id),u_link = VALUES (u_link),f_name = VALUES (f_name),when_int = VALUES (when_int);", (int(time.time()),int(user_id),str(url),str(user_fn))); con.commit()
								except Exception as Err:
									print(f'E:{Err}')
					except Exception as Err:
						print(f'E:{Err}')
						#pass
			return user_id
		
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
						return response
		
		####################################################################
		
		
		@client.on(events.NewMessage(outgoing=True,pattern=r'\.п'))
		async def cmd_п(event):
			mess = event.message
			text = mess.raw_text
			if text =='.п' or text=='.патоген':
				#FIX! А то спрацьовувало на .п(ередать,овысить,огладить,,,,,,,%)
				l_r = await message_q( # отправляет сообщение боту и возвращает
				f"/лаб в лс",
				5443619563,
				mark_read=True,
				delete=False,
				)
				h=utils.sanitize_parse_mode('html').unparse(l_r.message,l_r.entities)
				lab_lines = h.splitlines() # текст с лабой, разбитый на строки
				new = ""
				if "🔬 Досье лаборатории" not in lab_lines[0]:
					pass
				else:
					
					for i in lab_lines: # цикл for по всем строкам в тексте лабы
						if "🧪 Готовых патогенов:" in i:
							s = i.replace("🧪 Готовых патогенов:", "🧪 ")
							s = s.replace("из", "із")
							new+=f'{s}\n' # add \n

						if "☣️ Био-опыт:" in i:
							s = i.replace("☣️ Био-опыт:", "☣️ ")
							new+=f'{s}\n' # add \n
						if "🧬 Био-ресурс:" in i:
							s = i.replace("🧬 Био-ресурс:", "🧬 ")
							new+=f'{s}\n' # add \n

						if "❗️ Руководитель в состоянии горячки ещё" in i:
							s = i.replace("❗️ Руководитель в состоянии горячки ещё", "🤬 ")
							new+=f'{s}\n' # add \n
						if "вызванной болезнью" in i:
							#	❗️ Руководитель в состоянии горячки, вызванной болезнью «%s», ещё 
							#s = i.replace("❗️ Руководитель в состоянии горячки, вызванной болезнью ", "🤬 ")
							b = re.findall(r'вызванной болезнью «(.+)»',i)[0]#назва тої хєрні якою заразили
							s = i.replace(f"❗️ Руководитель в состоянии горячки, болезнью «{b}», ещё ", 
							f"🤬 <code>{b}</code>\n⏳ ")# копіпабельно для пошуку
					if not 'горячки' in l_r.message:
						new+='✅ ok\n'
					await event.edit(new) # ред.
		
		
		####################################################################
		
		
		@client.on(events.NewMessage(pattern='.*йобнув.*|.*подверг(ла)?.*|.*infected.*|.*сикди.*|.*насрал.*|.*выебал.*|.*за допомогою довіреності.*|.*при помощи.*'))
		async def infect(event):
			# хто там кого того
			m = event.message
			t = m.raw_text
			if m.sender_id !=6333102398 and m.sender_id not in irises:
				# зараз підтримуються лише Авокадо & Іріс.
				pass
			elif len(m.entities) > 1:
				h= utils.sanitize_parse_mode('html').unparse(t,m.entities)
				r= re.findall(r'<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">.*</a> (йобнув|подверг|infected|сикди|насрал|выебал|за допомогою|при помощи|by authorization).+<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">',h)
				if r:
					#print(h)
					exp_int=1
					experience=1
					u1url=r[0][0]
					u2url=r[0][2]
					u1id = await get_id(u1url)
					u2id = await get_id(u2url)
					when=int(datetime.timestamp(m.date))
					days=int(re.sub(r' ','',re.findall(r' (на|for|ещё) ([0-9\ ]+) (д|d).*', t)[0][1]))
					a=datetime.fromtimestamp(when)+timedelta(days=int(days), hours=3)
					do_int=datetime.timestamp(a)
					do_txt=str(a.strftime("%d.%m.%y"))
					
					if m.sender_id in irises:
						experience=re.findall(r"\+([0-9\.\,k]+) био-опыта", t)[0]
					if m.sender_id==6333102398:
						experience=re.findall(r"([☣️🧬🎄🥰🍖]).+: ([0-9\.\,k]+).+ \|",t)[0][1]
						
					
					if ',' in experience:
						experience=re.sub(r',', r'.',experience)
					if 'k' in experience:
						exp_int=int(float(re.sub('k', '',experience)) * 1000)
					else:
						exp_int=int(experience)
					
					if m.sender_id in irises:
						if 'Объект ещё не подвергался заражению вашим патогеном' in event.raw_text:
							exp_int=int(re.sub(r' ','',re.findall(r'по ([0-9\ ]+) ед.*',event.raw_text)[0]))
							
						if u1id > 0 and u2id > 0 and u1id != u2id and db_pymysql:
							try:
								d.execute("INSERT INTO `tg_iris_zarazy` (`who_id`, `user_id`, `when_int`, `bio_str`, `bio_int`, `expr_int`, `expr_str`, `u_link`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE when_int=VALUES (when_int),bio_str=VALUES (bio_str),bio_int=VALUES (bio_int),expr_int=VALUES (expr_int),expr_str=VALUES (expr_str),u_link = VALUES (u_link);", (int(u1id),int(u2id),int(when),str(experience), int(exp_int), int(datetime.timestamp(a)),str(do_txt),str(u2url))); con.commit()
								#print(f"\nINSERT INTO .... ON DUPLICATE KEY UPDATE # [@{u1id}] => [@{u2id}]\n")
							except Exception as Err:
								print(f'err: {Err} /localhost')
								# pass
						print(f'''🦠 {u1url} [@{u1id}] подверг(ла) {u2url} [@{u2id}] +{experience}''')# показать

					if m.sender_id==6333102398 and u1id > 0 and u2id > 0:
						if u1id==my_id:
							global ostalos_pt
							ostalos_pt=int(re.sub(r' ','',re.findall(r'\| Осталось: ([0-9\ ]+) шт.',t)[0]))
						if db_sqlite3 and u1id==my_id:
							try:
								c.execute("INSERT INTO avocado(user_id,when_int,bio_int,expr_int,expr_str) VALUES (?,?,?,?,?)",(int(u2id),int(when),int(exp_int),int(datetime.timestamp(a)),str(do_txt))); conn.commit()
							except:
								try:
									c.execute("UPDATE avocado SET when_int = :wh, bio_int = :xpi, expr_int = :end, expr_str = :do WHERE user_id = :z AND when_int <= :wh;", {"wh":int(when),"xpi":int(exp_int),"end":int(datetime.timestamp(a)),"do":str(do_txt),"z":int(u2id)}); conn.commit()
								except Exception as Err:
									print(f'err: {Err} avocado')
						elif db_sqlite3 and u2id!=my_id and u2id not in noeb:
							try:
								c.execute("INSERT INTO avocado(user_id,when_int,bio_int,expr_int) VALUES (?,?,?,?)", (int(u2id),int(when),int(exp_int),int(0))); conn.commit()# save not my pacients
							except:
								try:
									c.execute("UPDATE avocado SET when_int = :wh, bio_int = :xpi WHERE user_id = :z AND when_int < :wh AND expr_int < :wh;", {"wh":int(when),"xpi":int(exp_int),"z":int(u2id)}); conn.commit()
								except Exception as Err:
									print(f'err: {Err} avocado upd not my')
									# pass
						if db_pymysql:
							try:
								# from_infect 	who_id 	user_id 	profit 	until_infect 	until_str
								d.execute("INSERT INTO `tg_bio_attack` (`who_id`, `user_id`, `from_infect`, `profit`, `until_infect`, `until_str`) VALUES (%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE from_infect=VALUES (from_infect),profit=VALUES (profit),until_infect=VALUES (until_infect),until_str = VALUES (until_str);",(int(u1id),int(u2id),int(when),str(experience),int(datetime.timestamp(a)),str(do_txt))); con.commit()
								#print(f"\nINSERT INTO .... ON DUPLICATE KEY UPDATE # [@{u1id}] => [@{u2id}]\n")
							except Exception as Err:
								print(f'err: {Err} (tg_bio_attack)')
								# pass
							try:
								# user_id 	when 	profit
								d.execute("INSERT INTO `tg_bio_users` (`user_id`, `when_int`, `profit`) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE when_int=VALUES (when_int),profit=VALUES (profit);", (int(u2id),int(when),str(experience))); con.commit()
							except Exception as Err:
								print(f'err: {Err} (tg_bio_users)')
								# pass
						print(f'''🥑 @{u1id} подверг(ла) @{u2id} +{experience}''')# показать
		
		
		####################################################################
		
		
		@client.on(events.NewMessage(pattern='.+Резервная копия жертв'))
		async def bio_backup(event):
			m = event.message
			if m.sender_id == 6333102398 and event.chat_id == 6333102398:
				# відаправник Авокадо і це приват з Авокадо. перестрахувавсь?
				file_path = await m.download_media(file=f"{default_directory}")
				print(f'📃 backup file saved to {file_path}')
				added = 0
				victims = None
				raw_victims = None
				file_format = None
				with open(file_path, 'r') as stealed_backup:
					if file_path.lower().endswith('.json'):
						victims = json.load(stealed_backup)
						file_format = 'json'
						my_victims_ids = []
						added = 0
						for v in victims:
							u_id = int(v['user_id'])
							profit=int(v['profit'])
							when = int(v['from_infect'])
							expr = int(v['until_infect'])
							a=datetime.fromtimestamp(expr)
							do=str(a.strftime("%d.%m.%y"))
							if db_sqlite3:
								try:
									c.execute("INSERT INTO avocado(user_id,when_int,bio_int,expr_int,expr_str) VALUES (?,?,?,?,?)",(int(u_id),int(when),int(profit),int(expr),str(do))); conn.commit()
									print(f'''[@{u_id}] +{profit}''')# показать
									added+=1
								except:
									try:
										c.execute("UPDATE avocado SET when_int = :wh, bio_int = :xpi, expr_int = :expri, expr_str = :exprs WHERE user_id = :z AND when_int < :wh AND expr_int < :expri;", {"wh":int(when),"xpi":int(profit),"expri":int(expr),"exprs":str(do),"z":int(u_id)}); conn.commit()
									except Exception as Err:
										print(f'err: {Err} avocado backup')
										# pass
						del victims# free memory
						print(f'added: {added}')
		
		
		####################################################################
		
		
		@client.on(events.NewMessage(outgoing=True, pattern=r'\.biobackup$'))
		async def bio_steal_backup(event):
			mtime = int(datetime.timestamp(event.message.date))
			reply = await client.get_messages(event.peer_id, ids=event.reply_to.reply_to_msg_id)
			await event.edit('Downloading file...')
			file_path = await reply.download_media(file=f"{default_directory}")
			print(f'📃 backup file saved to {file_path}')
			victims = None
			raw_victims = None
			file_format = None
			with open(file_path, 'r') as stealed_backup:
				if file_path.lower().endswith('.json'):
					victims = json.load(stealed_backup)
					file_format = 'json'
					await event.edit('Processing json victims...')
				else:
					await event.edit('Format not supported.')
					return

			added = 0
			if file_format == 'json':
				for v in victims:
					if v['user_id']:
						#print(v)# захламляємо ?
						u_id = int(v['user_id'])
						profit=int(v['profit'] or 1)
						when = int(v['from_infect'] or 0)
						#expr = int(v['until_infect'])# А тут воно неважно, не свої ж.
						if u_id!=my_id and u_id not in noeb:
							try:
								c.execute("INSERT INTO avocado(user_id,when_int,bio_int,expr_int) VALUES (?,?,?,?)", (int(u_id),int(when),int(profit),int(0))); conn.commit()# save not my pacients
								added+= 1
							except:
								if profit > 1 and when > 0:
									# якщо є сенс оновлювати?
									try:
										c.execute("UPDATE avocado SET when_int = :wh, bio_int = :xpi WHERE user_id = :z AND when_int < :wh AND expr_int < :mtime;", {"wh":int(when),"xpi":int(profit),"mtime":int(mtime),"z":int(u_id)}); conn.commit()
									except Exception as Err:
										print(f'err: {Err} avocado backup json')
				ok=f'✅ Success added {added}'
				await event.edit(ok)
				print(ok)
			del my_victims_ids
			del victims  # free memory
			del raw_victims
		
		
		####################################################################
		
		
		@client.on(events.NewMessage(pattern='📝 .+'))
		async def iris_404(event):
			# iris off bio 31.12.24
			m = event.message
			t = m.raw_text
			if m.sender_id not in irises:
				pass
			elif (t=='📝 Заражать можно только пользователей' or t == '📝 Объект отказался от участия в игре' or 'Объект ещё не создал свою лабораторию' in t) and event.reply_to:
				reply = await client.get_messages(event.peer_id, ids=event.reply_to.reply_to_msg_id)
				t = reply.raw_text
				h= utils.sanitize_parse_mode('html').unparse(t,reply.entities)
				r= re.findall(r'([0-9]{6,10})',h)
				if r:
					# є ід юзера якого невдалось заразить
					uid=r[0] # ну власне ід
					if db_pymysql:
						try:
							#DELETE FROM `tg_iris_zarazy` WHERE `tg_iris_zarazy`.`user_id` = 0;
							con.query(f"DELETE FROM `tg_iris_zarazy` WHERE `user_id` = {uid};"); # нафіг.
						except Exception as Err:
							print(f'err: {Err} in DELETE FROM `tg_iris_zarazy` WHERE `user_id` = {uid}')
							# pass
					
		
		
		####################################################################
		
		
		@client.on(events.NewMessage(outgoing=True, pattern=r'\.biofuck$'))
		async def cmd_bf(event):			# крч акуратно з цим,вдруг шо я нічо
			global ch_id, bf_mode, bf_run, ostalos_pt
			m = event.message
			text = m.raw_text
			when=int(datetime.timestamp(m.date))
			msg='🤷' # якщо нема кого то жри рандом.
			c.execute(f"SELECT * FROM `avocado` WHERE expr_int < {when}"); 
			e_info=c.fetchall()
			count = len(e_info)
			if count < len(noeb)+2: # +2, так як, теоретично, там можуть всі вони + свій айді, тому жрать нема
				nema=f'🤷 рандом хавай.'
				await event.edit(nema) # ред.
				print(nema)
			elif bf_run:
				pong='✅ вже працює...' # ok.
				await event.edit(pong) # ред.
			elif event.chat_id > 0:
				pong='Алоу це не чат!' #wtf?!
				await event.edit(pong) # ред.
			else:
				bf_run = True
				pong='✅ погнали...'
				await event.edit(pong) # ред.
				if ch_id != event.chat_id:
					ch_id = event.chat_id
					save_config_key('ch_id',ch_id)
				print(f'✅ є {count} потенційних пацієнтів. спробуєм їх сожрать')
				for row in e_info:
					if row[0]!=my_id:				#	❌ Нельзя заразить самого себя.
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
							rs_max = 22
							bf_mode='Turbo'
						if os.name == 'nt':
							win32api.SetConsoleTitle(f'{my_id}#{bf_mode}')
						rs = float(random.uniform(rs_min,rs_max))# random
						eb = f'Биоеб {row[0]}' # повідомлення.
						print(f'{eb} and wait {rs}')
						m=await event.reply(eb)
						await asyncio.sleep(random.uniform(1.0001, 3.3))
						await client.delete_messages(event.chat_id,m.id)
						await asyncio.sleep(rs)
				bf_run = False	# dnt edit this.				# це якщо всьо уже.
				if os.name == 'nt':
					win32api.SetConsoleTitle(f'{my_id}')	# заголовк: мій_ід.
				
		
		####################################################################
		
		
		@client.on(events.NewMessage(pattern='.+Служба безопасности лаборатории'))
		# Организатор заражения: нада биоебнуть?
		async def iris_sb(event):
			# iris off bio 31.12.24
			m = event.message
			t = m.raw_text
			if m.sender_id in irises:
				i2a=get_config_key("i2a") # Iris => Avocado
				if a_404_p and i2a and len(m.entities) > 1:				
					h= utils.sanitize_parse_mode('html').unparse(t,m.entities)
					r= re.findall(r'Организатор заражения: <a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">',h)
					user_url=r[0]
					user_id = await get_id(user_url)
					if r and user_id!=my_id and user_id not in noeb:
						ch=f'.ч {user_url}'
						await asyncio.sleep(random.uniform(2,3))
						if ch_id == 0 or ch_id == event.chat_id:
							m = await event.reply(ch)
							kuda = event.chat_id
						else:
							kuda = ch_id
							m=await client.send_message(kuda,ch)
						await asyncio.sleep(random.uniform(2,5))
						await client.delete_messages(kuda, m.id)
					
		
		
		####################################################################
		
		
		@client.on(events.NewMessage(outgoing=True, pattern=r'\.ч(ек)?(_|\ )список$'))
		async def ch_list(event):
			reply = await client.get_messages(event.peer_id, ids=event.reply_to.reply_to_msg_id)
			when = int(datetime.timestamp(event.date))
			t = reply.raw_text
			h = utils.sanitize_parse_mode('html').unparse(t, reply.entities)  # HTML
			r = re.findall(r'<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">', h)
			for link in r:
				id = await get_id(link)
				if id > 0  and id!=my_id:
					rs_min = 2.01
					rs_max = 3.13
					ch = f'.ч {id}' # повідомлення.
					rs = float(random.uniform(rs_min,rs_max))
					print(f'{ch} and wait {rs}')
					m=await event.reply(ch)
					await asyncio.sleep(rs)
				
		
		####################################################################
		
		
		@client.on(events.NewMessage(pattern='⏱?🚫 Жертва'))
		async def infection_not_found(event):
			m = event.message
			if m.sender_id == 6333102398 and m.mentioned:
				if get_config_key("a_404_p"): # A_Click enabled?
					await asyncio.sleep(random.uniform(1.111,2.239))
					result = await client(functions.messages.GetBotCallbackAnswerRequest(  # src https://tl.telethon.dev/methods/messages/get_bot_callback_answer.html
					peer=m.peer_id,
					msg_id=m.id,
					game=False,  # idk why it works only when it false... 0_o
					data=m.reply_markup.rows[0].buttons[0].data
					))
					print('trying eat patient')
					if result.message:
						print(f'avocado says: {result.message}')
		
		
		####################################################################
		
		
		@client.on(events.NewMessage(pattern='🌡 У вас горячка вызванная'))
		async def need_h(event):
			m = event.message
			a_h=get_config_key("a_h") # читаємо із файла. 
			# ^ не баг, а фіча. Можливіть переключать в конфіґу без перезапуска
			if m.sender_id !=6333102398:
				pass
			elif a_h and m.mentioned:
				# нада хил
				ah = await message_q( # отправляет сообщение боту
				f"Хил",
				6333102398,
				mark_read=True,
				delete=False,
				)
			elif m.mentioned:
				# нада,но !a_h:
				global bf_mode,ostalos_pt
				bf_mode = 'Slow'
				ostalos_pt=1 # => 'Slow'. <= тобто 'костиль', да.
				
		
		####################################################################
		
		
		@client.on(events.NewMessage(pattern='👺 Чекай нових патогенів!'))
		async def need_p(event):
			m = event.message
			if m.sender_id !=6333102398:
				pass
			elif m.mentioned:
				global bf_mode,ostalos_pt
				bf_mode = 'Slow'
				ostalos_pt=0
		
		
		####################################################################
		
		
		@client.on(events.NewMessage(pattern='📉 Неудачная попытка майнинга!'))
		async def Неудачнаяпопыткамайнинга(event):
			c = event.chat_id
			m = event.message
			t = m.raw_text
			if m.sender_id == 6333102398 and (c == 6333102398 or c == ch_id):
				r=re.findall(r'⏱ Следующая попытка — через ([0-9]{1,3}) минут',t)
				Майн=get_config_key("mine")
				if r and Майн:
					print(t)
					if ch_id < 0:
						kuda = ch_id # слать в чат # навіть якщо неудача в лс бота. 
					else:
						kuda = 6333102398 # if!ch_id
					m = (int(r[0]) +1)*60	# +1 м
					await asyncio.sleep(m)	# ждем
					await client.send_message(kuda,'Майн')
		
		
		####################################################################
		
		
		@client.on(events.NewMessage(pattern='.+удалось намайнить'))
		async def удачнаяпопыткамайнинга(event):
			c = event.chat_id
			m = event.message
			Майн=get_config_key("mine")
			if m.sender_id == 6333102398 and (c == 6333102398 or (c == ch_id and m.mentioned)) and Майн:
				#save_config_key('mine',int(datetime.timestamp(m.date)))	# when
				if ch_id < 0:
					kuda = ch_id # слать в чат # навіть якщо удалось в лс бота. 
					if get_config_key("farm"):
						rs=random.uniform(2.2,3.3)	# random
						await asyncio.sleep(rs)	# ждем rs секунд
						await client.send_message(ch_id,'Ферма')
				else:
					kuda = 6333102398 # якщо чат не задано
				print(m.text) # показать в консолі текст
				rs=random.uniform(14402,14464)	# random
				await asyncio.sleep(rs)	# ждем rs секунд
				await client.send_message(kuda,'Майн')
		
		
		####################################################################
		
		
		@client.on(events.NewMessage(pattern=r'✅ (ВДАЛО|ЗАЧЁТ)'))
		async def ферма(event):
			m = event.message
			print(m.raw_text)
			if m.sender_id in irises:
				if ch_id < 0 and get_config_key("farm"):
					rs=random.uniform(3.53,5.11)	# random
					await asyncio.sleep(rs)	# ждем rs секунд
					await client.send_message(ch_id,'''.таймер 4 часа
.ферма''') # спробуєм ще так. \
						# бо з цими оновленнями у мене вони не працюють і по 4 часа.
				
		
		####################################################################
		
		
		@client.on(events.NewMessage(outgoing=True, pattern='.ping'))
		async def cmd_ping(event):
			# Say "pong!" whenever you send "!ping", then delete both messages
			m = await event.reply('pong!')
			await asyncio.sleep(5)
			await client.delete_messages(event.chat_id, [event.id, m.id])
		
		await client.run_until_disconnected()

asyncio.run(main())
