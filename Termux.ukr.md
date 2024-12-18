# установка ub4tg – Termux
<br/>

У вас має бути сам Termux<br/>
Встановлений із github або F-Droid<br/>

Якщо щойно встановили дать доступ до пам'яті.<br/>

Вводим у Termux:<br/>
`pkg install openssl python3 git termux-api`<br/>
після установки клонуємо: <br/>
`git clone https://github.com/S1S13AF7/ub4tg`<br/>
Установка requirements:<br/>
`cd ub4tg && pip3 install -r requirements.txt`<br/>

запуск бота: <br/>
`python3 ubot.py`<br/>
якщо пише 
mkdir: cannot create directory ‘/sdcard/ub4tg’: Permission denied 
перевірте чи дали доступ на пам'ять. і заново запуск.<br/>

