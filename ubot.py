# -*- coding: utf-8 -*-
#https://docs-python.ru/packages/telegram-klient-telethon-python/	<-info
import asyncio

from datetime import datetime, timedelta
#from telethon.sync import TelegramClient
from telethon import TelegramClient, events, utils

import os
import re
import random
import time

import pymysql
import pymysql.cursors

import sqlite3

#Название сессии
sessdb = 'tl-ub'
#Api ID и Api Hash полученные на my.telegram.org

api_id = 00000000
api_hash = 'blahblahblahblahblahblahblahblah'

db_pymysql = True#set True or False
db_sqlite3 = True#set True or False

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
		####################################################################
		async def get_id(url):
			user_id = 0
			if "tg://openmessage?user_id=" in url:
				user_id = int(re.findall(r'user_id=([0-9]+)',url)[0])
				print(user_id)
				return user_id
			if "t.me/" in url:
				try:
					user_entity = await client.get_entity(url)
					if user_entity.id:
						user_id = int(user_entity.id)
						print(f'ok:{url}/@{user_id}')
				except:
					#неок.
					pass
			return user_id
		
		@client.on(events.NewMessage(pattern='.*подверг(ла)? заражению.*'))
		async def podverg(event):
			#хто там кого подверг(ла)
			m = event.message
			t = m.raw_text
			irises = [707693258,5137994780,5226378684,5443619563,5434504334]
			if m.sender_id not in irises:
				print(f"@{m.sender_id} не Iris!?");#Або це або pass. що краще?
				#pass
			elif len(m.entities) > 1:
				h= utils.sanitize_parse_mode('html').unparse(t,m.entities)#HTML
				r= re.findall(r'🦠 <a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">.*</a> подверг.+<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">',h)
				if r:
					u1url=r[0][0]
					u2url=r[0][1]
					u1id = await get_id(u1url)
					u2id = await get_id(u2url)
					print(f'{u1url} [@{u1id}] подверг(ла) {u2url} [@{u2id}]')#показать в консолі?
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
						#Объект ещё не подвергался заражению вашим патогеном, поэтому каждый день, пока он заражён, вы будете получать по ? ??? единиц био-ресурса
						exp_int=int(re.sub(r' ','',re.findall(r'по ([0-9\ ]+) ед.*',event.raw_text)[0]))
					a=datetime.utcfromtimestamp(when)+timedelta(days=int(days), hours=3)
					do_int=datetime.timestamp(a)
					do_txt=str(a.strftime("%d.%m.%y"))
					if u1id > 0 and u2id > 0 and u1id != u2id:
						#print(f'''{u1url} [@{u1id}] подверг(ла) {u2url} [@{u2id}] +{experience}''')#показать в консолі? Або закоментувати/прибрати.
						if db_sqlite3 and u1id==my_id:
							try:
								c.execute("INSERT INTO zarazy(user_id,when_int,bio_str,bio_int,expr_int,expr_str) VALUES (?, ?, ?, ?, ?, ?)", (int(u2id),int(when),experience,exp_int,datetime.timestamp(a),str(a.strftime("%d.%m.%y")))); conn.commit()
								print('add/db.sqlite')
							except:
								try:
									c.execute("UPDATE zarazy SET when_int = :wh, bio_str = :xp, bio_int = :xpi, expr_int = :end, expr_str = :do WHERE user_id = :z AND when_int <= :wh;", {"wh":int(when),"xp":experience,"xpi":exp_int,"end":datetime.timestamp(a),"do":str(a.strftime("%d.%m.%Y")),"z":int(user2_id)}); conn.commit()
								except Exception as Err:
									print(f'err: {Err} zarazy')
						if db_pymysql:
							u2url=f'tg://openmessage?user_id={u2id}'	#fix для любителів мінять його
							try:
								d.execute("INSERT INTO `tg_iris_zarazy` (`who_id`, `user_id`, `when_int`, `bio_str`, `bio_int`, `expr_int`, `expr_str`, `u_link`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE when_int=VALUES (when_int),bio_str=VALUES (bio_str),bio_int=VALUES (bio_int),expr_int=VALUES (expr_int),expr_str=VALUES (expr_str),u_link = VALUES (u_link);", (int(u1id),int(u2id),int(when),str(experience), int(exp_int), str(datetime.timestamp(a)),str(a.strftime("%d.%m.%y")),str(u2url))); con.commit()
								print(f"\nINSERT INTO .... ON DUPLICATE KEY UPDATE # [@{u1id}] => [@{u2id}]\n")
							except Exception as Err:
								print(f'err: {Err} /localhost')
								#pass
						print(f'''{u1url} [@{u1id}] подверг(ла) {u2url} [@{u2id}] +{experience}''')#показать в консолі? Або закоментувати/прибрати.
		
		@client.on(events.NewMessage(outgoing=True, pattern='!ping'))
		async def handler(event):
			# Say "!pong" whenever you send "!ping", then delete both messages
			m = await event.respond('!pong')
			await asyncio.sleep(5)
			await client.delete_messages(event.chat_id, [event.id, m.id])
		
		await client.run_until_disconnected()

asyncio.run(main())
