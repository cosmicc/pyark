from datetime import datetime, timedelta
import pytz
from math import trunc

tzfix = timedelta(hours=4)

Secs = {
    "minute": 60,
    "1min": 60,
    "2min": 120,
    "3min": 180,
    "4min": 240,
    "5min": 300,
    "10min": 600,
    "13min": 780,
    "15min": 900,
    "20min": 1200,
    "30min": 1800,
    "halfhour": 1800,
    "60min": 3600,
    "hour": 3600,
    "2hour": 7200,
    "4hour": 14400,
    "8hour": 28800,
    "12hour": 43200,
    "day": 86400,
    "1day": 86400,
    "3day": 259200,
    "week": 604800,
    "month": 2592000,
    "3month": 7776000,
}

intervals = (
    ("years", 31536000),
    ("months", 2592000),
    # ('weeks', 604800),  # 60 * 60 * 24 * 7
    ("days", 86400),  # 60 * 60 * 24
    ("hours", 3600),  # 60 * 60
    ("minutes", 60),
    ("seconds", 1),
)


def truncate_float(number: float, digits: int) -> float:
    """Truncate a float to a specified number of digits

    Args:
        number (FLOAT, STRING): Description: Number to truncate
        digits (INT): Description: Number of decimal places to return

    Returns:
        FLOAT
    """
    if not isinstance(number, (float, str)):
        raise TypeError(f"Number value must be type float or str, not {type(number)}")
    if not isinstance(digits, int):
        raise TypeError(f"Digits value must be type int, not {type(digits)}")
    if isinstance(number, str):
        number = float(number)
    stepper = 10.0 ** abs(digits)
    return trunc(stepper * number) / stepper


def estconvert(utc_dt):
    """Summary:

    Args:
        utc_dt (TYPE): Description:

    Returns:
        TYPE: Description:
    """
    ndt = utc_dt.replace(tzinfo=pytz.UTC)
    return ndt.astimezone(pytz.timezone("America/Detroit"))


class newdatetimeto:
    def _checkinputs(dt):
        if not isinstance(dt, datetime):
            raise TypeError(f"Input must be of type datetime not {type(dt)}")

    def epoch(dt):
        """Convert datetime object to epoch

        Args:
            dt (datetime): Description: Datetime object to convert

        Returns:
            FLOAT: Description: Epoch value of datetime object
        """
        newdatetimeto._checkinputs(dt)
        return dt.timestamp()

    def string(dt):
        """Convert datetime object to string representation

        Args:
            dt (datetime): Description: Datetime object to convet

        Returns:
            STRING: Description: '%a, %b %d, %Y %I:%M %p'
        """
        newdatetimeto._checkinputs(dt)
        return dt.strftime("%a, %b %d, %Y %I:%M %p")


def datetimeto(dt, fmt, est=False):
    """Convert datetime object

    Args:
        dt (TYPE): Description:
        fmt (TYPE): Description:
        est (bool, [Optional]): Description:

    Returns:
        TYPE: Description:
    """
    if fmt == "epoch":
        return int(dt.timestamp())
    elif fmt == "string":
        if est:
            return estshift(dt).strftime("%a, %b %d, %Y %I:%M %p")
        else:
            return dt.strftime("%a, %b %d, %Y %I:%M %p")


def Now(fmt="epoch", est=False):
    """Return current time

    Args:
        fmt (str, [Optional]): Description: (dt, dtd, epoch, string)
        est (bool, [Optional]): Description:

    Returns:
        TYPE: Description:
    """
    if fmt == "dt":
        if est:
            return estshift(datetime.now())
        else:
            return datetime.now()
    elif fmt == "dtd":
        if est:
            return estshift(datetime.now()).date()
        else:
            return datetime.now().date()
    elif fmt == "epoch":
        return int(datetime.now().timestamp())
    elif fmt == "string":
        if est:
            return datetimeto(datetime.now(), "string", est=True)
        else:
            return datetimeto(datetime.now(), "string")


def epochto(epoch, fmt, est=False):
    if fmt == "dt":
        if est:
            return estshift(datetime.fromtimestamp(int(epoch)))
        else:
            return datetime.fromtimestamp(int(epoch))
    elif fmt == "string":
        if est:
            return datetimeto(datetime.fromtimestamp(int(epoch)), "string", est=True)
        else:
            return datetimeto(datetime.fromtimestamp(int(epoch)), "string")


def estshift(otime):
    return otime - tzfix


def gmtshift(otime):
    return otime + tzfix


def wcstamp():
    a = datetime.now() - tzfix
    return a.strftime("%m-%d %I:%M%p")


def elapsedTime(start_time, stop_time, nowifmin=True, append=False):
    """Convert 2 epochs to elapsed time string representation

    Args:
        start_time (string, int, float, datetime): Description: Start time
        stop_time (string, int, float, datetime): Description:  End time
        nowifmin (bool, [Optional]): Description: If less then 1 minute return 'Now'

    Returns:
        STRING: Description: e.g. '1 Hour, 47 Minutes'
    """
    if isinstance(start_time, datetime):
        start_time = datetimeto(start_time, fmt='epoch')
    if isinstance(stop_time, datetime):
        stop_time = datetimeto(stop_time, fmt='epoch')
    result = []
    if start_time > stop_time:
        seconds = int(start_time) - int(stop_time)
    else:
        seconds = int(stop_time) - int(start_time)
    tseconds = seconds
    if seconds > Secs["minute"] and seconds < Secs["hour"]:
        granularity = 1
    else:
        granularity = 2
    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip("s")
            result.append("{} {}".format(int(value), name))
    if tseconds < 60 and nowifmin:
        return "now"
    else:
        if append:
            return ", ".join(result[:granularity]) + f" {append}"
        else:
            return ", ".join(result[:granularity])


def elapsedSeconds(seconds):
    """Convert seconds to elapsed time string representation

    Args:
        seconds (string, int, float): Description: Number of seconds to convert

    Returns:
        STRING: Description: e.g. '1 Hour, 47 Minutes'
    """
    result = []
    if not isinstance(seconds, (int, float, str)):
        raise TypeError(f"Seconds is wrong type {type(seconds)}")
    if isinstance(seconds, str):
        seconds = seconds.replace(",", "")
    seconds = int(seconds)
    if seconds < Secs["hour"]:
        granularity = 1
    else:
        granularity = 2
    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip("s")
            result.append("{} {}".format(int(value), name))
    return ", ".join(result[:granularity])


def joinedTime(seconds):
    result = []
    seconds = int(seconds)
    if seconds < Secs["hour"]:
        granularity = 1
    else:
        granularity = 2
    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip("s")
            result.append("{} {}".format(int(value), name))
    return ", ".join(result[:granularity])


def playedTime(seconds):
    result = []
    seconds = int(seconds)
    if seconds < Secs["hour"]:
        granularity = 1
    else:
        granularity = 2
    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip("s")
            result.append("{} {}".format(int(value), name))
    return ", ".join(result[:granularity])
