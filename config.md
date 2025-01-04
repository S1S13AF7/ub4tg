# config
<br/>

config у цій версії бота називається просто conf.json (хз чому скоротив, але то вже неважно)

Структура конфіґа приблизно наступна (але не обов'язково така):<br/>

```json
{
	"api_id": 0000000,
	"api_hash": "blahblahblahblahblahblahblahblah",
	"timezone": "Europe/Kiev",
	"a_404_patient": true,
	"db_pymysql": false,
	"db_sqlite3": true,
	"wakelock": false,
	"a_404_p": true,
	"farm": true,
	"mine": true,
	"a_f": false,
	"a_h": true,
	"i2a": true,
	"ch_id": 0
}
```


api_id & api_hash - обов'язкові параметри; 
db_pymysql - чи юзать MySQL? (default: False); 
a_404_p - автоматично сожрать пацієнта якщо не знайдено; 
a_404_patient - стара назва (я і її вкоротив. не використовується);
ch_id - ід чата де відбувається магія. виставиться само якщо був 0; 
wakelock - чи юзать wakelock (у мене від нього нема толку); 
farm & mine - чи юзать/врубать ферму & майн;
a_f - не використовується ; 
a_h - врубать авто хил? ;
i2a - iris2avocado - мало/матиме сенс коли гра іріса працю(вала/ватиме);

Мінімально необхідний набір параметрів це власне api_id і api_hash,
Але у деяких версій цього бота він може відрізнятись. 

