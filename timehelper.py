intervals = (
    ('weeks', 604800),  # 60 * 60 * 24 * 7
    ('days', 86400),    # 60 * 60 * 24
    ('hours', 3600),    # 60 * 60
    ('minutes', 60),
    ('seconds', 1),
    )

def elapsedTime(start_time, stop_time):
    result = []
    seconds = start_time - stop_time
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


def playedTimeold(ptime):
    total_min = ptime / 60
    minutes = int(ptime % 60)
    if minutes == 1:
        minstring = 'Min'
    else:
        minstring = 'mins'
    hours = int(total_min / 60)
    if hours == 1:
        hourstring = 'hour'
    else:
        hourstring = 'hours'
    days = int(hours / 24)
    if days == 1:
        daystring = 'day'
    else:
        daystring = 'days'
    if days != 0:
        return('{} {}, {} {}'.format(days, daystring, hours-days*24, hourstring))
    elif hours != 0:
        return('{} {}, {} {}'.format(hours, hourstring, minutes-hours, minstring))
    elif minutes != 0:
        return('{} {}'.format(minutes, minstring))
    else:
        log.error('Elapsed time function failed. Could not convert.')
        return('Error')

