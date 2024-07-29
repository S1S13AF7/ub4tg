# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

from config import TOKEN

import os
import re
import random
import time

#import pymysql
#import pymysql.cursors

import sqlite3

print('Bot started') 

con = sqlite3.connect("db4tg.sqlite")
cur = con.cursor()

cur.execute('''CREATE TABLE IF NOT EXISTS users	(
 user_id	INTEGER NOT NULL DEFAULT 0 UNIQUE,
 when_int	INTEGER NOT NULL DEFAULT 0,
 c_dice	INTEGER NOT NULL DEFAULT 0,
 coffee	INTEGER NOT NULL DEFAULT 0,
 c_tea	INTEGER NOT NULL DEFAULT 0,
 f_name	VARCHAR NOT NULL DEFAULT 0,
 lang_code	VARCHAR NOT NULL DEFAULT 0,
 last_cmd	VARCHAR NOT NULL DEFAULT 0,
 user_url	VARCHAR NOT NULL DEFAULT 0)''');

async def reg_user(message: types.Message):
		print(message)
		msg = "🖖"
		user_id = message["from"]["id"]
		user_fn = message["from"]["first_name"]
		lngcode = message["from"]["language_code"]
		whenint = int(datetime.timestamp(message.date))
		try:
			cur.execute("INSERT INTO users(user_id,when_int,f_name,lang_code) VALUES (?, ?, ?, ?)", (int(user_id),int(whenint),user_fn,lngcode)); con.commit()
			msg="✅ ok"
			if lngcode=='uk':
				msg = f"✅ {user_fn} успішно зареєструвавсь(лась)"
			if lngcode=='ru':
				msg = f"✅ {user_fn} успешно зарегистрировался(лась)"
			if lngcode=='be':
				msg = f"✅ паспяхова зарэгістраваны"
			if lngcode=='en':
				msg = f"✅ successfully registered"
			print (msg)
		except Exception as Err:
			print(Err)
		return msg

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)   

@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    #print(message)
    await message.answer(await reg_user(message))

@dp.message_handler(commands=['help'])
async def process_help_command(message: types.Message):
    #print(message)
    await message.answer(emoji="🤷")

@dp.message_handler(commands=['ping'])
async def process_ping_command(message: types.Message):
    #print(message)
    await message.reply("PONG!")

@dp.message_handler(commands=['code'])
async def cmd_code(message: types.Message):
    #print(message)
    await message.reply("https://github.com/S1S13AF7/misc_beta_bot")

@dp.message_handler(commands=['кубик'])
async def cmd_dice(message: types.Message):
    #print(message)
    await message.answer_dice(emoji="🎲")

@dp.message_handler(commands=['coffee','кава','кофе','кофи','кофі'])
async def cmd_coffee(message: types.Message):
    #print(message)
    await message.answer("☕️")

@dp.message_handler(commands=['tea','чай','чяй'])
async def cmd_tea(message: types.Message):
    #print(message)
    await message.answer("🍵")

@dp.message_handler(commands=['chats','чати','чаты','чаті'])
async def cmd_chats(message: types.Message):
    #print(message)
    await message.answer('''
•   ☕️ @misc_chat
•   🦠 @misc_games
•   🗃 @misc_files_v2
''')

if __name__ == '__main__':
    executor.start_polling(dp)
