# -*- coding: utf-8 -*-
# https://docs-python.ru/packages/telegram-klient-telethon-python/	<-info
import asyncio

from datetime import datetime, timedelta
# from telethon.sync import TelegramClient
from telethon import TelegramClient, events, utils
from telethon import functions, types

import sys
import os
import json
import re
import random
import time

import pymysql
import pymysql.cursors

import sqlite3
from loguru import logger
from collections import Counter
logger.remove()
logger.level("DEBUG", color='<magenta>')
logger.add(sys.stderr, level="DEBUG")
is_termux = os.environ.get('TERMUX_APP__PACKAGE_NAME') or os.environ.get('TERMUX_APK_RELEASE')
if is_termux:
    logger.info('Termux detected, checking permissions...')
    logger.info('If you want prevent killing termux by android, get wake lock: check your notifications, find termux app and press "ACQUIRE WAKELOCK"')
    logger.warning('This can cause battery drain!')
    if (os.environ.get('TERMUX_APP__APK_RELEASE') or os.environ.get('TERMUX_APK_RELEASE')) not in ('F_DROID', 'GITHUB'):
        logger.warning('You use not f-droid/github apk release, it may have problems...')
        logger.warning('F-droid termux release here: https://f-droid.org/en/packages/com.termux/')
        logger.warning('Github termux release here: https://github.com/termux/termux-app/releases')
    if int(os.environ.get('TERMUX_VERSION').split('.')[1]) < 118:
        logger.warning('You use old version of termux, highly recommended that you update to v0.118.0 or higher ASAP for various bug fixes, including a critical world-readable vulnerability')
    if os.access('/sdcard', os.W_OK):
        logger.success('permission to write on internal storage allowed')
    else:
        logger.warning('permission denied to write on internal storage')
        logger.info('trying get permission...')
        os.system('termux-setup-storage')
        logger.info('Restart termux [Press CTRL+D or command "exit"]')
        sys.exit(0)

# Название сессии
sessdb = 'tl-ub'
default_directory = ''
default_config_file_path = 'config.json'
treat_as_true = ('true', '1', 't', 'y', 'yes', 'yeah', 'yup', 'certainly', 'uh-huh')
if is_termux:
    default_directory = '/sdcard/ub4tg'
    os.system(f'mkdir -p {default_directory}')
    default_config_file_path = f'{default_directory}/config.json'
if not os.path.exists(default_config_file_path):
    logger.info('config not found, first launch setup...')
    api_id = int(input('enter api_id from https://my.telegram.org/ : '))
    api_hash = input('enter api_hash from https://my.telegram.org/ : ')
    timezone = input('enter timezone, format is Country/City: ')
    db_pymysql = False
    db_sqlite3 = True
    a_h = input('enable automatic use medkit? [y/n]: ').lower() in treat_as_true
    a_404_patient = input('enable automatic bioeb if victim not found or expired? It will be trigger on "Жертва не найдена" [y/n]: ').lower() in treat_as_true
    new_config = {'api_id': api_id,
                  'api_hash': api_hash,
                  'timezone': timezone,
                  'db_pymysql': db_pymysql,
                  'db_sqlite3': db_sqlite3,
                  'a_h': a_h,
                  'a_404_patient': a_404_patient}
    with open(default_config_file_path, "w") as configfile:
        json.dump(new_config, configfile, indent=4)

with open(default_config_file_path, "r") as configfile:
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
a_404_patient = config.a_404_patient


class states:
    auto_bioeb_sleep_interval = (6, 66)  # the default on (re)start
    auto_bioeb_pathogen_threshold = 5  # these pathogens will be saved +- 1
    auto_bioeb_min_interval = (0.666, 3.666)  # for fast leak pathogen
    auto_bioeb_max_interval = (71, 121)  # waiting for more pathogen
    # Default strategy mean: you have 4-5 pathogens when auto bioeb is enabled, pathogen overflow reduced
    auto_bioeb_stop = True
    where_send_check_avocado = None
    last_sent_bioeb = 0  # for measure time between reply avocado and bioeb
    last_reply_bioeb_avocado = 0  # same as above
    avocado_reply_timeout = 3  # increase interval if lag more than this timeout in secs
    stats_medkit = 0
    stats_most_infect_spam_chats = Counter()


@logger.catch
async def main():
    async with TelegramClient(sessdb, api_id, api_hash, connection_retries=300, request_retries=10,) as client:
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
            logger.debug('sqlite3 database connecting...')
            if is_termux:
                conn = sqlite3.connect(f"{default_directory}/{my_id}.sqlite")
            else:
                conn = sqlite3.connect(f"{my_id}.sqlite")  # покласти базу рядом
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
            c.execute('''CREATE TABLE IF NOT EXISTS avocado_exclude	(
                        user_id	INTEGER NOT NULL DEFAULT 0 UNIQUE,
                        reason VARCHAR
                        )''')
            conn.commit()
            logger.debug('sqlite3 database initialized')

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
                            pass
                        else:
                            user_id = int(user['user_id'])
                            print(f'{url} in db: @{user_id}')
                    except:
                        pass
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

        @client.on(events.NewMessage(pattern='.*йобнув.*|.*подверг(ла)?.*|.*infected.*|.*сикди.*|.*насрал.*|.*выебал.*|.*за допомогою довіреності.*|.*by authorization infected.*|.*при помощи анонимуса атаковала.*'))
        @logger.catch
        async def podverg_a(event):
            logger.debug('bio attack detected')
            # хто там кого йобнув(ла)
            m = event.message
            cinfo = await m.get_chat()
            chat_name = cinfo.title
            logger.debug(f"in chat '{chat_name}'")
            states.stats_most_infect_spam_chats[chat_name] += 1
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
                # "Сексуальная индустрия" theme
                (r'<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">.*</a> выебал.+<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">',
                 r"кончила ([0-9\.\,k]+)",
                 r' ещё ([0-9\ ]+) д.*',
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
                logger.debug('not avocado infection, skipping')
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
                    logger.warning(
                        'theme not found, showing original message: ' + m.text)
                logger.debug(str(r))
                if r:
                    u1url = r[0][0]
                    u2url = r[0][1]
                    u1id = await get_id(u1url)
                    u2id = await get_id(u2url)
                    bio_excludes = [x[0] for x in c.execute('select user_id from avocado_exclude').fetchall()]
                    # print(f'{u1url} [@{u1id}] подверг(ла) {u2url} [@{u2id}]')#показать
                    when = int(datetime.timestamp(m.date))
                    days = int(re.findall(bio_attack_themes[trying_theme_index][2], t)[
                               0].replace(' ', ''))
                    experience = re.findall(
                        bio_attack_themes[trying_theme_index][1], t)[0].strip()
                    if ',' in experience:
                        experience = re.sub(r',', r'.', experience)
                    if 'k' in experience:
                        exp_int = int(
                            float(re.sub('k', '', experience)) * 1000)
                    else:
                        exp_int = int(experience)
                    pathogen_remaining = int(re.findall(
                        bio_attack_themes[trying_theme_index][3], t)[0])
                    if pathogen_remaining <= states.auto_bioeb_pathogen_threshold and u1id == my_id:
                        states.auto_bioeb_sleep_interval = states.auto_bioeb_max_interval
                        logger.warning(
                            f'Interval bioeb changed (slow down): {states.auto_bioeb_sleep_interval}')
                    elif u1id == my_id:
                        states.auto_bioeb_sleep_interval = states.auto_bioeb_min_interval
                        logger.debug(
                            f'Interval bioeb changed (more fast): {states.auto_bioeb_sleep_interval}')
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
                                logger.debug(
                                    '[new] success writen my bio attack')
                            except:
                                try:
                                    c.execute("UPDATE avocado SET when_int = :wh, bio_str = :xp, bio_int = :xpi, expr_int = :end, expr_str = :do WHERE user_id = :z AND when_int <= :wh;", {
                                              "wh": int(when), "xp": str(experience), "xpi": int(exp_int), "end": int(datetime.timestamp(a)), "do": str(a.strftime("%d.%m.%y")), "z": int(u2id)})
                                    conn.commit()
                                    logger.debug(
                                        '[upd] success updated my bio attack')
                                except Exception as Err:
                                    logger.exception(f'err: {Err} avocado')
                            states.last_reply_bioeb_avocado = time.time()
                        if db_sqlite3 and u1id != my_id and u2id not in bio_excludes:
                            try:
                                c.execute("INSERT INTO avocado(user_id,when_int,bio_str,bio_int,expr_int) VALUES (?, ?, ?, ?, ?)", (
                                    int(u2id), int(when), str(experience), int(exp_int), 0))
                                conn.commit()
                                logger.debug('[new] success writen bio attack')
                            except:
                                # NOTE: this maybe useful if you want sort database by bio-experience, but as S1S13AF7 said this
                                # can be like: in database you have +10k today, tomorrow it changed to +1...
                                # so... idk what next...
                                c.execute("UPDATE avocado SET when_int = :wh, bio_str = :xp, bio_int = :xpi WHERE user_id = :z AND when_int < :wh AND expr_int < :wh", {
                                    "wh": int(when), "xp": str(experience), "xpi": int(exp_int), "z": int(u2id)})
                                conn.commit()
                                logger.debug(
                                    '[upd] success updated bio attack')
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
                                f'''me подверг(ла) {u2url} [@{u2id}] +{experience}, d: {days}''')
                        else:
                            logger.info(
                                f'''{u1url} [@{u1id}] подверг(ла) {u2url} [@{u2id}] +{experience}, d: {days}''')
                            if u2id in bio_excludes:
                                logger.debug(f'{u2id} not added: excluded')

        ####################################################################

        @client.on(events.NewMessage(outgoing=True, pattern=r'\.biofuck$'))
        async def cmd_bf(event):  # крч акуратно з цим,вдруг шо я нічо
            if states.auto_bioeb_stop is False:
                await event.edit('biofucking already runned!')
                return
            m = event.message
            when = int(datetime.timestamp(m.date))
            msg = '🤷'  # якщо нема кого то жри рандом.

            def get_some_patients(limit=1000):
                count = int(c.execute(
                    f"SELECT COUNT(*) FROM `avocado` WHERE expr_int <= {when} ORDER BY expr_int,when_int ASC LIMIT {limit}").fetchone()[0])
                patients = list(c.execute(
                    f"SELECT * FROM `avocado` WHERE expr_int <= {when} ORDER BY expr_int,when_int ASC LIMIT {limit}").fetchall())
                bio_excludes = [x[0] for x in c.execute('select user_id from avocado_exclude').fetchall()]
                for p in patients:
                    if p[0] in bio_excludes:
                        logger.warning(f'skipping patient {p[0]}, excluded from bioebinng')
                        patients.remove(p)

                return count, patients

            count, e_info = get_some_patients()
            # more random for random and reduce risk get very immun target after restart
            random.shuffle(e_info)
            if count < 2:
                nema = '🤷 рандом хавай.'
                await event.edit(nema)  # ред
                logger.warning(nema)
            else:
                pong = '✅ погнали...'
                states.auto_bioeb_stop = False
                await event.edit(pong)  # ред
                logger.info(
                    f'є {count} потенційних пацієнтів. спробуєм їх сожрать')
                while states.auto_bioeb_stop is False:
                    # скільки спим: random
                    rs = float(random.uniform(
                        states.auto_bioeb_sleep_interval[0], states.auto_bioeb_sleep_interval[1]))
                    eb = f'Биоеб {e_info[0][0]}'  # повідомлення.
                    m = await event.reply(eb)
                    e_info.pop(0)
                    remaining_in_stack = len(e_info)
                    logger.info(
                        f'remaining patiences in current stack: {remaining_in_stack}')
                    random.shuffle(e_info)
                    states.last_sent_bioeb = int(datetime.timestamp(m.date))
                    if states.last_reply_bioeb_avocado == 0:  # reduce negative ping
                        states.last_reply_bioeb_avocado = int(
                            datetime.timestamp(m.date))
                    await asyncio.sleep(3.3)
                    await client.delete_messages(event.chat_id, m.id)
                    delta_avocado = states.last_reply_bioeb_avocado - states.last_sent_bioeb
                    if delta_avocado < 0:
                        delta_avocado = delta_avocado * -1
                    logger.debug(
                        f'latency avocado reply: {delta_avocado} secs')
                    if delta_avocado > states.avocado_reply_timeout:
                        interval_with_lag = rs + random.uniform(9.18299148, 40.9201412499)
                        logger.debug(
                            f'bioeb sleep [increased, because avocado have lag]: {interval_with_lag}s')
                        await asyncio.sleep(interval_with_lag)
                    else:
                        logger.debug(f'bioeb sleep: {rs}s')
                        await asyncio.sleep(rs)
                    if len(e_info) <= 0:
                        count, e_info = get_some_patients()
                        if count < 2:
                            event.reply('Закончились, рандом хавай')
                            logger.warning('you are eaten all')
                            break
                        random.shuffle(e_info)
                        e_count = len(e_info)
                        logger.success(
                            f'db refresh: {count} patiences; in stack: {e_count}')

                states.auto_bioeb_stop = True
                logger.warning('auto bioeb stopped')
                await event.reply('stopped')

        ####################################################################

        @client.on(events.NewMessage(outgoing=True, pattern=r'\.biofuck stop$'))
        async def stop_bioeb(event):
            states.auto_bioeb_stop = True
            await event.edit('Trying stop...')  # ред

        @client.on(events.NewMessage(outgoing=True, pattern=r'\.bioexclude'))
        async def add_bioeb_exclude(event):
            reason = event.text.split(' ', 1)[1] or None
            reply = await client.get_messages(event.peer_id, ids=event.reply_to.reply_to_msg_id)
            if not reply.entities:
                await event.edit('ids not found')
                return
            t = reply.raw_text
            h = utils.sanitize_parse_mode(
                'html').unparse(t, reply.entities)  # HTML
            r = re.findall(r'<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">', h)
            insertion_status = []
            for link in r:
                user_id = await get_id(link)
                try:
                    c.execute("INSERT INTO avocado_exclude(user_id, reason) VALUES (?, ?)", (user_id, reason))
                    insertion_status.append(f'{user_id}: ok')
                except:
                    insertion_status.append(f'{user_id}: exists')
            conn.commit()
            insertion_status = '\n'.join(insertion_status)
            await event.edit(f'{insertion_status}\nreason: {reason}')

        @client.on(events.NewMessage(outgoing=True, pattern=r'\.bioebmass$'))
        async def bioeb_mass(event):
            reply = await client.get_messages(event.peer_id, ids=event.reply_to.reply_to_msg_id)
            when = int(datetime.timestamp(event.date))
            t = reply.raw_text
            h = utils.sanitize_parse_mode(
                'html').unparse(t, reply.entities)  # HTML
            r_as_list = []
            r = re.findall(r'<a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">|(@\d+)', h)
            for x in r:
                r_as_list.extend(x)
            r = r_as_list

            if r == []:
                await event.edit('nothing to do: ids not found')
                return

            def filter_bioeb(victims_ids):
                bio_excludes = [x[0] for x in c.execute('SELECT user_id FROM avocado_exclude').fetchall()]
                filted_victims = []
                for v in victims_ids:
                    if v in bio_excludes:
                        logger.warning(f'skipping patient {v}, excluded from bioebinng')
                    elif c.execute(f'SELECT user_id FROM avocado WHERE expr_int >= {when} and user_id == {v}').fetchone():
                        logger.warning(f'skipping patient {v}, already eaten')
                    else:
                        filted_victims.append(v)

                return list(set(filted_victims))
            bioebbing_ids = []
            for i in r:
                if i == '':
                    continue
                if i.startswith('@'):
                    bioebbing_ids.append(int(i.replace('@', '')))
                else:
                    bioebbing_ids.append(await get_id(i))
            bioebbing_ids = filter_bioeb(bioebbing_ids)
            bioebbing_len = len(bioebbing_ids)
            if bioebbing_len == 0:
                await event.edit('already eaten or excluded')
                return
            await event.edit(f'trying eat {bioebbing_len} patients...')
            for patient in bioebbing_ids:
                await asyncio.sleep(random.uniform(1.234, 4.222))
                await event.respond(f'биоеб {patient}')

        @client.on(events.NewMessage(outgoing=True, pattern=r'\.biostealbackup'))
        async def bio_steal_backup(event):
            cmd = event.text.split(' ', 1)
            if len(cmd) > 1:
                cmd = cmd[1].lower()
            if cmd == 'me':
                logger.info('Requested steal yourself backup...')
            else:
                logger.info('Stealing backup...')
            reply = await client.get_messages(event.peer_id, ids=event.reply_to.reply_to_msg_id)
            await event.edit('Downloading file...')
            file_path = await reply.download_media(file=f"{default_directory}")
            logger.success(f'backup file saved to {file_path}')
            victims = None
            raw_victims = None
            file_format = None
            with open(file_path, 'r') as stealed_backup:
                if file_path.lower().endswith('.json'):
                    victims = json.load(stealed_backup)
                    file_format = 'json'
                    await event.edit('Processing json victims...')
                elif file_path.lower().endswith('.txt'):
                    raw_victims = stealed_backup.readlines()
                    file_format = 'txt'
                    await event.edit('Processing raw txt victims...')
                else:
                    await event.edit('Format not supported, avalaible: txt, json')
                    return

            added = 0
            rejected = 0
            my_victims_ids = []
            if file_format == 'json':
                for v in victims:
                    user_id = int(v['user_id'])
                    profit = v['profit']
                    when = v['from_infect']
                    expr = v['until_infect']
                    if cmd == 'me':
                        my_victims_ids.append(user_id)
                        c.execute("INSERT OR REPLACE INTO avocado(user_id,when_int,bio_str,bio_int,expr_int) VALUES (?, ?, ?, ?, ?)",
                                  (int(user_id), int(when), str(profit), int(profit), int(expr)))
                        added += 1
                    else:
                        if not c.execute(f'SELECT user_id FROM avocado WHERE user_id == {user_id}').fetchone() and not c.execute(f'SELECT user_id FROM avocado_exclude WHERE user_id == {user_id}').fetchone():
                            c.execute("INSERT INTO avocado(user_id,when_int,bio_str,bio_int,expr_int) VALUES (?, ?, ?, ?, ?)",
                                      (int(user_id), int(when), str(profit), int(profit), 0))
                            added += 1
                        else:
                            rejected += 1
            elif file_format == 'txt':
                when = int(datetime.timestamp(event.date))
                for raw_v in raw_victims:
                    if raw_v == '':
                        continue
                    user_id = re.findall(r'tg://openmessage\?user_id=(\d+)', raw_v)
                    if not user_id:
                        continue
                    user_id = int(user_id[0])
                    profit = re.findall(r'([0-9\.\,k]+) опыта', raw_v)
                    if not profit:
                        continue
                    profit = profit[0]
                    if ',' in profit:
                        profit = re.sub(r',', r'.', profit)
                    if 'k' in profit:
                        profit_int = int(
                            float(re.sub('k', '', profit)) * 1000)
                    else:
                        profit_int = int(profit)
                    if not c.execute(f'SELECT user_id FROM avocado WHERE user_id == {user_id}').fetchone() and not c.execute(f'SELECT user_id FROM avocado_exclude WHERE user_id == {user_id}').fetchone():
                        c.execute("INSERT INTO avocado(user_id,when_int,bio_str,bio_int,expr_int) VALUES (?, ?, ?, ?, ?)",
                                  (int(user_id), int(when), str(profit), int(profit_int), 0))
                        added += 1
                        logger.debug(f'added {user_id} - {profit_int}')
                    else:
                        rejected += 1
            conn.commit()
            logger.success('backup success stealed')
            if cmd == 'me':
                my_victims_ids = tuple(my_victims_ids)
                result = c.execute(f'UPDATE avocado SET expr_int = 0 WHERE user_id NOT IN {my_victims_ids}').fetchall()
                conn.commit()
                logger.success('database rebased')
            del my_victims_ids
            del victims  # free memory
            del raw_victims
            if cmd == 'me':
                rebased = len(result)
                await event.edit(f'Success added/updated {added} patients\nOther {rebased} patients reset to 0')
                del result
            else:
                await event.edit(f'Success added {added} new patients\nRejected or exists: {rejected}')

        @client.on(events.NewMessage(outgoing=True, pattern=r'\.biocheck$'))
        async def set_default_check_chat(event):
            states.where_send_check_avocado = event.peer_id
            await event.edit('Checks will be send here')

        @client.on(events.NewMessage(pattern='.+Служба безопасности лаборатории'))
        # Организатор заражения: нада биоебнуть?
        async def iris_sb(event):
            # iris off bio 31.12.24
            m = event.message
            t = m.raw_text
            irises = [707693258, 5137994780,
                      5226378684, 5443619563, 5434504334]
            if m.sender_id not in irises:
                pass
            elif a_404_patient and len(m.entities) > 1 and states.where_send_check_avocado:
                h = utils.sanitize_parse_mode(
                    'html').unparse(t, m.entities)  # HTML
                r = re.findall(
                    r'Организатор заражения: <a href="(tg://openmessage\?user_id=\d+|https://t\.me/\w+)">', h)
                user_url = r[0]
                # user_id = await get_id(user_url)
                if r:
                    await asyncio.sleep(random.uniform(1, 2))
                    logger.info(f'auto checking iris -> avocado: {user_url}')
                    m = await client.send_message(states.where_send_check_avocado, f'.ч {user_url}')
                    await asyncio.sleep(random.uniform(1, 5))
                    await client.delete_messages(m.chat_id, m.id)

                ####################################################################

        @client.on(events.NewMessage(pattern='⏱?🚫 Жертва'))
        async def infection_not_found(event):
            m = event.message
            if m.sender_id != 6333102398:
                pass
            elif a_404_patient and m.mentioned:
                await asyncio.sleep(random.uniform(1.0001, 2.22394))
                result = await client(functions.messages.GetBotCallbackAnswerRequest(  # src https://tl.telethon.dev/methods/messages/get_bot_callback_answer.html
                    peer=m.peer_id,
                    msg_id=m.id,
                    game=False,  # idk why it works only when it false... 0_o
                    data=m.reply_markup.rows[0].buttons[0].data
                ))
                logger.info('trying eat patient')
                if result.message:
                    logger.info(f'avocado says: {result.message}')

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
                states.last_reply_bioeb_avocado = int(
                    datetime.timestamp(event.date))
                logger.debug(ah.text)
                logger.warning('Used medkit')
            elif m.mentioned:
                # alternative method: just waiting, this reduce bio-res usage
                states.auto_bioeb_sleep_interval = (3600, 3600)
                states.last_reply_bioeb_avocado = int(
                    datetime.timestamp(event.date))
                logger.warning(
                    'Waiting for infection release... [For skip just bioeb somebody]')

        ####################################################################
        @client.on(events.NewMessage(outgoing=True, pattern=r'\.bstat$'))
        async def bio_stat(event):
            stats_most_chats = states.stats_most_infect_spam_chats.most_common()
            msg = "Session stats:\n" \
                f"Medkit usage: {states.stats_medkit}\n" \
                f"Most common chats:\n" \
                f"{stats_most_chats}".replace(',', '\n')
            await event.edit(msg)

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
