import sys
from datetime import datetime

import modules.timehelper as timehelper
import pytest

sys.path.append('/home/ark/pyark')


def test_truncate_float():
    with pytest.raises(TypeError):
        timehelper.truncate_float(12.3531, 1.4)
        timehelper.truncate_float(12, 0)
    assert timehelper.truncate_float('12a3531', 1)
    assert timehelper.truncate_float('12.3531', 1) == 12.3
    assert type(timehelper.truncate_float(12.23456, 2)) is float
    assert timehelper.truncate_float(12.34567, 2) == 12.34
    assert timehelper.truncate_float(12.3, 1) == 12.3
    assert timehelper.truncate_float(12.3, 5) == 12.3
    assert timehelper.truncate_float(12.386, -5) == 12.386
    assert timehelper.truncate_float(12.3531, 0) == 12


def test_newdatetimeto():
    with pytest.raises(TypeError):
        timehelper.newdatetimeto.epoch(1)
        timehelper.newdatetimeto.epoch('12.3')
        timehelper.newdatetimeto.epoch(12.3)
    assert type(timehelper.newdatetimeto.string(datetime.now())) is str
    assert type(timehelper.newdatetimeto.string(datetime.now())) is not None
    assert type(timehelper.newdatetimeto.epoch(datetime.now())) is float
    assert type(timehelper.newdatetimeto.epoch(datetime.now())) is not None


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


def test_elapsedSeconds():
    assert timehelper.elapsedSeconds(480) == '8 minutes'
    assert timehelper.elapsedSeconds('3600') == '1 hour'
    assert timehelper.elapsedSeconds('3,600') == '1 hour'
    assert timehelper.elapsedSeconds(5280.1023) == '1 hour, 28 minutes'
    assert timehelper.elapsedSeconds(863254) == '9 days, 23 hours'


def test_playedTime():
    assert timehelper.playedTime(480) == '8 minutes'
    assert timehelper.playedTime('3600') == '1 hour'
    assert timehelper.playedTime(5280.1023) == '1 hour, 28 minutes'
    assert timehelper.playedTime(863254) == '9 days, 23 hours'


def test_elapsedTime():
    with pytest.raises(TypeError):
        timehelper.elapsedTime([1, 3])
        timehelper.elapsedTime((1, 3))
    assert timehelper.elapsedTime(1541300681, 1541300689) == 'now'
    assert timehelper.elapsedTime(1541300681, 1541300689, nowifmin=False) == '8 seconds'
    assert timehelper.elapsedTime('1541300689', '1541300681', nowifmin=False) == '8 seconds'
    assert timehelper.elapsedTime(1541300681.012124, 1541300689.523465, nowifmin=False) == '8 seconds'
    assert timehelper.elapsedTime(1541288689, 1541300681) == '3 hours, 19 minutes'


def test_wcstamp():
    assert type(timehelper.wcstamp()) is str
