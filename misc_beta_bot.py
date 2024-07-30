# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

from config import TOKEN

from const import REG_OK

import os
import re
import random
import time

#import pymysql
#import pymysql.cursors

import sqlite3

#print('Bot started') 

con = sqlite3.connect("db4tg.sqlite")

cur = con.cursor()

cur.execute('''CREATE TABLE IF NOT EXISTS users (
		user_id	INTEGER NOT NULL DEFAULT 0 UNIQUE,
		reg_int	INTEGER NOT NULL DEFAULT 0,
		f_name	VARCHAR NOT NULL DEFAULT 'хз',
		mcoins	INTEGER NOT NULL DEFAULT 1024,
		rng_kd	INTEGER NOT NULL DEFAULT 0,
		lng_code	VARCHAR NOT NULL DEFAULT ''
		)''');

async def reg_user(message: types.Message):
	print(message)
	user_id = int(message.from_user.id)
	user_fn = message.from_user.first_name or ''
	lng_code = message.from_user.language_code or ''
	when_int = int(datetime.timestamp(message.date))
	try:
		cur.execute("INSERT OR IGNORE INTO users(user_id,reg_int,f_name,lng_code) VALUES (?,?,?,?)", (int(user_id),int(when_int),str(user_fn),str(lng_code))); con.commit()
	except Exception as Err:
		print(Err)
	try:
		cur.execute("SELECT reg_int FROM users WHERE user_id = %d" % int(user_id)); 
		rd = cur.fetchone();
		if rd is None:
			return 0
		else:
			rd=rd[0]
			if rd==when_int:
				print(REG_OK.get(lng_code, REG_OK['default']).format(user_fn=user_fn))
		return rd
	except Exception as Err:
		print(Err)
	return 0

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)   

print('Bot started') 

@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
	#print(message)
	snd_msg = "🖖"
	user_id = int(message.from_user.id)
	user_fn = message.from_user.first_name or ''
	lng_code = message.from_user.language_code or ''
	when_int = int(datetime.timestamp(message.date))
	rd=int(await reg_user(message))#create or date
	if rd == when_int:
		snd_msg = REG_OK.get(lng_code, REG_OK['default']).format(user_fn=user_fn)
	await message.answer(snd_msg)

@dp.message_handler(commands=['reg'])
async def cmd_reg(message: types.Message):
	#print(message)
	snd_msg = "🤷"
	user_id = int(message.from_user.id)
	user_fn = message.from_user.first_name or ''
	lng_code = message.from_user.language_code or ''
	when_int = int(datetime.timestamp(message.date))
	rd=int(await reg_user(message))#create or date
	if rd == when_int:
		snd_msg = REG_OK.get(lng_code, REG_OK['default']).format(user_fn=user_fn)
	elif rd > 0:
		snd_msg = time.strftime('%d.%m.%Y', time.localtime(rd))
	await message.answer(snd_msg)

@dp.message_handler(commands=['farm','ферма','random','rand','rnd'])
async def cmd_farm (message: types.Message):
	user_id = int(message.from_user.id)
	when_int = int(datetime.timestamp(message.date))
	await reg_user(message)#register_user
	bal = 0
	rkd = 0
	try:
		cur.execute("SELECT mcoins,rng_kd FROM users WHERE user_id = %d" % int(user_id)); 
		rd = cur.fetchone();
		if rd is None:
			msg = "ERROR"			
		else:
			#print(rd)
			bal = rd[0]
			rkd = rd[1]
			if when_int > rkd:
				rnd = random.randint(-32,64)
				if rnd > 0:
					msg = f"✅ ok!	+{rnd}"
					rkd = rnd * 60
				if rnd < 0:
					msg = f"❎ ой! {rnd}"
					rkd = (64-rnd) *32
				if rnd == 0:
					rnd = 100
					rkd = rnd * 64
					msg = f"✅ оу!	+{rnd}"
				bal+=rnd
				if bal<10:
					bal =10	#я сьодня добрьій.
				msg=f"{msg}\n🤑 бл:	{bal} \n⌚️	кд: {rkd} сек"
				rkd+=when_int
				try:
					cur.execute("UPDATE users SET mcoins = :bal, rng_kd = :rkd WHERE user_id = :uid;", 
					{"rkd":int(rkd),"bal":int(bal),"uid":int(user_id)}); con.commit()
				except Exception as Err:
					msg = Err
					print(Err)
			else:
				rkd = rkd-when_int
				msg=f"\n⌚️	кд: {rkd} сек.\n🤑 бл:	{bal}"
	except Exception as Err:
		msg = Err
		print(Err)
	await message.answer(msg)

@dp.message_handler(commands=['help'])
async def process_help_command(message: types.Message):
	#await message.answer(emoji="🤷")
	await message.answer('''
•	💬 /chats
•	🎲 /dice
•	🤑 /rnd
''')

@dp.message_handler(commands=['ping'])
async def process_ping_command(message: types.Message):
	await message.reply("PONG!")

@dp.message_handler(commands=['dice','кубик'])
async def cmd_dice(message: types.Message):
	await message.answer_dice(emoji="🎲")

@dp.message_handler(commands=['chats','чати','чаты','чаті'])
async def cmd_chats(message: types.Message):
	await message.answer('''
•	☕ @misc_chat
•	🦠 @misc_flood
•	🦠 @misc_games
•	🗃 @misc_files_v2
''')

if __name__ == '__main__':
	executor.start_polling(dp)
