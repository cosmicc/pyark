from quart import Quart, websocket, redirect, render_template, url_for
from modules.asyncdb import asyncDB
from modules.redis import RedisClass
from modules.timehelper import Now, Secs


webapp = Quart(__name__)


@webapp.context_processor
async def _otherplayercounts():
    async def otherplayercounts():
        wcount = await webapp.db.fetchall(f"""SELECT COUNT(*) FROM players WHERE banned = '' AND lastseen >= '{Now() - Secs["1week"]}'""")
        mcount = await webapp.db.fetchall(f"""SELECT COUNT(*) FROM players WHERE banned = '' AND lastseen >= '{Now() - Secs["1month"]}'""")
        return {'week': wcount, 'month': mcount}
    return dict(otherplayercounts=await otherplayercounts())


@webapp.context_processor
async def _dailyplayers():
    async def dailyplayers():
        pnames = await webapp.db.fetchall(f"""SELECT playername FROM players WHERE banned = '' AND lastseen >= '{Now() - Secs["1day"]}' ORDER BY lastseen DESC""")
        playernamelist = []
        for player in iter(pnames):
            playernamelist.append(player['playername'].title())
        playernames = ', '.join(playernamelist)
        count = len(playernamelist)
        return {'count': count, 'names': playernames}
    return dict(dailyplayers=await dailyplayers())


@webapp.context_processor
async def _onlineplayers():
    async def onlineplayers():
        pnames = await webapp.db.fetchall(f'SELECT playername from players where online = True ORDER BY lastconnect DESC')
        playernamelist = []
        for player in iter(pnames):
            playernamelist.append(player['playername'].title())
        playernames = ', '.join(playernamelist)
        count = len(playernamelist)
        return {'count': count, 'names': playernames}
    return dict(onlineplayers=await onlineplayers())


@webapp.context_processor
async def _instancedata():
    async def instancedata():
        return await webapp.db.fetchall(f'SELECT name, isup, needsrestart, restartcountdown, enabled, steamlink, activeplayers FROM instances ORDER BY name')
    return dict(instancedata=iter(await instancedata()))


@webapp.context_processor
async def _gallerylinks():
    async def gallerylinks():
        return iter(await webapp.db.fetchall(f'SELECT playername, link FROM gallerylinks ORDER BY id ASC'))
    return dict(gallerylinks=iter(await gallerylinks()))


@webapp.before_serving
async def db_pool():
    webapp.db = asyncDB()
    await webapp.db.connect(min=3, max=20, timeout=240)


@webapp.before_serving
async def redis_pool():
    Redis = RedisClass()
    webapp.redis = Redis.redis


@webapp.after_serving
async def db_close():
    await webapp.db.close()


@webapp.route('/')
async def index():
    return await render_template('home.html')


@webapp.websocket('/ws')
async def ws():
    while True:
        await websocket.send('hello')
