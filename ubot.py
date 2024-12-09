# -*- coding: utf-8 -*-
# https://docs-python.ru/packages/telegram-klient-telethon-python/	<-info
import asyncio

from datetime import datetime, timedelta
# from telethon.sync import TelegramClient
from telethon import TelegramClient, events, utils

import sys
import json
import re
import random
# import pytz
import time

import pymysql
import pymysql.cursors

import sqlite3
from loguru import logger
logger.remove()
logger.level("DEBUG", color='<magenta>')
logger.add(sys.stderr, level="DEBUG")

# Название сессии
sessdb = 'tl-ub'
with open("config.json", "r") as configfile:
    from types import SimpleNamespace
    cnf_dict = json.load(configfile)
    config = SimpleNamespace(**cnf_dict)
    logger.debug('config loaded')

# Api ID и Api Hash полученные на my.telegram.org
api_id = config.api_id
api_hash = config.api_hash
timezone = config.timezone

db_pymysql = config.db_pymysql  # set True or False
db_sqlite3 = config.db_sqlite3  # set True or False
a_h = config.a_h


class states:
    auto_bioeb_sleep_interval = (6, 66)  # the default on (re)start
    auto_bioeb_pathogen_threshold = 5  # these pathogens will be saved +- 1
    auto_bioeb_min_interval = (0.666, 3.666)  # for fast leak pathogen
    auto_bioeb_max_interval = (71, 121)  # waiting for more pathogen
    # Default strategy mean: you have 4-5 pathogens when auto bioeb is enabled, pathogen overflow reduced
    auto_bioeb_stop = False
    stats_medkit = 0



@logger.catch
async def main():
    async with TelegramClient(sessdb, api_id, api_hash) as client:
        client.parse_mode = "HTML"
        logger.success('User-Bot started')
        me = await client.get_me()
        my_id = int(me.id)
        my_fn = me.first_name
        logger.info(f'your id: {my_id}')
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
			);''')
            con.commit()
            d.execute('''CREATE TABLE IF NOT EXISTS `tg_bio_attack` (
			`from_infect` int(11) unsigned NOT NULL DEFAULT '0',
			`who_id` bigint(20) unsigned NOT NULL DEFAULT '0',
			`user_id` bigint(20) unsigned NOT NULL DEFAULT '0',
			`profit` int(11) unsigned NOT NULL DEFAULT '1',
			`until_infect` int(11) unsigned NOT NULL DEFAULT '0',
			`until_str` varchar(11) NOT NULL DEFAULT '0',
			UNIQUE KEY `UNIQUE` (`who_id`,`user_id`)
			);''')
            con.commit()
            d.execute('''CREATE TABLE IF NOT EXISTS `tg_bio_users` (
			`user_id` bigint(20) unsigned NOT NULL DEFAULT '0',
			`when_int` int(11) unsigned NOT NULL DEFAULT '0',
			`profit` int(11) unsigned NOT NULL DEFAULT '1',
			UNIQUE KEY `user_id` (`user_id`)
			);''')
            con.commit()
            d.execute('''CREATE TABLE IF NOT EXISTS `tg_users_url` (
			`user_id` bigint(20) unsigned NOT NULL DEFAULT '0',
			`when_int` int(11) unsigned NOT NULL DEFAULT '0',
			`u_link` varchar(64) NOT NULL DEFAULT '',
			`f_name` text NOT NULL,
			PRIMARY KEY (`user_id`),
			UNIQUE KEY (`u_link`)
			);''')
            con.commit()

        if db_sqlite3:
            conn = sqlite3.connect(f"{my_id}.sqlite")  # покласти базу рядом?
            # conn = sqlite3.connect(f"D:\\Misc\\projects\\Python\\ub4tg_db\\{my_id}.sqlite")#Або повністю
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS zarazy	(
			user_id	INTEGER NOT NULL DEFAULT 0 UNIQUE,
			when_int	INTEGER NOT NULL DEFAULT 0,
			bio_str	VARCHAR NOT NULL DEFAULT 1,
			bio_int	INTEGER NOT NULL DEFAULT 1,
			expr_int	INTEGER NOT NULL DEFAULT 0,
			expr_str	VARCHAR NOT NULL DEFAULT 0
			)''')
            conn.commit()
            c.execute('''CREATE TABLE IF NOT EXISTS avocado	(
			user_id	INTEGER NOT NULL DEFAULT 0 UNIQUE,
			when_int	INTEGER NOT NULL DEFAULT 0,
			bio_str	VARCHAR NOT NULL DEFAULT 1,
			bio_int	INTEGER NOT NULL DEFAULT 1,
			expr_int	INTEGER NOT NULL DEFAULT 0,
			expr_str	VARCHAR NOT NULL DEFAULT 0
			)''')
            conn.commit()
        ####################################################################

        async def get_id(url):
            user_id = 0
            if "tg://openmessage?user_id=" in url:
                user_id = int(re.findall(r'user_id=([0-9]+)', url)[0])
                logger.debug(user_id)
                return user_id
            if "t.me/" in url:
                if db_pymysql:
                    try:
                        d.execute(
                            "SELECT * FROM `tg_users_url` WHERE `u_link` = '%s' ORDER BY `when_int` DESC" % str(url))
                        user = d.fetchone()
                        if user is None:
                            # print(f'не знайшли {url} у `tg_users_url`')
                            pass
                        else:
                            user_id = int(user['user_id'])
                            print(f'{url} in db: @{user_id}')
                    except Exception as Err:
                        print(f'E:{Err}/S {url} у `tg_users_url`')
                if user_id == 0:
                    try:
                        user_entity = await client.get_entity(url)
                        if user_entity.id:
                            user_id = int(user_entity.id)
                            user_fn = user_entity.first_name or ''
                            print(f'ok:{url}/@{user_id}')
                            if db_pymysql:
                                try:
                                    d.execute("INSERT INTO `tg_users_url` (`when_int`,`user_id`,`u_link`,`f_name`) VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE user_id = VALUES (user_id),u_link = VALUES (u_link),f_name = VALUES (f_name),when_int = VALUES (when_int);", (int(
                                        time.time()), int(user_id), str(url), str(user_fn)))
                                    con.commit()
                                except Exception as Err:
                                    print(f'E:{Err}')
                    except Exception as Err:
                        print(f'E:{Err}')
                        # pass
            return user_id

        async def message_q(  # спизжено
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

        @client.on(events.NewMessage(pattern='.*йобнув.*|.*подверг(ла)? заражению.*|.*infected.*|.*сикди.*|.*насрал.*|.*подверг заморозке.*|.*за допомогою довіреності зазнала зараження.*|.*by authorization infected.*|.*при помощи анонимуса атаковала.*'))
        @logger.catch
        async def podverg_a(event):
            logger.debug('New bio attack detected')
            # хто там кого йобнув(ла)
            m = event.message
            t = m.raw_text
            # NOTE: theme hell... any ideas for improvment required
            # but not use huge regular expression like|that|fuckin|way|a|aaaa|aaaaaaaa
            # because it makes re.findall like mess...
            default_bioexpr_theme = r"Прибыль: ([0-9\.\,k]+)"
            default_infected_days_theme = r' на ([0-9\ ]+) д.*'
            default_pathogen_remaining_theme = r'Осталось: ([0-9\ ]+)'
            bio_attack_themes = (  # I guess if too many themes it will be slow, but acceptable, because python slow as is.
                # current order in theme:
                # ('infected', 'bio_expr', 'infected days', 'pathogen remaining')
                # UA theme
                (r'<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">.*</a> йобнув.+<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">',
                 r"([0-9\.\,k]+) біо-ресурса",
                 default_infected_days_theme,
                 default_pathogen_remaining_theme),
                # RU theme
                (r'<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">.*</a> подверг.+<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">',
                 default_bioexpr_theme,
                 default_infected_days_theme,
                 default_pathogen_remaining_theme),
                # EN theme
                (r'<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">.*</a> infected.+<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">',
                 r"([0-9\.\,k]+) pcs\.",
                 r' for ([0-9\ ]+) d.*',
                 r'Remaining: ([0-9\ ]+)'),
                # AZ theme
                (r'<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">.*</a> сикди.+<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">',
                 r"верир: ([0-9\.\,k]+)",
                 default_infected_days_theme,
                 default_pathogen_remaining_theme),
                # "ПК гик" theme
                (r'<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">.*</a> насрал.+<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">',
                 r"потеряет: ([0-9\.\,k]+)",
                 default_infected_days_theme,
                 default_pathogen_remaining_theme),
                # "Новогодняя" theme
                (r'<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">.*</a> подверг заморозке.+<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">',
                 default_bioexpr_theme,
                 default_infected_days_theme,
                 default_pathogen_remaining_theme),
                # UA theme [via trust]
                (r'<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">.*</a> за допомогою довіреності зазнала зараження.+<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">',
                 r"([0-9\.\,k]+) біо-ресурса",
                 default_infected_days_theme,
                 default_pathogen_remaining_theme),
                # RU theme [via trust]
                (r'<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">.*</a> при помощи доверенности подвергла заражению.+<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">',
                 default_bioexpr_theme,
                 default_infected_days_theme,
                 default_pathogen_remaining_theme),
                # EN theme [via trust]
                (r'<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">.*</a> by authorization infected.+<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">',
                 r"([0-9\.\,k]+) pcs\.",
                 r' for ([0-9\ ]+) d.*',
                 r'Remaining: ([0-9\ ]+)'),
                # idk what is theme [via trust]
                (r'<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">.*</a> при помощи анонимуса атаковала.+<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">',
                 r'приносит: ([0-9\.\,k]+)',
                 default_infected_days_theme,
                 default_pathogen_remaining_theme),
            )

            if m.sender_id != 6333102398:
                pass
            elif len(m.entities) > 1:
                h = utils.sanitize_parse_mode(
                    'html').unparse(t, m.entities)  # HTML
                for theme in bio_attack_themes:
                    trying_theme_index = bio_attack_themes.index(theme)
                    logger.debug(f'trying theme {trying_theme_index}...')
                    r = re.findall(theme[0], h)
                    if r:
                        logger.debug(f'found theme {trying_theme_index}')
                        break
                if r == []:
                    logger.warning('theme not found, showing original message: ' + m.text)
                logger.debug(str(r))
                if r:
                    u1url = r[0][0]
                    u2url = r[0][1]
                    u1id = await get_id(u1url)
                    u2id = await get_id(u2url)
                    # print(f'{u1url} [@{u1id}] подверг(ла) {u2url} [@{u2id}]')#показать
                    when = int(datetime.timestamp(m.date))
                    days = int(re.findall(bio_attack_themes[trying_theme_index][2], t)[0].replace(' ', ''))
                    experience = re.findall(bio_attack_themes[trying_theme_index][1], t)[0].strip()
                    if ',' in experience:
                        experience = re.sub(r',', r'.', experience)
                    if 'k' in experience:
                        exp_int = int(
                            float(re.sub('k', '', experience)) * 1000)
                    else:
                        exp_int = int(experience)
                    pathogen_remaining = int(re.findall(bio_attack_themes[trying_theme_index][3], t)[0])
                    if pathogen_remaining <= states.auto_bioeb_pathogen_threshold and u1id == my_id:
                        states.auto_bioeb_sleep_interval = states.auto_bioeb_max_interval
                        logger.warning(f'Interval bioeb changed (slow down): {states.auto_bioeb_sleep_interval}')
                    elif u1id == my_id:
                        states.auto_bioeb_sleep_interval = states.auto_bioeb_min_interval
                        logger.debug(f'Interval bioeb changed (more fast): {states.auto_bioeb_sleep_interval}')
                    a = datetime.utcfromtimestamp(
                        when)+timedelta(days=int(days), hours=3)
                    do_int = datetime.timestamp(a)
                    do_txt = str(a.strftime("%d.%m.%y"))
                    if u1id > 0 and u2id > 0:
                        if db_sqlite3 and u1id == my_id:
                            try:
                                c.execute("INSERT INTO avocado(user_id,when_int,bio_str,bio_int,expr_int,expr_str) VALUES (?, ?, ?, ?, ?, ?)", (int(
                                    u2id), int(when), str(experience), int(exp_int), int(datetime.timestamp(a)), str(a.strftime("%d.%m.%y"))))
                                conn.commit()
                                logger.debug('success writen my attack')
                            except:
                                try:
                                    c.execute("UPDATE avocado SET when_int = :wh, bio_str = :xp, bio_int = :xpi, expr_int = :end, expr_str = :do WHERE user_id = :z AND when_int <= :wh;", {
                                              "wh": int(when), "xp": str(experience), "xpi": int(exp_int), "end": int(datetime.timestamp(a)), "do": str(a.strftime("%d.%m.%y")), "z": int(u2id)})
                                    conn.commit()
                                    logger.debug('success updated my attack')
                                except Exception as Err:
                                    logger.exception(f'err: {Err} avocado')
                        if db_sqlite3 and u1id != my_id:
                            try:
                                c.execute("INSERT INTO avocado(user_id,when_int,bio_str,bio_int,expr_int) VALUES (?, ?, ?, ?, ?)", (
                                    int(u2id), int(when), str(experience), int(exp_int), 0))
                                conn.commit()
                                logger.debug('success writen not my new bio attack')
                            except:
                                # NOTE: this maybe useful if you want sort database by bio-experience, but as S1S13AF7 said this
                                # can be like: in database you have +10k today, tomorrow it changed to +1...
                                # so... idk what next...
                                c.execute("UPDATE avocado SET when_int = :wh, bio_str = :xp, bio_int = :xpi WHERE user_id = :z", {
                                    "wh": int(when), "xp": str(experience), "xpi": int(exp_int), "z": int(u2id)})
                                conn.commit()
                                logger.debug('success updated not my new bio attack')
                        if db_pymysql:
                            try:
                                # from_infect 	who_id 	user_id 	profit 	until_infect 	until_str
                                d.execute("INSERT INTO `tg_bio_attack` (`who_id`, `user_id`, `from_infect`, `profit`, `until_infect`, `until_str`) VALUES (%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE from_infect=VALUES (from_infect),profit=VALUES (profit),until_infect=VALUES (until_infect),until_str = VALUES (until_str);", (int(
                                    u1id), int(u2id), int(when), str(experience), int(datetime.timestamp(a)), str(a.strftime("%d.%m.%y"))))
                                con.commit()
                                print(
                                    f"\nINSERT INTO .... ON DUPLICATE KEY UPDATE # [@{u1id}] => [@{u2id}]\n")
                            except Exception as Err:
                                logger.exception(f'err: {Err} (tg_bio_attack)')
                                # pass
                            try:
                                # user_id 	when 	profit
                                d.execute("INSERT INTO `tg_bio_users` (`user_id`, `when_int`, `profit`) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE when_int=VALUES (when_int),profit=VALUES (profit);", (int(
                                    u2id), int(when), str(experience)))
                                con.commit()
                            except Exception as Err:
                                logger.exception(f'err: {Err} (tg_bio_users)')
                                # pass
                        if u1id == my_id:
                            logger.success(
                                f'''{u1url} [@{u1id}] подверг(ла) {u2url} [@{u2id}] +{experience}, d: {days}''')
                        else:
                            logger.info(
                                f'''{u1url} [@{u1id}] подверг(ла) {u2url} [@{u2id}] +{experience}, d: {days}''')

        ####################################################################

        @client.on(events.NewMessage(outgoing=True, pattern=r'\.biofuck$'))
        async def cmd_bf(event):  # крч акуратно з цим,вдруг шо я нічо
            m = event.message
            when = int(datetime.timestamp(m.date))
            msg = '🤷'  # якщо нема кого то жри рандом.
            c.execute(
                f"SELECT * FROM `avocado` WHERE expr_int <= {when} ORDER BY expr_int,when_int ASC")
            e_info = list(c.fetchall())
            random.shuffle(e_info)  # more random for random and reduce risk get very immun target after restart
            count = len(e_info)
            if count < 2:
                nema = '🤷 рандом хавай.'
                await event.edit(nema)  # ред
                logger.warning(nema)
            else:
                pong = '✅ погнали...'
                states.auto_bioeb_stop = False
                await event.edit(pong)  # ред
                logger.info(f'є {count} потенційних пацієнтів. спробуєм їх сожрать')
                for row in e_info:
                    if states.auto_bioeb_stop:
                        logger.warning('auto bioeb stopped')
                        await event.reply('stopped')
                        break
                    rs = float(random.uniform(states.auto_bioeb_sleep_interval[0], states.auto_bioeb_sleep_interval[1]))  # скільки спим: random
                    eb = f'Биоеб {row[0]}'  # повідомлення.
                    m = await event.reply(eb)
                    await asyncio.sleep(3.3)
                    await client.delete_messages(event.chat_id, m.id)
                    logger.debug(f'bioeb sleep: {rs}s')
                    await asyncio.sleep(rs)

        ####################################################################

        @client.on(events.NewMessage(outgoing=True, pattern=r'\.biofuck stop$'))
        async def stop_bioeb(event):
            states.auto_bioeb_stop = True
            await event.edit('Trying stop...')  # ред

        @client.on(events.NewMessage(pattern='🌡 У вас горячка вызванная'))
        async def need_h(event):
            m = event.message
            # reply = await client.get_messages(m.peer_id, ids=m.reply_to.reply_to_msg_id)
            # logger.debug(reply)
            if m.sender_id != 6333102398:
                pass
            elif a_h and m.mentioned:
                # нада хил
                ah = await message_q(  # отправляет сообщение боту
                    "Хил",
                    6333102398,
                    mark_read=True,
                    delete=False,
                )
                states.stats_medkit += 1
                logger.debug(ah.text)
                logger.warning('Used medkit')
            elif m.mentioned:
                # alternative method: just waiting, this reduce bio-res usage
                states.auto_bioeb_sleep_interval = (3600, 3600)
                logger.warning('Waiting for infection release... [For skip just bioeb somebody]')

        ####################################################################
        @client.on(events.NewMessage(outgoing=True, pattern=r'\.bstat$'))
        async def bio_stat(event):
            msg = "Session stats:\n" \
                f"Medkit usage: {stats_medkit}"
            await event.edit(msg)

        @client.on(events.NewMessage(outgoing=True, pattern='.l2f'))
        async def cmd_l2f(event):  # Local->file/{id}.sqlite
            msg = 'для успішного виконання повинно бути обидві бази True'
            if db_pymysql:
                try:
                    d.execute(
                        "SELECT * FROM `tg_iris_zarazy` WHERE who_id = %d ORDER BY when_int;" % int(my_id))
                    bz_info = d.fetchall()  # получить
                    count = len(bz_info)
                    if count == 0:
                        msg = '🤷 інфа нема.'
                        print(msg)
                    else:
                        saved = 0
                        for row in bz_info:
                            print(row)
                            id_user = int(row["user_id"])
                            bio_int = int(row["bio_int"])
                            bio_str = str(row["bio_str"])
                            when_int = int(row["when_int"])
                            expr_int = int(row["expr_int"])
                            # .2024->.24
                            expr_str = str(
                                re.sub(r'.20', r'.', row["expr_str"]))
                            # fix для любителів мінять його
                            user_url = str(
                                f'tg://openmessage?user_id={id_user}')
                            if db_sqlite3:
                                try:
                                    c.execute("INSERT INTO zarazy (user_id,when_int,bio_str,bio_int,expr_int,expr_str) VALUES (?, ?, ?, ?, ?, ?)", (int(
                                        id_user), int(when_int), str(bio_str), int(bio_int), int(expr_int), str(expr_str)))
                                    conn.commit()
                                    saved += 1
                                except:
                                    try:
                                        c.execute("UPDATE zarazy SET when_int = :wh, bio_str = :xp, bio_int = :xpi, expr_int = :end, expr_str = :do WHERE user_id = :z AND when_int <= :wh;", {
                                                  "wh": int(when_int), "xp": str(bio_str), "xpi": int(bio_int), "end": int(expr_int), "do": str(expr_str), "z": int(id_user)})
                                        conn.commit()
                                    except Exception as Err:
                                        print(f'err: {Err} zarazy')
                                msg = f"{saved} із {count}"
                            else:
                                msg = 'для успішного виконання повинно бути обидві бази True'
                except Exception as Err:
                    logger.exception(f'err: {Err} zarazy localhost')
                    msg = Err
            m = await event.reply(msg)
            await asyncio.sleep(5)
            await client.delete_messages(event.chat_id, [event.id, m.id])

        @client.on(events.NewMessage(outgoing=True, pattern='.ping'))
        async def cmd_ping(event):
            # Say "pong!" whenever you send "!ping", then delete both messages
            time_start = time.time()
            m = await event.reply('pong!')
            time_end = time.time()
            delta = int(round((time_end - time_start) * 1000, 0))
            await m.edit(f'pong message sending time: {delta} ms')
            await asyncio.sleep(10)
            await client.delete_messages(event.chat_id, [event.id, m.id])

        await client.run_until_disconnected()

asyncio.run(main())
