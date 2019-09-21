from quart import websocket, redirect, render_template, url_for, Blueprint
from modules.asyncdb import asyncDB
from modules.redis import RedisClass


webapp = Blueprint('galaxycluster', __name__)


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
