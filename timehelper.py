def elapsedTime(start_time, stop_time, lshort=False):
    diff_time = start_time - stop_time
    total_min = diff_time / 60
    minutes = int(total_min % 60)
    if minutes == 1:
        if lshort is False:
            minstring = 'Minute'
        else:
            minstring = 'Min'
    else:
        if lshort is False:
            minstring = 'Minutes'
        else:
            minstring = 'Mins'
    hours = int(total_min / 60)
    if hours == 1:
        if lshort is False:
            hourstring = 'Hour'
        else:
            hourstring = 'Hr'
    else:
        if lshort is False:
            hourstring = 'Hours'
        else:
            hourstring = 'Hrs'
    days = int(hours / 24)
    if days == 1:
        if lshort is False:
            daystring = 'Day'
        else:
            daystring = 'Day'
    else:
        if lshort is False:
            daystring = 'Days'
        else:
            daystring = 'Days'
    if days != 0:
        return('{} {}, {} {}'.format(days, daystring, hours, hourstring))
    elif hours != 0:
        return('{} {}, {} {}'.format(hours, hourstring, minutes, minstring))
    elif minutes != 0:
        return('{} {}'.format(minutes, minstring))
    elif minutes == 0:
        return('now')
    else:
        log.error('Elapsed time function failed. Could not convert.')
        return('Error')


def playedTime(ptime):
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

