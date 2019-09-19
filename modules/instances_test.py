import sys

import modules.instances
import pytest

sys.path.append('/home/ark/pyark')


def test_isinstanceup():
    with pytest.raises(TypeError):
        modules.instances.isinstanceup(None)
        modules.instances.isinstanceup(1)
        modules.instances.isinstanceup(['island', 'ragnarok'])
    assert modules.instances.isinstanceup('ragnarok') == '1'
