import sys
import re
import pytest
from pdb import set_trace
sys.path.insert(0, '.')
sys.path.insert(0, '..')
from bento_meta.util.cypher import (
    N, N0, R, R0, P, T, Path,
    Clause, Match, Where, Return, Statement,
    Func, count, exists, group, And, Or, Not,
    _pattern, _as, _condition, _return,
    _plain, _anon, _var
)


def test_entities():
    # nodes
    assert isinstance(N0(), N)
    assert not N0().label
    assert not N0().props
    assert not N0().As
    assert not N0().var

    n = N()
    assert n.var
    assert re.match("^n[0-9]+$", n.var)
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
    assert isinstance(R0(), R)
    assert not R0().Type
    assert not R0().props
    assert not R0().var
    
    r = R(Type="has_a")
    assert re.match("^r[0-9]+$", r.var)
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
    l = P(handle="color", value="blue")
    assert type(l.value) == str
    assert l.value == "blue"
    t = P(handle="spin", value="$parm")

    assert not p.condition()
    assert not q.condition()

    w = N(label="item", props=q)
    assert q.condition() == "{}.weight = 12".format(w.var)
    assert _condition(q) == "{}.weight = 12".format(w.var)
    x = N(label="item", props=l)
    assert _condition(l) == "{}.color = 'blue'".format(x.var)
    y = N(label="item", props=t)
    assert _condition(t) == "{}.spin = $parm".format(y.var)

    z = y.relate_to(r, x)
    assert isinstance(z, T)
    assert z.pattern() == (
        "({}:item {{spin:$parm}})-[{}:has_a]->({}:item "
        "{{color:'blue'}})"
        ).format(y.var, r.var, x.var)
    assert z.pattern() == z.condition()
    assert _pattern(z) == _condition(z)

    u = s.relate(w, x)
    assert isinstance(u, T)
    assert _pattern(_plain(u)) == (
        "({}:item)-[{}:is_a]->({}:item)"
        ).format(w.var, s.var, x.var)

    u = _anon(s).relate(w, _anon(x))
    assert _pattern(_plain(u)) == (
        "({}:item)-[:is_a]->(:item)"
        ).format(w.var)

    u = R0().relate(_var(w), _var(x))
    assert _pattern(_plain(u)) == (
        "({})-->({})"
        ).format(w.var, x.var)

    assert _pattern(R0().relate(N0(), N0())) == "()-->()"


def test_paths():
    # happy paths:
    # Path(N, R, N), Path(T, T), Path(N, R, T), Path(T, R, N)
    # Path(N, R, P), Path(Path, R, N)
    # Path(N, R, N, R, N, R, N), Path(T, Path), Path(Path, T)
    # Path(Path, Path)
    # Path(Path, R, N, R, T) ...
    # unhappy paths: with pytest.raises(Exception)
    # Path(N), Path(R), Path(N, R), Path(R, N), Path(N, N)
    # Path(N, T), Path(R, T), Path(N, P), Path(R, P)
    # Path(N, R, N, R, N, R)
    pass


def test_clauses():

    n = N(label="node", props={"model": "ICDC", "handle": "diagnosis"})
    m = N(label="property", props={"handle": "disease_type"})
    t = _anon(R(Type="has_property")).relate(n, m)

    c = count(n)
    assert isinstance(c, count)
    assert isinstance(c, Func)
    assert str(c) == "count({})".format(n.var)
    assert str(count("this")) == "count(this)"
    x = exists(m.props['handle'])
    assert isinstance(x, exists)
    assert isinstance(x, Func)
    assert str(x) == "exists({}.handle)".format(m.var)
    assert str(exists("this.that")) == "exists(this.that)"

    match = Match(t)
    assert isinstance(match, Match)
    assert isinstance(match, Clause)
    assert str(match) == (
        "MATCH ({}:node {{model:'ICDC',handle:'diagnosis'}})"
        "-[:has_property]->({}:property {{handle:'disease_type'}})"
        ).format(n.var, m.var)

    where = Where(*t.nodes())
    assert isinstance(where, Where)
    assert isinstance(where, Clause)
    assert str(where) == (
        "WHERE {n}.model = 'ICDC' AND {n}.handle = 'diagnosis' "
        "AND {m}.handle = 'disease_type'"
        ).format(n=n.var, m=m.var)

    ret = Return(t)
    assert isinstance(ret, Return)
    assert isinstance(ret, Clause)
    assert str(ret) == (
        "RETURN {n}, {m}"
        ).format(n=n.var, m=m.var)


def test_statments():
    n = N(label="node", props={"model": "ICDC", "handle": "diagnosis"})
    m = N(label="property", props={"handle": "disease_type"})
    t = _anon(R(Type="has_property")).relate(n, m)
    p = P(handle='boog')
    p.entity = n

    assert str(
        Statement(
            Match(_var(_plain(t))),
            Where(exists(m.props['handle']), n),
            Return(count(n))
            )
        ) == (
            "MATCH ({n})-[:has_property]->({m}) "
            "WHERE exists({m}.handle) AND {n}.model = 'ICDC' AND "
            "{n}.handle = 'diagnosis' "
            "RETURN count({n})"
            ).format(n=n.var, m=m.var)

    assert str(
        Statement(
            Match(_var(_plain(t))),
            Where(group(And(exists(m.props['handle']), n.props['model'])),
                  Not(n.props['handle'])),
            Return(p),
            'LIMIT 10'
            )
        ) == (
            "MATCH ({n})-[:has_property]->({m}) "
            "WHERE (exists({m}.handle) AND {n}.model = 'ICDC') AND NOT "
            "{n}.handle = 'diagnosis' "
            "RETURN {n}.boog LIMIT 10"
            ).format(n=n.var, m=m.var)
