from datetime import timedelta, datetime

tzfix = timedelta(hours=4)

Seconds = {'minute': 60, 'hour': 3600, 'day': 86400, 'week': 604800, 'month': 2592000}

intervals = (
    ('weeks', 604800),  # 60 * 60 * 24 * 7
    ('days', 86400),    # 60 * 60 * 24
    ('hours', 3600),    # 60 * 60
    ('minutes', 60),
    ('seconds', 1),)


def dt2epoch(dt):
    return float(dt.timestamp())


def estshift(otime):
    return otime - tzfix


def gmtshift(otime):
    return otime + tzfix


def epoch2string(epoch):
    return estshift(datetime.fromtimestamp(float(epoch))).strftime('%a, %b %d %I:%M %p')


def wcstamp():
    a = datetime.now() - tzfix
    return a.strftime('%m-%d %I:%M%p')


def elapsedTime(start_time, stop_time, now=True):
    result = []
    seconds = float(start_time) - float(stop_time)
    if seconds > Seconds['minute'] and seconds < Seconds['hour']:
        granularity = 1
    else:
        granularity = 2
    if seconds > Seconds['minute']:
        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                if value == 1:
                    name = name.rstrip('s')
                result.append("{} {}".format(int(value), name))

                
        return ', '.join(result[:granularity])
    else:
        return 'now'


def playedTime(seconds):
    result = []
    if type(seconds) != float:
        seconds = float(seconds.replace(',', ''))
    if seconds < Seconds['hour']:
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
