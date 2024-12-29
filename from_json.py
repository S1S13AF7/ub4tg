# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

import os
import re
import time
import json

import sqlite3

if os.name == 'nt':
	import win32api

db_pymysql = False# set True or False
db_sqlite3 = True	# set True or False

########################################################################
if db_sqlite3:
	conn = sqlite3.connect(f"0.sqlite") # Ваша база
	c = conn.cursor()
	
	c.execute('''CREATE TABLE IF NOT EXISTS avocado	(
	user_id	INTEGER NOT NULL DEFAULT 0 UNIQUE,
	when_int	INTEGER NOT NULL DEFAULT 0,
	bio_int	INTEGER NOT NULL DEFAULT 1,
	expr_int	INTEGER NOT NULL DEFAULT 0,
	expr_str	VARCHAR NOT NULL DEFAULT 0
	)''');
	conn.commit()
	
	
########################################################################

jsonfile='victims.json'
with open(jsonfile, 'r') as stealed_backup:
	try:
		victims = json.load(stealed_backup)
		count=0
		saved=0
		updtd=0
		errrs=0
		for v in victims:
			if v['user_id']:
				print(v)
				count +=1
				id_user = int(v['user_id'])
				bio_int = int(v['profit'] or 1)
				when_int= int(v['from_infect'] or 0)
				if db_sqlite3:
					try:
						c.execute("INSERT INTO avocado(user_id,when_int,bio_int,expr_int) VALUES (?,?,?,?)", (int(id_user),int(when_int),int(bio_int),int(0))); conn.commit()# save not my pacients
						saved+=1
					except:
						try:
							c.execute("UPDATE avocado SET when_int = :wh, bio_int = :xpi WHERE user_id = :z AND when_int < :wh AND expr_int < :wh;", {"wh":int(when_int),"xpi":int(bio_int),"z":int(id_user)}); conn.commit()
							updtd+=1
						except Exception as Err:
							print(f'err: {Err} avocado upd not my')
							errrs+=1

		m=f'users: {count}\nsaved: {saved}\nupdtd? {updtd}\nerrrs: {errrs}'
		print(m)
	except Exception as Err:
		print(f'err: {Err}')

#
