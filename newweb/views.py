from quart import Quart, websocket, redirect, render_template, url_for
from modules.asyncdb import asyncDB
from modules.redis import RedisClass


webapp = Quart(__name__)


@webapp.context_processor
async def _onlineplayers():
    async def onlineplayers():
        pnames = await webapp.db.fetchall(f'SELECT playername from players where online = True')
        playernamelist = []
        for player in iter(pnames):
            playernamelist.append(player['playername'])
        playernames = ', '.join(playernamelist)
        count = len(playernames)
        return {'count': count, 'names': playernames}
    return dict(onlineplayers=await onlineplayers())


@webapp.context_processor
async def _instancedata():
    async def instancedata():
        return await webapp.db.fetchall(f'SELECT name, isup, needsrestart, restartcountdown, enabled FROM instances ORDER BY name')
    return dict(instancedata=iter(await instancedata()))


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
