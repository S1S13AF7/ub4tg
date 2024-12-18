Termux apk here: https://f-droid.org/repo/com.termux_1020.apk  
Termux:API apk if you want get notifications about updates of this code: https://f-droid.org/repo/com.termux.api_51.apk  

0. Optional step: allow permission on storage in Termux before start, after this, step 3-4 can be skipped
1. Run termux and enter this oneliner:  
`pkg install openssl python3 git termux-api && git clone https://github.com/S1S13AF7/ub4tg && cd ub4tg && pip3 install -r requirements.txt`  
If pkg upgrade ask overwrite some files - press Y
2. Now after this you can run bot:  
`./run` or `python3 ubot.py`
3. Termux will ask permission on storage, allow it. Restart Termux (enter `quit` or press CTRL+d)
4. Run bot again:  
`cd ub4tg; ./run`
5. Follow first time setup, it creates config for you and asks some questions
6. Enjoy
7. If you get some warnings about future events: sync your time in Android settings "date and time" and switch "network time" off/on

For start bot again (if Termux restarted) just enter:  
`cd ub4tg; ./run`  

