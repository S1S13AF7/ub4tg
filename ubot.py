# -*- coding: utf-8 -*-
#https://docs-python.ru/packages/telegram-klient-telethon-python/	<-info
import asyncio

from datetime import datetime, timedelta
#from telethon.sync import TelegramClient
from telethon import TelegramClient, events, utils

import os
import re
import random
#import pytz
import time

import pymysql
import pymysql.cursors

import sqlite3

#Название сессии
sessdb = 'tl-ub'
#Api ID и Api Hash полученные на my.telegram.org

api_id = 00000000
api_hash = 'blahblahblahblahblahblahblahblah'
timezone = "Europe/Kiev"

db_pymysql = True#set True or False
db_sqlite3 = True#set True or False

a_h = False # set True or False

async def main():
	async with TelegramClient(sessdb,api_id,api_hash) as client:
		client.parse_mode="HTML"
		print('User-Bot started')
		me= await client.get_me()
		my_id = int(me.id)
		my_fn = me.first_name
		print(my_id)
		
		if db_pymysql:
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
			#conn = sqlite3.connect(f"D:\\Misc\\projects\\Python\\ub4tg_db\\{my_id}.sqlite")#Або повністю
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
			bio_str	VARCHAR NOT NULL DEFAULT 1,
			bio_int	INTEGER NOT NULL DEFAULT 1,
			expr_int	INTEGER NOT NULL DEFAULT 0,
			expr_str	VARCHAR NOT NULL DEFAULT 0
			)''');
			conn.commit()
		####################################################################
		async def get_id(url):
			user_id = 0
			if "tg://openmessage?user_id=" in url:
				user_id = int(re.findall(r'user_id=([0-9]+)',url)[0])
				print(user_id)
				return user_id
			if "t.me/" in url:
				if db_pymysql:
					try:
						d.execute("SELECT * FROM `tg_users_url` WHERE `u_link` = '%s' ORDER BY `when_int` DESC" % str(url)); 
						user = d.fetchone();
						if user is None:
							#print(f'не знайшли {url} у `tg_users_url`')
							pass
						else:
							user_id = int(user['user_id'])
							print(f'{url} in db: @{user_id}')
					except Exception as Err:
							print(f'E:{Err}/S {url} у `tg_users_url`')
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
		
		
		@client.on(events.NewMessage(outgoing=True,pattern='\.п'))
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
							f"🤬 <code>{b}</code>\n⏳ ")#копіпабельно для пошуку
					await event.edit(new) #ред
		
		
		####################################################################
		
		
		@client.on(events.NewMessage(pattern='.*подверг(ла)? заражению.*'))
		async def podverg(event):
			#хто там кого подверг(ла)
			m = event.message
			t = m.raw_text
			irises = [707693258,5137994780,5226378684,5443619563,5434504334]
			if m.sender_id not in irises:
				#print(f"@{m.sender_id} не Iris!?");#Або це або pass. що краще?
				pass
			elif len(m.entities) > 1:
				h= utils.sanitize_parse_mode('html').unparse(t,m.entities)#HTML
				r= re.findall(r'🦠 <a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">.*</a> подверг.+<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">',h)
				if r:
					u1url=r[0][0]
					u2url=r[0][1]
					u1id = await get_id(u1url)
					u2id = await get_id(u2url)
					#print(f'{u1url} [@{u1id}] подверг(ла) {u2url} [@{u2id}]')#показать
					when=int(datetime.timestamp(m.date))
					days=int(re.sub(r' ','',re.findall(r' на ([0-9\ ]+) д.*', t)[0]))
					experience=re.findall(r"\+([0-9\.\,k]+) био-опыта", t)[0]
					if ',' in experience:
						experience=re.sub(r',', r'.',experience)
					if 'k' in experience:
						exp_int=int(float(re.sub('k', '',experience)) * 1000)
					else:
						exp_int=int(experience)
					if 'Объект ещё не подвергался заражению вашим патогеном' in event.raw_text:
						exp_int=int(re.sub(r' ','',re.findall(r'по ([0-9\ ]+) ед.*',event.raw_text)[0]))
					a=datetime.utcfromtimestamp(when)+timedelta(days=int(days), hours=3)
					do_int=datetime.timestamp(a)
					do_txt=str(a.strftime("%d.%m.%y"))
					if u1id > 0 and u2id > 0 and u1id != u2id:
						if db_sqlite3 and u1id==my_id:
							try:
								c.execute("INSERT INTO zarazy(user_id,when_int,bio_str,bio_int,expr_int,expr_str) VALUES (?, ?, ?, ?, ?, ?)", (int(u2id),int(when),str(experience),int(exp_int),int(datetime.timestamp(a)),str(a.strftime("%d.%m.%y")))); conn.commit()
							except:
								try:
									c.execute("UPDATE zarazy SET when_int = :wh, bio_str = :xp, bio_int = :xpi, expr_int = :end, expr_str = :do WHERE user_id = :z AND when_int <= :wh;", {"wh":int(when),"xp":str(experience),"xpi":int(exp_int),"end":int(datetime.timestamp(a)),"do":str(a.strftime("%d.%m.%y")),"z":int(u2id)}); conn.commit()
								except Exception as Err:
									print(f'err: {Err} zarazy')
						if db_pymysql:
							try:
								d.execute("INSERT INTO `tg_iris_zarazy` (`who_id`, `user_id`, `when_int`, `bio_str`, `bio_int`, `expr_int`, `expr_str`, `u_link`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE when_int=VALUES (when_int),bio_str=VALUES (bio_str),bio_int=VALUES (bio_int),expr_int=VALUES (expr_int),expr_str=VALUES (expr_str),u_link = VALUES (u_link);", (int(u1id),int(u2id),int(when),str(experience), int(exp_int), int(datetime.timestamp(a)),str(a.strftime("%d.%m.%y")),str(u2url))); con.commit()
								print(f"\nINSERT INTO .... ON DUPLICATE KEY UPDATE # [@{u1id}] => [@{u2id}]\n")
							except Exception as Err:
								print(f'err: {Err} /localhost')
								#pass
						print(f'''{u1url} [@{u1id}] подверг(ла) {u2url} [@{u2id}] +{experience}''')#показать
		
		
		####################################################################
		
		
		@client.on(events.NewMessage(pattern='.*йобнув.*|.*подверг(ла)?.*|.*infected.*|.*сикди.*|.*насрал.*'))
		async def podverg_a(event):
			#хто там кого йобнув(ла)
			m = event.message
			t = m.raw_text
			if m.sender_id !=6333102398:
				pass
			elif len(m.entities) > 1:
				h= utils.sanitize_parse_mode('html').unparse(t,m.entities)#HTML
				r= re.findall(r'<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">.*</a> (йобнув|подверг|infected|сикди|насрал|за допомогою|при помощи|by authorization).+<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">',h)
				if r:
					u1url=r[0][0]
					u2url=r[0][2]
					u1id = await get_id(u1url)
					u2id = await get_id(u2url)
					experience=1# fix if not preg match
					when=int(datetime.timestamp(m.date))
					days=int(re.sub(r' ','',re.findall(r' (на|for) ([0-9\ ]+) (д|d).*', t)[0][1]))
					experience=re.findall(r"([☣️🧬🎄]).+: ([0-9\.\,k]+).+ \|",t)[0][1]
					if ',' in experience:
						experience=re.sub(r',', r'.',experience)
					if 'k' in experience:
						exp_int=int(float(re.sub('k', '',experience)) * 1000)
					else:
						exp_int=int(experience)
					a=datetime.utcfromtimestamp(when)+timedelta(days=int(days), hours=3)
					do_int=datetime.timestamp(a)
					do_txt=str(a.strftime("%d.%m.%y"))
					if u1id > 0 and u2id > 0:
						if db_sqlite3 and u1id==my_id:
							try:
								c.execute("INSERT INTO avocado(user_id,when_int,bio_str,bio_int,expr_int,expr_str) VALUES (?, ?, ?, ?, ?, ?)", (int(u2id),int(when),str(experience),int(exp_int),int(datetime.timestamp(a)),str(a.strftime("%d.%m.%y")))); conn.commit()
							except:
								try:
									c.execute("UPDATE avocado SET when_int = :wh, bio_str = :xp, bio_int = :xpi, expr_int = :end, expr_str = :do WHERE user_id = :z AND when_int <= :wh;", {"wh":int(when),"xp":str(experience),"xpi":int(exp_int),"end":int(datetime.timestamp(a)),"do":str(a.strftime("%d.%m.%y")),"z":int(u2id)}); conn.commit()
								except Exception as Err:
									print(f'err: {Err} avocado')
						elif db_sqlite3:
							try:
								c.execute("INSERT INTO avocado(user_id,when_int,bio_str,bio_int,expr_int) VALUES (?, ?, ?, ?, ?)", (int(u2id),int(when),str(experience),int(exp_int),int(0))); conn.commit()#save not my pacients
							except:
								#user in db. not need update? ну а нафіга?
								pass
						if db_pymysql:
							try:
								#from_infect 	who_id 	user_id 	profit 	until_infect 	until_str
								d.execute("INSERT INTO `tg_bio_attack` (`who_id`, `user_id`, `from_infect`, `profit`, `until_infect`, `until_str`) VALUES (%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE from_infect=VALUES (from_infect),profit=VALUES (profit),until_infect=VALUES (until_infect),until_str = VALUES (until_str);", (int(u1id),int(u2id),int(when),str(experience), int(datetime.timestamp(a)),str(a.strftime("%d.%m.%y")))); con.commit()
								print(f"\nINSERT INTO .... ON DUPLICATE KEY UPDATE # [@{u1id}] => [@{u2id}]\n")
							except Exception as Err:
								print(f'err: {Err} (tg_bio_attack)')
								#pass
							try:
								#user_id 	when 	profit
								d.execute("INSERT INTO `tg_bio_users` (`user_id`, `when_int`, `profit`) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE when_int=VALUES (when_int),profit=VALUES (profit);", (int(u2id),int(when),str(experience))); con.commit()
							except Exception as Err:
								print(f'err: {Err} (tg_bio_users)')
								#pass
						print(f'''{u1url} [@{u1id}] подверг(ла) {u2url} [@{u2id}] +{experience}''')#показать
		
		
		####################################################################
		
		
		@client.on(events.NewMessage(outgoing=True, pattern='\.biofuck$'))
		async def cmd_bf(event):			#крч акуратно з цим,вдруг шо я нічо
			m = event.message
			text = m.raw_text
			when=int(datetime.timestamp(m.date))
			msg='🤷' # якщо нема кого то жри рандом.
			c.execute(f"SELECT * FROM `avocado` WHERE expr_int <= {when}"); 
			e_info=c.fetchall()
			count = len(e_info)
			if count < 2:
				nema=f'🤷 рандом хавай.'
				await event.edit(nema) #ред
				print(nema)
			else:
				pong='✅ погнали...'
				await event.edit(pong) #ред
				print(f'є {count} потенційних пацієнтів. спробуєм їх сожрать')
				for row in e_info:
					rs = float(random.uniform(11,99)) #скільки спим: random
					eb = f'Биоеб {row[0]}' #повідомлення.
					m=await event.reply(eb)
					await asyncio.sleep(3.3)
					await client.delete_messages(event.chat_id,m.id)
					await asyncio.sleep(rs)
				
		
		####################################################################
		
		
		@client.on(events.NewMessage(pattern='🌡 У вас горячка вызванная'))
		async def need_h(event):
			m = event.message
			if m.sender_id !=6333102398:
				pass
			elif a_h and m.mentioned:
				#нада хил
				ah = await message_q( # отправляет сообщение боту
				f"Хил",
				6333102398,
				mark_read=True,
				delete=False,
				)
		
		
		####################################################################
		
		
		@client.on(events.NewMessage(outgoing=True, pattern='.l2f'))
		async def cmd_l2f(event):			#Local->file/{id}.sqlite
			msg='для успішного виконання повинно бути обидві бази True'
			if db_pymysql:
				try:
					d.execute("SELECT * FROM `tg_iris_zarazy` WHERE who_id = %d ORDER BY when_int;" % int(my_id));
					bz_info = d.fetchall()#получить
					count=len(bz_info)
					if count==0:
						msg='🤷 інфа нема.'
						print(msg)
					else:
						saved=0
						for row in bz_info:
							print(row)
							id_user=int(row["user_id"])
							bio_int=int(row["bio_int"])
							bio_str=str(row["bio_str"])
							when_int=int(row["when_int"])
							expr_int=int(row["expr_int"])
							expr_str=str(re.sub(r'.20', r'.',row["expr_str"]))	#.2024->.24
							user_url=str(f'tg://openmessage?user_id={id_user}')	#fix для любителів мінять його
							if db_sqlite3:
								try:
									c.execute("INSERT INTO zarazy (user_id,when_int,bio_str,bio_int,expr_int,expr_str) VALUES (?, ?, ?, ?, ?, ?)", (int(id_user),int(when_int),str(bio_str),int(bio_int),int(expr_int),str(expr_str))); conn.commit()
									saved+=1
								except:
									try:
										c.execute("UPDATE zarazy SET when_int = :wh, bio_str = :xp, bio_int = :xpi, expr_int = :end, expr_str = :do WHERE user_id = :z AND when_int <= :wh;", {"wh":int(when_int),"xp":str(bio_str),"xpi":int(bio_int),"end":int(expr_int),"do":str(expr_str),"z":int(id_user)}); conn.commit()
									except Exception as Err:
										print(f'err: {Err} zarazy')
								msg=f"{saved} із {count}"
							else:
								msg='для успішного виконання повинно бути обидві бази True'
				except Exception as Err:
					print(f'err: {Err} zarazy localhost')
					msg=Err
			m=await event.reply(msg)
			await asyncio.sleep(5)
			await client.delete_messages(event.chat_id, [event.id, m.id])
		
		
		@client.on(events.NewMessage(outgoing=True, pattern='.ping'))
		async def cmd_ping(event):
			# Say "pong!" whenever you send "!ping", then delete both messages
			m = await event.reply('pong!')
			await asyncio.sleep(5)
			await client.delete_messages(event.chat_id, [event.id, m.id])
		
		await client.run_until_disconnected()

asyncio.run(main())
