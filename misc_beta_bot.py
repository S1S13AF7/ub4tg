# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

from config import TOKEN

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)   

print('Bot started') 

@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
	#print(message)
	await message.answer(emoji="🖖")

@dp.message_handler(commands=['help'])
async def process_help_command(message: types.Message):
	#print(message)
	await message.answer(emoji="🤷")

@dp.message_handler(commands=['ping'])
async def process_ping_command(message: types.Message):
	#print(message)
	await message.reply("PONG!")

@dp.message_handler(commands=['кубик'])
async def cmd_dice(message: types.Message):
	#print(message)
	await message.answer_dice(emoji="🎲")

@dp.message_handler(commands=['coffee','кава','кофе','кофи','кофі'])
async def cmd_coffee(message: types.Message):
	#print(message)
	await message.answer("☕")

@dp.message_handler(commands=['tea','чай','чяй'])
async def cmd_tea(message: types.Message):
	#print(message)
	await message.answer("🍵")

@dp.message_handler(commands=['chats','чати','чаты','чаті'])
async def cmd_chats(message: types.Message):
	#print(message)
	await message.answer('''
•	☕ @misc_chat
•	🦠 @misc_flood
•	🦠 @misc_games
•	🗃 @misc_files_v2
''')

if __name__ == '__main__':
	executor.start_polling(dp)
