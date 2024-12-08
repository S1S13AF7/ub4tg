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
