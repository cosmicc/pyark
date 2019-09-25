from quart import Quart, websocket, redirect, render_template, url_for
from modules.asyncdb import asyncDB
from modules.redis import RedisClass


webapp = Quart(__name__)


@webapp.context_processor
def _gettimezones():
    def ui_gettimezones():
        pass
    return dict(ui_gettimezones=ui_gettimezones)


@webapp.context_processor
def _getinstancedata():
    def getinstancedata():
        return iter(webapp.db.fetchall(f'SELECT * FROM instances'))
    return dict(getinstancedata=_getinstancedata)


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
