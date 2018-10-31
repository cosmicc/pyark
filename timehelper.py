from datetime import timedelta, datetime

tzfix = timedelta(hours=4)

Secs = {'minute': 60, '1min': 60, '2min': 120, '3min': 180, '4min': 240, '5min': 300, '10min': 600, '15min': 900, '20min': 1200, '30min': 1800, 'halfhour': 1800, '60min': 3600, 'hour': 3600, '2hour': 7200, '4hour': 14400, '8hour': 28800, '12hour': 43200, 'day': 86400, 'week': 604800, 'month': 2592000}

intervals = (
    ('weeks', 604800),  # 60 * 60 * 24 * 7
    ('days', 86400),    # 60 * 60 * 24
    ('hours', 3600),    # 60 * 60
    ('minutes', 60),
    ('seconds', 1),)


def now(fmt='epoch', est=False):
    if fmt == 'dt':
        if est:
            return estshift(datetime.now())
        else:
            return datetime.now()
    elif fmt == 'epoch':
        return int(datetime.now().timestamp())
    elif fmt == 'string':
        if est:
            return estshift(datetime.now()).strftime('%a, %b %d %I:%M %p')
        else:
            return datetime.now().strftime('%a, %b %d %I:%M %p')


def dt2epoch(dt):
    return float(dt.timestamp())


def estshift(otime):
    return otime - tzfix


def gmtshift(otime):
    return otime + tzfix


def dt2string(dt, est=False):
    if est:
        return estshift(dt).strftime('%a, %b %d %I:%M %p')
    else:
        return dt.strftime('%a, %b %d %I:%M %p')


def epoch2string(epoch):
    return dt2string(datetime.fromtimestamp(float(epoch)))


def wcstamp():
    a = datetime.now() - tzfix
    return a.strftime('%m-%d %I:%M%p')


def elapsedTime(start_time, stop_time, nowifmin=True):
    result = []
    if start_time > stop_time:
        seconds = int(start_time) - int(stop_time)
    else:
        seconds = int(stop_time) - int(start_time)
    tseconds = seconds
    if seconds > Secs['minute'] and seconds < Secs['hour']:
        granularity = 1
    else:
        granularity = 2
    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append("{} {}".format(int(value), name))
    if tseconds < 60 and now:
        return 'now'
    else:
        return ', '.join(result[:granularity])


def playedTime(seconds):
    result = []
    seconds = int(seconds)
    if seconds < Secs['hour']:
        granularity = 1
    else:
        granularity = 2
    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append("{} {}".format(int(value), name))
    return ', '.join(result[:granularity])
