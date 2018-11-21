from datetime import datetime, timedelta
from flask import Flask, render_template, Response, request, redirect, url_for, flash
from flask_security import Security, SQLAlchemyUserDatastore, login_required, logout_user, current_user, UserMixin, RoleMixin, LoginForm, roles_required, url_for_security, RegisterForm
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from itertools import chain
from lottery import isinlottery, getlotteryplayers, getlotteryendtime
from modules.configreader import psql_host, psql_port, psql_user, psql_pw, psql_db, psql_statsdb
from modules.dbhelper import dbquery, dbupdate
from modules.instances import instancelist, isinstanceup, isinrestart, restartinstance, getlog, iscurrentconfig, serverchat
from modules.players import getplayersonline, getlastplayersonline, isplayerbanned, getplayer, banunbanplayer, isplayeronline, isplayerold, kickplayer
from modules.timehelper import elapsedTime, Now, playedTime, epochto, Secs, datetimeto
from wtforms import StringField, IntegerField
from wtforms.validators import InputRequired, Length
import json
import pandas as pd
import psycopg2
import pytz

app = Flask(__name__)
app.config['SECRET_KEY'] = '669v445Xyrzqkt@4N*%!74XkerrHQmz5^86eaKS^Cr4nF3a6KW5gUQTXZPRTmQm7'
app.config['SECURITY_PASSWORD_SALT'] = '8465Gk6562x2'
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{psql_user}:{psql_pw}@{psql_host}:{psql_port}/{psql_db}"
app.config['SECURITY_TRACKABLE'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECURITY_REGISTERABLE'] = False


# app.= Blueprint('webui', __name__, template_folder='templates')
# app.register_blueprint(app. url_prefix='/')

db = SQLAlchemy(app)

roles_users = db.Table('roles_users', db.Column('user_id', db.Integer(), db.ForeignKey('web_users.id')), db.Column('role_id', db.Integer(), db.ForeignKey('web_roles.id')))


class Role(db.Model, RoleMixin):
    __tablename__ = 'web_roles'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class User(db.Model, UserMixin):
    __tablename__ = 'web_users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(100))
    current_login_ip = db.Column(db.String(100))
    login_count = db.Column(db.Integer)
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    timezone = db.Column(db.String(25))
    steamid = db.Column(db.String(17), unique=True)
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))


class ExtendedRegisterForm(RegisterForm):
    timezone = StringField('Time Zone')


user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

#@app.before_first_request
#def initdb():
#db.create_all()
#user_datastore.find_or_create_role(name='admin', description='Administrator')
#user_datastore.find_or_create_role(name='player', description='Player')

#if not user_datastore.get_user('shithead'):
#user_datastore.create_user(email='admin', password='Ifa6wasa9', steamid='76561198408657294', timezone='US/Eastern')
#user_datastore.create_user(email='rykker', password='Ifa6wasa9', steamid='76561198388849736', timezone='US/Eastern')
#    if not user_datastore.get_user('admin@example.com'):
#        user_datastore.create_user(email='admin@example.com', password=encrypted_password)
    # User.query.filter_by(email='admin').update(dict(steamid='76561198408657294'))

    # Commit any database changes; the User and Roles must exist before we can add a Role to the User
#db.session.commit()

    # Give one User has the "end-user" role, while the other has the "admin" role. (This will have no effect if the
    # Users already have these Roles.) Again, commit any database changes.
#    user_datastore.add_role_to_user('someone@example.com', 'end-user')
#user_datastore.add_role_to_user('admin', 'admin')
#user_datastore.remove_role_from_user('shithead', 'admin')
#db.session.commit()


class LotteryForm(FlaskForm):
    buyinpoints = IntegerField('buyinpoints', validators=[InputRequired()])
    length = IntegerField('length', validators=[InputRequired()])


class MessageForm(FlaskForm):
    message = StringField('message', validators=[InputRequired(), Length(min=1, max=30)])


@app.context_processor
def _gettimezones():
    def ui_gettimezones():
        return pytz.common_timezones
    return dict(ui_gettimezones=ui_gettimezones)


@app.context_processor
def _utctolocal():
    def ui_utctolocal(utc_dt, short=False):
        if utc_dt is None:
            return 'Never'
        local_tz = pytz.timezone(current_user.timezone)
        #utc_dt.replace(tzinfo=local_tz)
        newdt = pytz.utc.localize(utc_dt).astimezone(local_tz)
        if not short:
            return newdt.strftime('%m-%d-%Y %-I:%M %p')
        else:
            return newdt.strftime('%m-%d %-I:%M %p')
    return dict(ui_utctolocal=ui_utctolocal)


@app.context_processor
def _Now():
    def Now():
        return datetime.now()
    return dict(Now=Now)


@app.context_processor
def _str2time():
    def ui_str2time(strtime):
        return datetime.strptime(strtime, '%m-%d %I:%M%p')
    return dict(ui_str2time=ui_str2time)


@app.context_processor
def database_processor():
    def ui_getplayersonline(instance, fmt):
        return getplayersonline(instance, fmt=fmt, case='title')
    return dict(ui_getplayersonline=ui_getplayersonline)


@app.context_processor
def database_processor2():
    def ui_getlastplayersonline(instance, fmt):
        return getlastplayersonline(instance, fmt=fmt, case='title')
    return dict(ui_getlastplayersonline=ui_getlastplayersonline)


@app.context_processor
def database_processor3():
    def ui_getplayerserver(player):
        return dbquery("SELECT server FROM players WHERE playername = '%s'" % (player.lower(),), fmt='string', fetch='one')
    return dict(ui_getplayerserver=ui_getplayerserver)


@app.context_processor
def database_processor4():
    def ui_getplayerlasttime(player):
        return elapsedTime(Now(), int(dbquery("SELECT lastseen FROM players WHERE playername = '%s'" % (player.lower(),), fmt='string', fetch='one')))
    return dict(ui_getplayerlasttime=ui_getplayerlasttime)


@app.context_processor
def _getplayer():
    def ui_getplayer(playername):
        return dbquery("SELECT * FROM players WHERE playername = '%s'" % (playername,), fmt='dict', fetch='one')
    return dict(ui_getplayer=ui_getplayer)


@app.context_processor
def _getlotteryplayers():
    def ui_getlotteryplayers(fmt='list'):
        return dbquery("SELECT playername FROM lotteryplayers", fmt=fmt, fetch='all', single=True)
    return dict(ui_getlotteryplayers=ui_getlotteryplayers)


@app.context_processor
def database_processor5():
    def ui_getinstver(inst):
        return dbquery("SELECT arkversion FROM instances WHERE name = '%s'" % (inst.lower(),), fmt='string', fetch='one')
    return dict(ui_getinstver=ui_getinstver)


@app.context_processor
def database_processor6():
    def ui_getrestartleft(inst):
        return dbquery("SELECT restartcountdown FROM instances WHERE name = '%s'" % (inst.lower(),), fmt='string', fetch='one')
    return dict(ui_getrestartleft=ui_getrestartleft)


@app.context_processor
def database_processor7():
    def ui_isinlottery():
        return isinlottery()
    return dict(ui_isinlottery=ui_isinlottery)


@app.context_processor
def database_processor8():
    def ui_getlotteryplayers(fmt):
        return getlotteryplayers(fmt=fmt)
    return dict(ui_getlotteryplayers=ui_getlotteryplayers)


@app.context_processor
def database_processor9():
    def ui_getlotteryendtime():
        return getlotteryendtime()
    return dict(ui_getlotteryendtime=ui_getlotteryendtime)


@app.context_processor
def database_processor10():
    def ui_isinstanceup(inst):
        return isinstanceup(inst)
    return dict(ui_isinstanceup=ui_isinstanceup)


@app.context_processor
def database_processor11():
    def ui_isinrestart(inst):
        return isinrestart(inst)
    return dict(ui_isinrestart=ui_isinrestart)


@app.context_processor
def _iscurrentconfig():
    def ui_iscurrentconfig(inst):
        return iscurrentconfig(inst)
    return dict(ui_iscurrentconfig=ui_iscurrentconfig)


@app.context_processor
def _elapsedTime():
    def ui_elapsedTime(etime):
        return elapsedTime(Now(), int(etime))
    return dict(ui_elapsedTime=ui_elapsedTime)


@app.context_processor
def _playedTime():
    def ui_playedTime(etime):
        return playedTime(int(etime))
    return dict(ui_playedTime=ui_playedTime)


@app.context_processor
def _epochto():
    def ui_epochto(epoch, fmt=''):
        return epochto(int(epoch))
    return dict(ui_epochto=ui_epochto)


@app.context_processor
def _isbanned():
    def ui_isbanned(steamid):
        return isplayerbanned(steamid=steamid)
    return dict(ui_isbanned=ui_isbanned)


@app.context_processor
def _isplayeronline():
    def ui_isplayeronline(steamid):
        return isplayeronline(steamid=steamid)
    return dict(ui_isplayeronline=ui_isplayeronline)


@app.context_processor
def _isplayerold():
    def ui_isplayerold(steamid):
        return isplayerold(steamid=steamid)
    return dict(ui_isplayerold=ui_isplayerold)


@app.context_processor
def _length():
    def ui_len(alist):
        return len(alist)
    return dict(ui_len=ui_len)


@app.context_processor
def _lastactive():
    def ui_lastactive(inst):
        retime = dbquery("SELECT date FROM %s WHERE value != 0 ORDER BY date DESC LIMIT 1" % (inst,), db='statsdb', fetch='one')[0]
        if datetime.now() - retime > timedelta(seconds=300):
            return f'{elapsedTime(Now(), datetimeto(retime, "epoch"))} ago'
        else:
            return 'Now'
    return dict(ui_lastactive=ui_lastactive)


@app.context_processor
def _statpull():
    def ui_last24avg(inst, dtype):
        if dtype == 'chart1':
            hours = 2
            rate = '10T'
            tstr = '%I:%M%p'
        elif dtype == 'chart2':
            hours = 24
            rate = 'H'
            tstr = '%-I%p'
        elif dtype == 'chart4':
            hours = 192
            rate = 'D'
            tstr = '%a'
        elif dtype == 'chart3':
            hours = 720
            rate = 'D'
            tstr = '%b %-d'
        conn = psycopg2.connect(dbname=psql_statsdb, user=psql_user, host=psql_host, port=psql_port, password=psql_pw)
        if inst == 'all':
            avglist = []
            for each in instances():
                slist = []
                navglist = []
                dlist = []
                c = conn.cursor()
                c.execute("SELECT * FROM {} WHERE date > '{}' ORDER BY date DESC".format(each[0], datetime.now() - timedelta(hours=hours)))
                nlist = c.fetchall()
                for y in nlist:
                    slist.append(y[1])
                    dlist.append(y[0])
                if avglist == []:
                    avglist = slist
                else:
                    navglist = [sum(pair) for pair in zip(slist, avglist)]
                    avglist = navglist
            c.close()
            conn.close()
            ret = list(zip(dlist, avglist))
            df = pd.DataFrame.from_records(ret, columns=['date', 'value'])
            df = df.set_index(pd.DatetimeIndex(df['date']))
        else:
            df = pd.read_sql("SELECT * FROM {} WHERE date > '{}' ORDER BY date DESC".format(inst, datetime.now() - timedelta(hours=hours)), conn, parse_dates=['date'], index_col='date')
            conn.close()
        df = df.tz_localize(tz='UTC')
        df = df.tz_convert(tz=current_user.timezone)
        df = df.resample(rate).mean()
        datelist = []
        for each in df.index:
            datelist.append(each.strftime(tstr))
        return (datelist, list(chain.from_iterable(df.values.round(1).tolist())))
    return dict(ui_last24avg=ui_last24avg)


@app.context_processor
def _playerlastactive():
    def ui_playerlastactive(lastseen):
        if Now() - lastseen > 40:
            return f'{elapsedTime(Now(), lastseen)} ago'
        else:
            return 'Now'
    return dict(ui_playerlastactive=ui_playerlastactive)


@app.context_processor
def _getannouncement():
    def ui_getannouncement():
        return dbquery("SELECT announce FROM general ", fmt='string', fetch='one')
    return dict(ui_getannouncement=ui_getannouncement)


@app.context_processor
def _haswebaccount():
    def haswebaccount(steamid):
        webuser = User.query.filter_by(steamid=steamid).first()
        if not hasattr(webuser, 'email'):
            return False
        else:
            return True
    return dict(haswebaccount=haswebaccount)


def instances():
    return dbquery("SELECT name FROM instances", fmt='list', fetch='all')


def instanceinfo(inst):
    return dbquery("SELECT * FROM instances WHERE name = '%s'" % (inst.lower(),), fmt='dict', fetch='one')


def getplayernames():
    return dbquery("SELECT playername FROM players ORDER BY playername ASC", fmt='list', single=True)


def getbannedplayers():
    return dbquery("SELECT playername FROM players WHERE banned != '' ORDER BY playername ASC", fmt='list', single=True)


def getexpiredplayers():
    return dbquery("SELECT playername FROM players WHERE banned = '' AND lastseen < '%s' ORDER BY playername ASC" % (Now() - Secs['month'],), fmt='list', single=True)


def getnewplayers(atime):
    return dbquery("SELECT playername FROM players WHERE banned = '' AND firstseen > '%s' ORDER BY playername ASC" % (Now() - Secs[atime],), fmt='list', single=True)


def getlastevent():
    return dbquery("SELECT * FROM events WHERE completed = 1 ORDER BY endtime DESC", fmt='dict', fetch='one')


def setannouncement(msg):
    if msg != '':
        dbupdate("UPDATE general SET announce = '%s'" % (msg,))
    else:
        dbupdate("UPDATE general SET announce = NULL")


def getlastlottery():
    return dbquery("SELECT * FROM lotteryinfo WHERE winner != 'Incomplete' ORDER BY timestamp DESC", fmt='dict', fetch='one')


def getcurrentlottery():
    return dbquery("SELECT * FROM lotteryinfo WHERE winner = 'Incomplete'", fmt='dict', fetch='one')


def getcurrentevent():
    return dbquery("SELECT * FROM events WHERE completed = 0 AND startime < '%s' ORDER BY endtime DESC" % (Now(),), fmt='dict', fetch='one')


def getfutureevent():
    return dbquery("SELECT * FROM events WHERE completed = 0 AND startime > '%s' ORDER BY endtime DESC" % (Now(),), fmt='dict', fetch='one')


def startthelottery(buyin, length):
    litm = str(buyin * 10)
    # lottostart = datetime.fromtimestamp(Now() + (3600 * int(length))).strftime('%a, %b %d %I:%M%p')
    dbupdate("INSERT INTO lotteryinfo (type,payoutitem,timestamp,buyinpoints,lengthdays,players,winner,announced) VALUES ('%s','%s','%s','%s','%s',0,'Incomplete',False)" % ('points', litm, Now(), buyin, length))


@app.context_processor
def _getlog():
    def ui_getlog(instance, wlog):
        chatlog = getlog(instance, wlog)
        return chatlog[::-1]
    return dict(ui_getlog=ui_getlog)


@app.route('/manifest.json')
def manifest():
    data = json.dumps({
        "short_name": "Galaxy",
        "name": "Galaxy Cluster",
        "icons": [
            {
                "src": "/static/images/galaxy192.png",
                "type": "image/png",
                "sizes": "192x192"
            }
        ],
        "start_url": "/",
        "background_color": "#000000",
        "display": "standalone",
        "scope": "/",
        "theme_color": "#000000"
    })
    return Response(data, mimetype='app.ication/x-web-app.manifest+json')

#@app.errorhandler(403)
#def forbidden(error):
#    return render_template('error/403.html', title='Forbidden'), 403

#@app.errorhandler(404)
#def page_not_found(error):
#    return render_template('error/404.html', title='Page Not Found'), 404

#@app.errorhandler(500)
#def internal_server_error(error):
#    db.session.rollback()
#    return render_template('error/500.html', title='Server Error'), 500


@app.route('/', methods=['POST', 'GET'])
@login_required
def dashboard():
    if request.method == 'POST':
        setannouncement(request.form["message"])
        flash(f'Login Announcement Set', 'info')
        return redirect(url_for('dashboard'))
    return render_template('dashboard.html', loginname=current_user.email, instances=instancelist())


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash(u'You have been logged out', 'info')
    return redirect(url_for('login'))


@app.route('/serverinfo/<instance>')
@login_required
def serverinfo(instance):
    return render_template('serverinfo.html', serverinfo=instanceinfo(instance))


@app.route('/playersearch', methods=['POST', 'GET'])
@login_required
def result():
    if request.method == 'POST':
        return render_template("playerinfo.html", playerinfo=getplayer(playername=request.form['player'].lower(), fmt='dict'))


@app.route('/startlottery', methods=['POST', 'GET'])
@login_required
@roles_required('admin')
def startlottery():
    form = LotteryForm()
    if form.validate_on_submit():
        startthelottery(form.buyinpoints.data, form.length.data)
        flash(u'New Lottery has been Started', 'info')
        return redirect(url_for('_lottery'))
    return render_template('startlottery.html', form=form)


@app.route('/server/sendchat/<server>', methods=['POST'])
@login_required
@roles_required('admin')
def sendchat(server):
    form = MessageForm()
    if form.validate_on_submit():

        flash(f'Message sent to {server.title()}', 'info')
        return redirect(url_for('_chatlog', instance=server))
    flash(f'Message failed to {server.title()}', 'error')
    return redirect(url_for('_chatlog', instance=server))


@app.route('/playerinfo/<player>', methods=['POST', 'GET'])
@login_required
def playerinfo(player):
    if request.method == 'POST':
        serverchat(request.form["message"], whosent=player.lower(), inst=getplayer(playername=player.lower(), fmt='dict')['server'], private=True)
        flash(f'Message Sent', 'info')
        return redirect(url_for('playerinfo', player=player))
    return render_template('playerinfo.html', playerinfo=getplayer(playername=player.lower(), fmt='dict'))


@app.route('/webcreate/<steamid>', methods=['POST', 'GET'])
@login_required
@roles_required('admin')
def webcreate(steamid):
    if request.method == 'POST':
        user_datastore.create_user(email=request.form['email'], password=request.form['password'], steamid=request.form['steamid'], timezone=request.form['timezone'])
        db.session.commit()
        flash(f'Web User Created', 'info')
        webuser = User.query.filter_by(steamid=steamid).first()
        return render_template('webinfo.html', webuser=webuser, playerinfo=getplayer(steamid=steamid, fmt='dict'))
    return render_template('webcreate.html', playerinfo=getplayer(steamid=steamid, fmt='dict'))


@app.route('/webinfo/<steamid>', methods=['POST', 'GET'])
@login_required
def webinfo(steamid):
    if request.method == 'POST':
        User.query.filter_by(steamid=steamid).update(dict(timezone=request.form["timezone"]))
        db.session.commit()
        flash(f'Web Settings Updated', 'info')
        webuser = User.query.filter_by(steamid=steamid).first()
        return render_template('webinfo.html', webuser=webuser, playerinfo=getplayer(steamid=steamid, fmt='dict'))
    webuser = User.query.filter_by(steamid=steamid).first()
    if not hasattr(webuser, 'email'):
        flash(f'Player does not have a web account', 'warning')
        return render_template('playerinfo.html', playerinfo=getplayer(steamid=steamid, fmt='dict'))
    else:
        if current_user.has_role('admin') or current_user.steamid == steamid:
            return render_template('webinfo.html', webuser=webuser, playerinfo=getplayer(steamid=steamid, fmt='dict'))
        else:
            flash(f'Invalid Access', 'error')
            return render_template('playerinfo.html', playerinfo=getplayer(steamid=steamid, fmt='dict'))


@app.route('/playerinfo')
@login_required
def _players():
    return render_template('playerselect.html', players=getplayernames(), bannedplayers=getbannedplayers(), expiredplayers=getexpiredplayers(), newplayers=getnewplayers('week'))


@app.route('/events')
@login_required
def _events():
    return render_template('eventinfo.html', lastevent=getlastevent(), currentevent=getcurrentevent(), futureevent=getfutureevent())


@app.route('/lottery')
@login_required
def _lottery():
    return render_template('lotteryinfo.html', lastlottery=getlastlottery(), currentlottery=getcurrentlottery())


@app.route('/stats/<inst>')
@login_required
def _stats(inst):
    return render_template('stats.html', inst=inst)


@app.route('/bantoggle/<steamid>')
@login_required
@roles_required('admin')
def _bantoggle(steamid):
    if isplayerbanned(steamid=steamid):
        banunbanplayer(steamid=steamid, ban=False)
        flash(u'Player has been Un-Banned', 'success')
        return render_template('playerinfo.html', playerinfo=getplayer(steamid=steamid, fmt='dict'))
    else:
        banunbanplayer(steamid=steamid, ban=True)
        flash(u'Player has been BANNED!', 'error')
        return render_template('playerinfo.html', playerinfo=getplayer(steamid=steamid, fmt='dict'))


@app.route('/kickplayer/<steamid>/<instance>')
@login_required
@roles_required('admin')
def _kickplayer(steamid, instance):
    kickplayer(instance, steamid)
    flash(u'Kicking player from %s' % (instance,), 'info')
    return render_template('playerinfo.html', playerinfo=getplayer(steamid=steamid, fmt='dict'))


@app.route('/server/restart/<instance>')
@login_required
@roles_required('admin')
def _restartinstance(instance):
    restartinstance(instance, cancel=False)
    flash(u'Restarting Server', 'info')
    return render_template('serverinfo.html', serverinfo=instanceinfo(instance))


@app.route('/server/cancelrestart/<instance>')
@login_required
@roles_required('admin')
def _cancelrestartinstance(instance):
    restartinstance(instance, cancel=True)
    flash(u'Cencelling Server Restart', 'info')
    return render_template('serverinfo.html', serverinfo=instanceinfo(instance))


@app.route('/server/chatlog/<instance>', methods=['POST', 'GET'])
@login_required
def _chatlog(instance):
    if request.method == 'POST':
        serverchat(request.form["message"], inst=instance)
        flash(f'Message Sent to {instance.title()}', 'info')
        return redirect(url_for('_chatlog', instance=instance))
    chatlog = getlog(instance, 'chat')
    return render_template('serverchatlog.html', serverinfo=instanceinfo(instance), chatlog=chatlog[::-1])
