# -*- coding: utf-8 -*-
# from misc_beta_bot
# "диспетчер" це звичайний бот (не юб)
# Використовувати "диспетчер" є сенс, якщо: 
#
# > у вас є база MySQL на http://localhost/
# > у вас кілька акків підключено до 1 бд
#
# спільне використання однієї бд sqlite кількома ботами створює проблему db is locked
# тому у випадку з кількома юзерами у кожного своя sqlite база {id}.slite
# а от MySQL в свою чергу може бути спільна для всіх ботів і юзерботів.
# тобто якщо юзаєте лише sqlite то і "диспетчер" вам нафіг нетреба.
from datetime import datetime, timedelta

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

from config import TOKEN

import os
import re
import random
import time

import pymysql
import pymysql.cursors

import sqlite3

db_pymysql = True#set True
db_sqlite3 = False#set False

if db_pymysql:
	ldb=pymysql.connect(
	host='localhost',
	user='root',
	password='напишіть_сюда_ваш_пароль_від_локальної_бд',
	db='db',
	charset='utf8mb4',
	cursorclass=pymysql.cursors.DictCursor)
	dbc = ldb.cursor()
	dbc.execute('''CREATE TABLE IF NOT EXISTS `tg_iris_zarazy` (
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
	#зберігалка: https://github.com/S1S13AF7/ub4tg
	ldb.commit()

bot = Bot(token=TOKEN, parse_mode=types.ParseMode.HTML) #see: https://mastergroosha.github.io/aiogram-2-guide/messages/
dp = Dispatcher(bot)   

print('Bot started') 

@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
	#print(message)
	snd_msg = "🖖"
	await message.answer(snd_msg)


@dp.message_handler(commands=['mz','мж','мз'])
async def cmd_myzh (message: types.Message):
	msg="🤷"
	user_id = int(message.from_user.id)
	user_fn = message.from_user.first_name or ''
	lng_code = message.from_user.language_code or ''
	when_int = int(datetime.timestamp(message.date))
	if db_pymysql:
		try:
			#зберігалка: https://github.com/S1S13AF7/ub4tg (адреса може змінитись)
			dbc.execute("SELECT user_id,bio_str,expr_str FROM `tg_iris_zarazy` WHERE who_id = %d ORDER BY when_int DESC LIMIT 10;" % int(user_id));
			bz_info = dbc.fetchmany(10)#получить
			all_sicknes=[]#інфа
			count=len(bz_info)
			who=f"🦠 {user_fn}:"
			for row in bz_info:
				print(row)
				id_user=row["user_id"]
				bio_str=row["bio_str"]
				u_link =f'tg://openmessage?user_id={id_user}'	#fix для любителів мінять його
				expr_str=re.sub(r'.20', r'.',row["expr_str"]) #.2024->.24
				a_href = f'<a href="{u_link}"><code>@{id_user}</code></a>'
				all_sicknes.append(f"➕{bio_str}	{a_href}#{expr_str}\n")
			if len(all_sicknes)!=0:
				all_sicknes=f'{who}\n{"".join(all_sicknes)}'
			else:
				all_sicknes='🤷 інфа нема.'
			msg=all_sicknes
		except Exception as Err:
			msg = Err
			print(f"localhost SELECT:{Err}")
	await message.answer(msg, parse_mode=types.ParseMode.HTML)

@dp.message_handler(commands=['ends'])
async def cmd_ends (message: types.Message):
	msg="🤷"
	user_id = int(message.from_user.id)
	user_fn = message.from_user.first_name or ''
	lng_code = message.from_user.language_code or ''
	when_int = int(datetime.timestamp(message.date))
	if db_pymysql:
		try:
			#зберігалка: https://github.com/S1S13AF7/ub4tg (адреса може змінитись)
			dbc.execute(f"SELECT user_id,bio_str,expr_str FROM `tg_iris_zarazy` WHERE who_id = {user_id} AND expr_int < {when_int} ORDER BY `bio_int` DESC, `when_int` DESC LIMIT 10;")
			bz_info = dbc.fetchmany(10)#получить
			all_sicknes=[]#інфа
			count=len(bz_info)
			who=f"🦠 {user_fn}:"
			for row in bz_info:
				print(row)
				id_user=row["user_id"]
				bio_str=row["bio_str"]
				u_link =f'tg://openmessage?user_id={id_user}'	#fix для любителів мінять його
				expr_str=re.sub(r'.20', r'.',row["expr_str"]) #.2024->.24
				a_href = f'<a href="{u_link}"><code>@{id_user}</code></a>'
				all_sicknes.append(f"➕{bio_str} {a_href}#{expr_str}\n")
			if len(all_sicknes)!=0:
				all_sicknes=f'{who}\n{"".join(all_sicknes)}'
			else:
				all_sicknes='🤷 інфа нема.'
			msg=all_sicknes
		except Exception as Err:
			msg = Err
			print(f"localhost SELECT:{Err}")
	await message.answer(msg, parse_mode=types.ParseMode.HTML)

@dp.message_handler(commands=['help'])
async def process_help_command(message: types.Message):
	#await message.answer(emoji="🤷")
	await message.answer('''
•	🦠 /mz
''')

@dp.message_handler(commands=['ping'])
async def process_ping_command(message: types.Message):
	await message.reply("PONG!")

@dp.message_handler(commands=['dice','кубик'])
async def cmd_dice(message: types.Message):
	await message.answer_dice(emoji="🎲")

@dp.message_handler(commands=['code','код'])
async def cmd_code(message: types.Message):
	text='''
<code>https://github.com/S1S13AF7/ub4tg</code> – юб. Зберігалка хто кого заразив
	'''
	await message.answer(text,parse_mode=types.ParseMode.HTML)

if __name__ == '__main__':
	executor.start_polling(dp)
