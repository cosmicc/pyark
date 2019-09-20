from quart import Quart, websocket, redirect, render_template, url_for

app = Quart(__name__)


@app.route('/')
async def index():
    return await render_template('landing.html')


@app.websocket('/ws')
async def ws():
    while True:
        await websocket.send('hello')

app.run(host='172.31.250.115')
