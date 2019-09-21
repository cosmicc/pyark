from quart import Quart, websocket, redirect, render_template, url_for
from modules.asyncdb import asyncDB
from modules.redis import RedisClass

app = Quart(__name__)


@app.before_serving
async def db_pool():
    app.db = asyncDB()
    await app.db.connect(min=3, max=20, timeout=240)


@app.before_serving
async def redis_pool():
    Redis = RedisClass()
    app.redis = Redis.redis


@app.after_serving
async def db_close():
    await app.db.close()


@app.route('/')
async def index():
    return await render_template('home.html')


@app.websocket('/ws')
async def ws():
    while True:
        await websocket.send('hello')

app.run(host='172.31.250.115')
