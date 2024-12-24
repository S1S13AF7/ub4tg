# Termux
<br/>
Termux apk: https://f-droid.org/repo/com.termux_1020.apk<br/>
Termux:API: https://f-droid.org/repo/com.termux.api_51.apk<br/>
(або новіші)<br/>

Якщо щойно встановили дать доступ до пам'яті.<br/>

Вводим у Termux:<br/><br/>
`pkg install openssl python3 git termux-api`<br/><br/>
після установки клонуємо: <br/><br/>
`git clone https://github.com/S1S13AF7/ub4tg`<br/><br/>
Установка requirements:<br/><br/>
`cd ub4tg && pip3 install -r requirements.txt`<br/><br/>

запуск бота: <br/>
`python3 ubot.py`<br/>
якщо пише 
mkdir: cannot create directory ‘/sdcard/ub4tg’: Permission denied 
перевірте чи дали доступ на пам'ять. і заново запуск.<br/>

запуск кількох копій бота з різними авторизаціями:<br/>
просто скопіюйте папку з ботом (перейменувать)<br/>
(із скопійованої папки видалить .session буде інша)<br/>

