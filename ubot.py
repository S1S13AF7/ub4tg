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
	if float(os.environ.get('TERMUX_VERSION')[:5]) < 0.118:
		print('You use old version of termux, highly recommended that you update to v0.119.0 or higher ASAP for various bug fixes, including a critical world-readable vulnerability')
	if termux_api:
		print('✅ termux API work')
	if os.access('/sdcard', os.W_OK):
		print('✅ дозвіл на запис')
		default_directory = '/sdcard/ub4tg'
		os.system(f'mkdir -p {default_directory}')
		CONFIG_PATH = f'{default_directory}/conf.json' # в доступну без рута
	else:
		print('permission denied to write on internal storage')
		print('trying get permission...')
		os.system('termux-setup-storage')
		print('Restart termux [Press CTRL+D or command "exit"]')
		sys.exit(0)

if not os.path.exists(CONFIG_PATH):
	api_id = int(input('enter api_id from https://my.telegram.org/ :'))
	api_hash = input('enter api_hash from https://my.telegram.org/ :')
	
	new_config = {
	'api_id': api_id,
	'api_hash': api_hash,
	'db_pymysql': False,
	'db_sqlite3': False,
	'wakelock': False,
	'farm': False,
	'ch_id': 0
	}
	# api_id & api_hash - обов'язкові параметри; 
	# db_pymysql - чи юзать MySQL? (default: False); 
	# ch_id - ід чата де відбувається магія. виставить в конфіґу; 
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
	db_sqlite3 = bool(config['db_sqlite3'] or False)
	
	ch_id = int(config['ch_id'] or 0)  # id чата
	farm= bool(config['farm'] or False)# вмикать фарм?
	
	if ch_id > 0:
		ch_id=0
		save_config_key('ch_id',ch_id)
		print('неправильний id чата')
	
################################################################################

irises = [707693258,5137994780,5226378684,5434504334,5443619563]

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
			d.execute('''CREATE TABLE IF NOT EXISTS `tg_bot_users` (
			`user_id` bigint(20) UNSIGNED NOT NULL DEFAULT '0',
			`reg_int` int(11) UNSIGNED NOT NULL DEFAULT '0',
			`f_name` text CHARACTER SET utf8mb4 NOT NULL DEFAULT '',
			PRIMARY KEY (`user_id`)
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
			except:
				pass
		
		#if db_sqlite3:
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
		
		async def ферма(w:int=0):
			kuda = int(ch_id)
			if kuda==0:
				return
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
			if f.text:
				t = f.raw_text
				s = f.sender_id
				if s in irises:
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
						#
						try:
							await asyncio.sleep(random.uniform(2,4))
							await client.delete_messages(kuda,f.id)					
						except:
							pass
						w=int(w)
						print(f'⏳ wait {w}')
						await asyncio.sleep(w)
						f = await message_q(
						text='Ферма',
						user_id=kuda,
						mark_read=True,
						delete=True)
			return f
		
		########################################################################
		
		@client.on(events.NewMessage(incoming=True,
		pattern=r'(✅|🔑) (ВДАЛО|ЗАЧЁТ|УСПІХ)'))
		async def ферма_ВДАЛО(event):
			m = event.message
			t = m.raw_text
			u = 0 # OR id
			д = int(time.time())
			if m.sender_id in irises:
				if ch_id < 0:
					kuda = ch_id
				elif m.chat_id in irises:
					kuda = m.chat_id
			else:
				return
			if m.date:
				д = max(int(datetime.timestamp(m.date)),int(time.time()))
			if m.entities:
				h= utils.sanitize_parse_mode('html').unparse(t,m.entities)
				r= re.findall(r'<a href="tg://user\?id=([0-9]+)">.+</a>',h)
				if r:
					u=int(r[0])
			else:
				h=t
				#return
			if u==my_id and get_config_key("farm"):
				print(m.raw_text)
				f=await ферма(14401)	# ждем + шлем
		
		########################################################################
		
		@client.on(events.NewMessage(outgoing=True, pattern='.ping'))
		async def cmd_ping(event):
			# Say "pong!" whenever you send "!ping", then delete both messages
			m = await event.reply('pong!')
			await asyncio.sleep(5)
			await client.delete_messages(event.chat_id, [event.id, m.id])
		
		########################################################################
		
		if get_config_key("farm") and ch_id<0:
			await ферма()
		
		########################################################################
		
		await client.run_until_disconnected()
		
		########################################################################
		
asyncio.run(main())
