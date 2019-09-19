import sys

import modules.instances
import pytest

sys.path.append('/home/ark/pyark')


def test_isinstanceonline():
    with pytest.raises(TypeError):
        modules.instances.isinstanceonline(None)
        modules.instances.isinstanceonline(1)
        modules.instances.isinstanceonline(['island', 'ragnarok'])
    assert modules.instances.isinstanceonline('ragnarok') is True
    assert type(modules.instances.isinstanceonline('ragnarok')) is bool


async def test_asyncgetinstancelist():
    assert type(await modules.instances.asyncgetinstancelist()) is tuple
    assert await modules.instances.asyncgetinstancelist() is not None
    assert len(await modules.instances.asyncgetinstancelist()) == 5


async def test_asyncisinstanceenabled(db):
    await db.connect(min=1, max=10, timeout=30)
    with pytest.raises(TypeError):
        await modules.instances.asyncisinstanceenabled(None, db)
        await modules.instances.asyncisinstanceenabled(1, db)
        await modules.instances.asyncisinstanceenabled(['island', 'ragnarok'], db)
    assert await modules.instances.asyncisinstanceenabled('ragnarok', db) is True
    assert type(await modules.instances.asyncisinstanceenabled('ragnarok'), db) is bool


async def test_asyncgetlastwipe(db):
    await db.connect(min=1, max=10, timeout=30)
    with pytest.raises(TypeError):
        await modules.instances.asyncgetlastwipe(None, db)
        await modules.instances.asyncgetlastwipe(1, db)
        await modules.instances.asyncgetlastwipe(['island', 'ragnarok'], db)
    assert await modules.instances.asyncgetlastwipe('ragnarok', db) is not None
    assert type(await modules.instances.asyncgetlastwipe('ragnarok'), db) is int
