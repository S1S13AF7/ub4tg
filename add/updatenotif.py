from loguru import logger
import os
import asyncio


async def git_notifications_update():
    logger.info('module for checking updates started')
    cwd = os.getcwd()
    os.chdir(cwd)
    while True:
        termux_api = os.system('termux-api-start')
        if termux_api == 0:
            logger.info('Checking for updates...')
            fetching_git = os.system('git fetch')
            if fetching_git == 0:
                os.system("printf 'For apply tap button Get update and restart bot\nChanges:\n' > upd_info")
                commits = os.popen(
                    "git log --pretty=format:'%h %s%n%b' HEAD..origin/$(git rev-parse --abbrev-ref HEAD) | tee upd_info").read()
                if len(commits) <= 5:
                    logger.info('updates not found, nothing to do')
                else:
                    os.system(
                        f"cat upd_info | termux-notification -i ub4tgupd --title 'ub4tg: update avalaible!' --button1 'Get update' --button1-action 'termux-notification-remove ub4tgupd'; cd {cwd}; git pull; termux-toast 'ub4tg updated, now restart it for apply update'")
            else:
                os.system(
                    "termux-toast '[ub4tg]: failed fetching update, maybe connection error, check console log for more info'")
        else:
            logger.warning(
                'For getting updates via notifications, you should:')
            logger.warning('pkg install termux-api')
            logger.warning(
                'download the apk: https://f-droid.org/repo/com.termux.api_51.apk')
        logger.debug('next update will be check after 1 hours')
        await asyncio.sleep(3600)
