import sys

import modules.instances
import pytest

sys.path.append('/home/ark/pyark')


def test_isinstanceup():
    with pytest.raises(TypeError):
        pass
    assert modules.instances.isinstanceup('ragnarok') == '1'
