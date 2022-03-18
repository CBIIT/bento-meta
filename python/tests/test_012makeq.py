import sys
import os
import re
import pytest
from pdb import set_trace
sys.path.insert(0, '.')
sys.path.insert(0, '..')
from bento_meta.util.cypher.entities import (
    N, N0, R, R0, P, T, G,
    _pattern, _as, _condition, _return,
    _plain, _anon, _var,
    )
from bento_meta.util.cypher.functions import (
    Func, count, exists, labels, group, And, Or, Not,
    )
from bento_meta.util.cypher.clauses import (
    Clause, Match, Where, Return, Statement,
)

from bento_meta.util.makeq import Query

tdir = 'tests/' if os.path.exists('tests') else ''

def test_paths(test_paths):
    assert Query.load_paths(open("{}samples/query_paths.yml".format(tdir)))
    assert len(test_paths)

    q = Query("/model/ICDC/node/demographic/property/breed/terms")
    q = Query("/tag/Category/values")
    assert q.path_id == "tag_values"
    q = Query("/tag/Category/administrative/entities")
    assert q.path_id == "tag_entities"
    
    for t in test_paths:
        qq = Query(t)
        assert qq.statement
        assert isinstance(qq.params, dict)
        pass

    assert len(Query.cache) == len(test_paths)
    for t in test_paths:
        Query(t)  # should all be found in cache, so
    assert len(Query.cache) == len(test_paths)

    q1 = Query("/tag/this/that/entities/count")
    list(q.params.values()) == ["this","that"]
    q2 = Query("/tag/13/other/entities/count")
    list(q.params.values()) == [13, "other"]
    assert q1._engine == q2._engine
