import pytest


async def test_connection(cursor):
    rs = cursor.execute('SELECT id FROM messages').fetchval()
    assert len(rs) == 0
