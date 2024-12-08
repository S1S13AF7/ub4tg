This is fork from: https://github.com/S1S13AF7/ub4tg  
Main changes:  
* removed iris compatibility
* added loguru
* other some improvments  
  
before start, create config.json file with this content:  
```json
{
  "api_id": 0000000,
  "api_hash": "1234567890",
  "timezone": "Europe/[Your_city]",
  "db_pymysql": false,
  "db_sqlite3": true,
  "a_h": true
}
```
___
# ub4tg – юзербот для телеграма.
покищо лише пінґ-понґ
і збереження хто кого заразив 
<br/>

БД може бути sqlite і/або MySQL (та хоч дві зразу) <br/>
переключається прямо в файлах ботів: <br/>

db_pymysql = True#set True or False <br/>
db_sqlite3 = True#set True or False <br/>

У базу sqlite3 зберігає лише кого заразив сам<br/>
У базу MySQL намагаємось зберігать все підряд<br/>

Якщо у вас ще нема MySQL і/або нехочете зберігать чужих, тоді просто поставте <br/>
db_pymysql = False

# dispatcher – звичайний бот (не юб)
Використовувати "диспетчер" є сенс, якщо:<br/>
> у вас є база MySQL на http://localhost/<br/>
> у вас кілька акків підключено до 1 бд<br/>

спільне використання однієї бд sqlite кількома ботами створює проблему db is locked<br/>
тому у випадку з кількома юзерами у кожного своя sqlite база {id}.sqlite<br/>
а от MySQL в свою чергу може бути спільна для всіх ботів і юзерботів.<br/>
тобто якщо база спільна то достатньо одного "диспетчера" для всіх.<br/>
Але якщо юзаєте лише sqlite то і "диспетчер" вам нафіг нетреба.<br/>
