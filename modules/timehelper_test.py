import sys
from datetime import datetime

import modules.timehelper as timehelper
import pytest

sys.path.append('/home/ark/pyark')


def test_truncate_float():
    with pytest.raises(TypeError):
        timehelper.truncate('12.3531', 0)
        timehelper.truncate(12.3531, 1.4)
    assert type(timehelper.truncate(12.23456, 2)) is float
    assert timehelper.truncate(12.34567, 2) == 12.34
    assert timehelper.truncate(12.3, 1) == 12.3
    assert timehelper.truncate(12, 0) == 12
    assert timehelper.truncate(12.3, 5) == 12.3
    assert timehelper.truncate(12.386, -5) == 12.3
    assert timehelper.truncate(12.3531, 0) == 12


def test_datetimeto():
    assert type(timehelper.datetimeto(datetime.now(), 'string')) is str
    assert type(timehelper.datetimeto(datetime.now(), 'string', est=True)) is str
    assert type(timehelper.datetimeto(datetime.now(), 'epoch')) is int
    assert type(timehelper.datetimeto(datetime.now(), 'epoch', est=True)) is int


def test_Now():
    assert type(timehelper.Now(fmt='epoch')) is int
    assert type(timehelper.Now(fmt='epoch', est=True)) is int
    assert type(timehelper.Now(fmt='string')) is str
    assert type(timehelper.Now(fmt='string', est=True)) is str
    assert type(timehelper.Now(fmt='dt')) is datetime
    assert type(timehelper.Now(fmt='dt', est=True)) is datetime


def test_epochto():
    assert type(timehelper.epochto(datetime.now().timestamp(), 'dt')) is datetime
    assert type(timehelper.epochto(datetime.now().timestamp(), 'dt', est=True)) is datetime
    assert type(timehelper.epochto(datetime.now().timestamp(), 'string')) is str
    assert type(timehelper.epochto(datetime.now().timestamp(), 'string', est=True)) is str


def test_playedTime():
    assert timehelper.playedTime(480) == '8 minutes'
    assert timehelper.playedTime(3600) == '1 hour'
    assert timehelper.playedTime(5280) == '1 hour, 28 minutes'
    assert timehelper.playedTime(863254) == '1 week, 2 days'


def test_elapsedTime():
    assert timehelper.elapsedTime(1541300681, 1541300689) == 'now'
    assert timehelper.elapsedTime(1541300681, 1541300689, nowifmin=False) == '8 seconds'
    assert timehelper.elapsedTime(1541300689, 1541300681, nowifmin=False) == '8 seconds'
    assert timehelper.elapsedTime(1541288689, 1541300681) == '3 hours, 19 minutes'


def test_wcstamp():
    assert type(timehelper.wcstamp()) is str
