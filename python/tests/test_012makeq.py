import sys
import re
import pytest
from pdb import set_trace
sys.path.insert(0, '.')
sys.path.insert(0, '..')
from bento_meta.util.cypher import (
    N, N0, R, R0, P, T, G,
    Clause, Match, Where, Return, Statement,
    Func, count, exists, group, And, Or, Not,
    _pattern, _as, _condition, _return,
    _plain, _anon, _var
)

from bento_meta.util.makeq import Query

def test_paths(test_paths):
    assert Query.load_paths(open("samples/query_paths.yml"))
    assert len(test_paths)
    for t in test_paths:
        q = Query(t)
        assert q.statement
        assert isinstance(q.params, dict)
    pass
