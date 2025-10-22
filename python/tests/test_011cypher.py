import re
import sys

import pytest

sys.path.insert(0, ".")
sys.path.insert(0, "..")
from minicypher.clauses import (
    Clause,
    Create,
    Match,
    Merge,
    OnCreateSet,
    OnMatchSet,
    Remove,
    Return,
    Set,
    Where,
)
from minicypher.entities import (
    N0,
    R0,
    G,
    N,
    P,
    R,
    T,
    _anon,
    _As,
    _condition,
    _pattern,
    _plain,
    _plain_var,
    _return,
    _var,
)
from minicypher.functions import (
    And,
    Func,
    Not,
    count,
    exists,
    group,
)
from minicypher.statement import Statement


def test_entities():
    # nodes
    assert isinstance(N0(), N)
    assert not N0().label
    assert not N0().props
    assert not N0()._as
    assert not N0()._var

    n = N()
    assert n._var
    assert re.match("^n[0-9]+$", n._var)
    m = N(label="thing")
    assert m.label == "thing"
    assert n.var != m.var

    assert n.pattern() == f"({n._var})"
    assert m.pattern() == f"({m._var}:thing)"
    assert _pattern(m) == f"({m._var}:thing)"
    assert not n.condition()
    assert not m.condition()
    assert not _condition(n)
    assert n.Return() == n._var
    assert m.Return() == m._var
    assert _return(m) == m._var

    assert _return(_As(m, "eddie")) == f"{m._var} AS eddie"

    x = N(label="thing", As="dude")
    assert x.label == "thing" and x._as == "dude"
    assert x.Return() == f"{x._var} AS dude"

    # relationships
    assert isinstance(R0(), R)
    assert not R0().Type
    assert not R0().props
    assert not R0()._var

    r = R(Type="has_a")
    assert re.match("^r[0-9]+$", r._var)
    s = R(Type="is_a")
    assert r._var != s._var
    assert r.pattern() == f"-[{r._var}:has_a]-"
    assert _pattern(r) == f"-[{r._var}:has_a]-"
    assert not r.condition()
    assert not _condition(r)
    assert r.Return() == f"{r._var}"
    assert _return(r) == f"{r._var}"

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
    assert q.condition() == f"{w._var}.weight = 12"
    assert _condition(q) == f"{w._var}.weight = 12"
    x = N(label="item", props=l)
    assert _condition(l) == f"{x._var}.color = 'blue'"
    y = N(label="item", props=t)
    assert _condition(t) == f"{y._var}.spin = $parm"

    z = y.relate_to(r, x)
    assert isinstance(z, T)
    assert z.pattern() == (
        f"({y._var}:item {{spin:$parm}})-[{r._var}:has_a]->({x._var}:item "
        "{color:'blue'})"
    )
    assert z.pattern() == z.condition()
    assert _pattern(z) == _condition(z)

    u = s.relate(w, x)
    assert isinstance(u, T)
    assert _pattern(_plain(u)) == (f"({w._var}:item)-[{s._var}:is_a]->({x._var}:item)")

    u = _anon(s).relate(w, _anon(x))
    assert _pattern(_plain(u)) == (f"({w._var}:item)-[:is_a]->(:item)")

    u = R0().relate(_var(w), _var(x))
    assert _pattern(_plain(u)) == (f"({w._var})-->({x._var})")

    assert _pattern(R0().relate(N0(), N0())) == "()-->()"


def test_paths():
    # happy paths:
    # G(N, R, N), G(T, T), G(N, R, T), G(T, R, N)
    # G(N, R, P), G(G, R, N)
    # G(N, R, N, R, N, R, N), G(T, G), G(G, T)
    # G(G, G)
    # G(G, R, N, R, T) ...
    # unhappy paths: with pytest.raises(Exception)
    # G(N), G(R), G(N, R), G(R, N), G(N, N)
    # G(N, T), G(R, T), G(N, G), G(R, G)
    # G(N, R, N, R, N, R)
    nodes = [N(label="case"), N(label="sample"), N(label="aliquot"), N(label="file")]
    edges = [R(Type="of_case"), R(Type="of_sample"), R(Type="of_aliquot")]

    t1 = edges[0].relate(nodes[1], nodes[0])  # (sample)-[:of_case]->(case)
    t2 = edges[1].relate(nodes[2], nodes[1])  # (aliquot)-[:of_sample]->(sample)
    t3 = edges[2].relate(nodes[3], nodes[2])  # (file)-[:of_aliquot]->(aliquot)

    pth0 = G(nodes[1], edges[0], nodes[0])  # G(N, R, N)
    assert re.match(
        "\\(n[0-9]+:sample\\)-\\[r[0-9]+:of_case\\]->\\(n[0-9]+:case\\)",
        pth0.pattern(),
    )
    pth1 = G(t1)  # G(T)
    assert re.match(
        "\\(n[0-9]+:sample\\)-\\[r[0-9]+:of_case\\]->\\(n[0-9]+:case\\)",
        pth1.pattern(),
    )
    pth2 = G(t1, t2)  # G(T, T)
    assert re.match(
        "\\(n[0-9]+:aliquot\\)-\\[r[0-9]+:of_sample\\]->\\(n[0-9]+:sample\\)-\\[r[0-9]+:of_case\\]->\\(n[0-9]+:case\\)",
        pth2.pattern(),
    )
    pth3 = G(t2)
    pth4 = G(pth1, pth3)  # G(G, G)
    assert re.match(
        "\\(n[0-9]+:aliquot\\)-\\[r[0-9]+:of_sample\\]->\\(n[0-9]+:sample\\)-\\[r[0-9]+:of_case\\]->\\(n[0-9]+:case\\)",
        pth4.pattern(),
    )
    pth5 = G(t2, nodes[1], edges[2], nodes[3])
    assert re.match(
        "\\(n[0-9]+:aliquot\\)-\\[r[0-9]+:of_sample\\]->\\(n[0-9]+:sample\\)-\\[r[0-9]+:of_aliquot\\]->\\(n[0-9]+:file\\)",
        pth5.pattern(),
    )
    pth6 = G(t2, edges[2], nodes[3])  # G(T, R, N)
    assert re.match(
        "\\(n[0-9]+:aliquot\\)-\\[r[0-9]+:of_sample\\]->\\(n[0-9]+:sample\\)-\\[r[0-9]+:of_aliquot\\]->\\(n[0-9]+:file\\)",
        pth6.pattern(),
    )
    pth7 = G(nodes[0], edges[0], t2)  # G(N, R, T)
    pth8 = G(pth1, edges[1], nodes[2], edges[2], t3)
    assert re.match(
        "\\(n[0-9]+:sample\\)-\\[r[0-9]+:of_case\\]->\\(n[0-9]+:case\\)-\\[r[0-9]+:of_sample\\]->\\(n[0-9]+:aliquot\\)<-\\[r[0-9]+:of_aliquot\\]-\\(n[0-9]+:file\\)",
        pth8.pattern(),
    )
    pth9 = G(t1, nodes[2], edges[1], nodes[1], t3)
    assert re.match(
        "\\(n[0-9]+:file\\)-\\[r[0-9]+:of_aliquot\\]->\\(n[0-9]+:aliquot\\)-\\[r[0-9]+:of_sample\\]->\\(n[0-9]+:sample\\)-\\[r[0-9]+:of_case\\]->\\(n[0-9]+:case\\)",
        pth9.pattern(),
    )

    with pytest.raises(RuntimeError, match="needs _join hints"):
        pth10 = G(t1, edges[1], t3)
    edges[1]._join = ["sample", "aliquot"]
    assert re.match(
        "\\(n[0-9]+:file\\)-\\[r[0-9]+:of_aliquot\\]->\\(n[0-9]+:aliquot\\)-\\[r[0-9]+:of_sample\\]->\\(n[0-9]+:sample\\)-\\[r[0-9]+:of_case\\]->\\(n[0-9]+:case\\)",
        pth9.pattern(),
    )

    with pytest.raises(RuntimeError, match="do not define a complete Path"):
        G(nodes[0])  # G(N)
    with pytest.raises(RuntimeError, match="is not valid at arg position 1"):
        G(edges[0])  # G(R)
    with pytest.raises(RuntimeError, match="do not define a complete Path"):
        G(nodes[0], edges[0])  # G(N, R)
    with pytest.raises(RuntimeError, match="is not valid at arg position 2"):
        G(nodes[0], nodes[1])  # G(N, N)
    with pytest.raises(RuntimeError, match="is not valid at arg position 2"):
        G(nodes[0], t1)  # G(N, T)
    with pytest.raises(RuntimeError, match="is not valid at arg position 1"):
        G(edges[1], t1)  # G(R, T)
    with pytest.raises(RuntimeError, match="do not define a complete Path"):
        G(nodes[0], edges[0], nodes[1], nodes[2], edges[1])  # G(N, R, N, N, R)
    with pytest.raises(RuntimeError, match="from-node is ambiguous"):
        G(pth4, edges[2], nodes[3])  # G(G, R, N) when num G triples > 1
    with pytest.raises(RuntimeError, match="to-node is ambiguous"):
        G(nodes[3], edges[2], pth4)  # G(G, R, N) when num G triples > 1
    # two overlapping triples work: call it a feature
    G(nodes[1], edges[0], nodes[0], nodes[2], edges[1], nodes[1])

    # equivalent
    G(nodes[2], edges[1], nodes[1], edges[0], nodes[0])

    mm = G(
        R(Type="funk").relate(_plain_var(nodes[0]), _plain_var(nodes[1])),
        R(Type="master").relate(_plain_var(nodes[0]), _plain_var(nodes[2])),
    )
    assert len(mm.triples) == 2

    with pytest.raises(RuntimeError, match="do not overlap"):
        G(t1, t3)
    # same semantics as G(t1, t2), but not the same objects:
    with pytest.raises(RuntimeError, match="do not overlap"):
        G(
            t1,
            R(Type=edges[1].Type).relate(
                N(label=nodes[2].label),
                N(label=nodes[1].label),
            ),
        )


def test_clauses():
    n = N(label="node", props={"model": "ICDC", "handle": "diagnosis"})
    m = N(label="property", props={"handle": "disease_type"})
    t = _anon(R(Type="has_property")).relate(n, m)

    c = count(n)
    assert isinstance(c, count)
    assert isinstance(c, Func)
    assert str(c) == f"count({n._var})"
    assert str(count("this")) == "count(this)"
    x = exists(m.props["handle"])
    assert isinstance(x, exists)
    assert isinstance(x, Func)
    assert str(x) == f"exists({m._var}.handle)"
    assert str(exists("this.that")) == "exists(this.that)"

    match = Match(t)
    assert isinstance(match, Match)
    assert isinstance(match, Clause)
    assert str(match) == (
        f"MATCH ({n._var}:node {{model:'ICDC',handle:'diagnosis'}})"
        f"-[:has_property]->({m._var}:property {{handle:'disease_type'}})"
    )

    where = Where(*t.nodes())
    assert isinstance(where, Where)
    assert isinstance(where, Clause)
    assert str(where) == (
        f"WHERE {n._var}.model = 'ICDC' AND {n._var}.handle = 'diagnosis' "
        f"AND {m._var}.handle = 'disease_type'"
    )

    ret = Return(t)
    assert isinstance(ret, Return)
    assert isinstance(ret, Clause)
    assert str(ret) == (f"RETURN {n._var}, {m._var}")

    st = Set(*n.props.values())
    assert isinstance(st, Set)
    assert isinstance(st, Clause)
    assert str(st) == f"SET {n._var}.model = 'ICDC', {n._var}.handle = 'diagnosis'"

    st = OnMatchSet(*n.props.values())
    assert isinstance(st, Set)
    assert isinstance(st, Clause)
    assert (
        str(st)
        == f"ON MATCH SET {n._var}.model = 'ICDC', {n._var}.handle = 'diagnosis'"
    )

    st = OnCreateSet(*n.props.values())
    assert isinstance(st, Set)
    assert isinstance(st, Clause)
    assert (
        str(st)
        == f"ON CREATE SET {n._var}.model = 'ICDC', {n._var}.handle = 'diagnosis'"
    )


def test_statments():
    n = N(label="node", props={"model": "ICDC", "handle": "diagnosis"})
    m = N(label="property", props={"handle": "disease_type"})
    t = _anon(R(Type="has_property")).relate(n, m)
    p = P(handle="boog")
    p.entity = n

    assert str(
        Statement(
            Match(_var(_plain(t))),
            Where(exists(m.props["handle"]), n),
            Return(count(n)),
        ),
    ) == (
        f"MATCH ({n._var})-[:has_property]->({m._var}) "
        f"WHERE exists({m._var}.handle) AND {n._var}.model = 'ICDC' AND "
        f"{n._var}.handle = 'diagnosis' "
        f"RETURN count({n._var})"
    )

    assert str(
        Statement(
            Match(_var(_plain(t))),
            Where(exists(m.props["handle"]), n),
            Return(count(n)),
            use_params=True,
        ),
    ) == (
        "MATCH ({n})-[:has_property]->({m}) "
        "WHERE exists({m}.handle) AND {n}.model = ${p0} AND "
        "{n}.handle = ${p1} "
        "RETURN count({n})"
    ).format(n=n._var, m=m._var, p0=n.props["model"]._var, p1=n.props["handle"]._var)

    assert Statement(
        Match(_var(_plain(t))),
        Where(exists(m.props["handle"]), n),
        Return(count(n)),
        use_params=True,
    ).params == {
        n.props["model"]._var: "ICDC",
        n.props["handle"]._var: "diagnosis",
    }

    assert str(
        Statement(
            Match(_var(_plain(t))),
            Where(
                group(And(exists(m.props["handle"]), n.props["model"])),
                Not(n.props["handle"]),
            ),
            Return(p),
            "LIMIT 10",
        ),
    ) == (
        f"MATCH ({n._var})-[:has_property]->({m._var}) "
        f"WHERE (exists({m._var}.handle) AND {n._var}.model = 'ICDC') AND NOT "
        f"{n._var}.handle = 'diagnosis' "
        f"RETURN {n._var}.boog LIMIT 10"
    )

    assert str(
        Statement(
            Create(_plain(n)),
            Set(*n.props.values()),
            Return(n),
        ),
    ) == (
        f"CREATE ({n._var}:node) "
        f"SET {n._var}.model = 'ICDC', {n._var}.handle = 'diagnosis' "
        f"RETURN {n._var}"
    )

    assert str(
        Statement(
            Merge(_plain(n)),
            OnCreateSet(*n.props.values()),
            Return(n),
        ),
    ) == (
        f"MERGE ({n._var}:node) "
        f"ON CREATE SET {n._var}.model = 'ICDC', {n._var}.handle = 'diagnosis' "
        f"RETURN {n._var}"
    )

    assert str(
        Statement(
            Merge(_plain(n)),
            OnMatchSet(*n.props.values()),
            Return(n),
        ),
    ) == (
        f"MERGE ({n._var}:node) "
        f"ON MATCH SET {n._var}.model = 'ICDC', {n._var}.handle = 'diagnosis' "
        f"RETURN {n._var}"
    )

    assert str(
        Statement(
            Match(n),
            Remove(n, label="node"),
        ),
    ) == (
        f"MATCH ({n._var}:node {{model:'ICDC',handle:'diagnosis'}}) REMOVE {n._var}:node"
    )

    assert str(
        Statement(
            Match(n),
            Remove(n, prop="nanoid"),
        ),
    ) == (
        f"MATCH ({n._var}:node {{model:'ICDC',handle:'diagnosis'}}) "
        f"REMOVE {n._var}.nanoid"
    )
