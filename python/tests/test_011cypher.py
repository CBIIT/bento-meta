import sys
import re
import pytest
from pdb import set_trace
sys.path.insert(0, '.')
sys.path.insert(0, '..')
from bento_meta.util.cypher import (
    N, N0, R, R0, P, T,
    _pattern, _as, _condition, _return
)

def test_entities():
    # nodes
    assert isinstance(N0(),N)
    assert not N0().label
    assert not N0().props
    assert not N0().As
    assert not N0().var

    n = N()
    assert n.var
    assert re.match("^n[0-9]+$",n.var)
    m = N(label="thing")
    assert m.label == "thing"
    assert n.var != m.var

    assert n.pattern() == "({})".format(n.var)
    assert m.pattern() == "({}:thing)".format(m.var)
    assert _pattern(m) == "({}:thing)".format(m.var)
    assert not n.condition()
    assert not m.condition()
    assert not _condition(n)
    assert n.Return() == n.var
    assert m.Return() == m.var
    assert _return(m) == m.var

    assert _return(_as(m, "eddie")) == "{} as eddie".format(m.var)
    
    x = N(label="thing", As="dude")
    assert x.label == "thing" and x.As == "dude"
    assert x.Return() == "{} as dude".format(x.var)
    
    # relationships
    assert isinstance(R0(),R)
    assert not R0().Type
    assert not R0().props
    assert not R0().var
    
    r = R(Type="has_a")
    assert re.match("^r[0-9]+$",r.var)
    s = R(Type="is_a")
    assert r.var != s.var
    assert r.pattern() == "-[{}:has_a]-".format(r.var)
    assert _pattern(r) == "-[{}:has_a]-".format(r.var)
    assert not r.condition()
    assert not _condition(r)
    assert r.Return() == "{}".format(r.var)
    assert _return(r) == "{}".format(r.var)
    
    # props
    p = P(handle="height")
    assert p.handle == "height"
    q = P(handle="weight", value=12)
    assert type(q.value) == int
    assert q.value == 12
    s = P(handle="color", value="blue")
    assert type(s.value) == str
    assert s.value == "blue"
    t = P(handle="spin", value="$parm")


    assert not p.condition()
    assert not q.condition()

    w = N(label="item", props=q)
    assert q.condition() == "{}.weight = 12".format(w.var)
    
    
    
def test_clauses():
    pass


def test_statments():
    pass
