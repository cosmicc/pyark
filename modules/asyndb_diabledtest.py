import pytest
from loguru import logger as log


@pytest.mark.order1
async def test_connection(cursor):
    rs = cursor.execute('SELECT id FROM messages')
    assert len(rs) == 1
