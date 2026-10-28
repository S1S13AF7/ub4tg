# -*- coding: utf-8 -*-

import asyncio
from telethon import TelegramClient, errors
import qrcode

import os
import json

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
		
################################################################################

# Функція малювання QR-коду в консолі
def display_qr(url):
    qr = qrcode.QRCode()
    qr.clear()
    qr.add_data(url)
    print("Налаштування -> Пристрої -> Підключити пристрій\n")
    # tty=True змушує консоль використовувати інвертовані кольори для коректного зчитування
    qr.print_ascii(tty=True) 

async def main():
    # Називаємо сесію, наприклад 'my_telegram_account'
    client = TelegramClient(sessdb, api_id, api_hash)
    await client.connect()

    if await client.is_user_authorized():
        print("Ви вже успішно авторизовані!")
        me = await client.get_me()
        print(f"Увійшли як: {me.first_name} (@{me.id})")
        await client.disconnect()
        return

    # Ініціалізуємо вхід через QR
    qr_login = await client.qr_login()
    
    # Показуємо QR-код у терміналі
    display_qr(qr_login.url)

    # Очікуємо, поки користувач сканує код (таймаут 45 секунд)
    try:
        await qr_login.wait(timeout=45)
        print("\n[+] Успішно авторизовано через QR-код!")
        
    except errors.SessionPasswordNeededError:
        # Якщо у вас увімкнена двофакторна автентифікація (хмарний пароль)
        print("\n[!] QR-код скановано, але потрібен пароль двоетапної перевірки (2FA).")
        password = input("Введіть ваш хмарний пароль Telegram: ")
        await client.sign_in(password=password)
        print("[+] Успішно авторизовано з хмарним паролем!")
        
    except asyncio.TimeoutError:
        print("\n[-] Час очікування QR-коду вичерпано. Спробуйте запустити скрипт знову.")
        # Перестворюємо токен, якщо не встигли
        await qr_login.recreate()
        return

    # Перевірка успішного входу
    me = await client.get_me()
    print(f"Вітаємо, {me.first_name}! Сесія успішно створена.")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
