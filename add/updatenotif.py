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
                commits = os.popen(
                    "git log --pretty=format:'%h %s%n%b' HEAD..origin/$(git rev-parse --abbrev-ref HEAD)").read()
                if len(commits) <= 5:
                    logger.info('updates not found, nothing to do')
                else:
                    os.system(
                        f"termux-notification --title 'ub4tg: update avalaible!' --content 'For apply tap button Get update and restart bot\nChanges:\n{commits}' --button1 'Get update' --button1-action 'cd {cwd}; git pull'")
            else:
                os.system(
                    "termux-toast '[ub4tg]: failed fetching update, maybe connection error, check console log for more info'")
        else:
            logger.warning(
                'For getting updates via notifications, you should:')
            logger.warning('pkg install termux-api')
            logger.warning(
                'download the apk: https://f-droid.org/repo/com.termux.api_51.apk')
        logger.debug('next update will be check after 6 hours')
        await asyncio.sleep(6 * 60 * 60)
