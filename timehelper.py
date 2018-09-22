from datetime import timedelta, datetime

tzfix = timedelta(hours=4)

intervals = (
    ('weeks', 604800),  # 60 * 60 * 24 * 7
    ('days', 86400),    # 60 * 60 * 24
    ('hours', 3600),    # 60 * 60
    ('minutes', 60),
    ('seconds', 1),
    )

def wcstamp():
    a = datetime.now()-tzfix
    return a.strftime('%m-%d %I:%M%p')

def elapsedTime(start_time, stop_time):
    result = []
    seconds = float(start_time) - float(stop_time)
    if seconds > 60 and seconds < 3600:
        granularity = 1
    else:
        granularity = 2
    if seconds > 60:
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
    if seconds < 3600:
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


