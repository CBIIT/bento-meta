import sys

sys.path.insert(0, ".")
sys.path.insert(0, "..")

import neo4j.graph
import pytest
from bento_meta.object_map import ObjectMap
from bento_meta.objects import Concept, Node, Property, Term, ValueSet
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError
from pdb import set_trace

@pytest.mark.docker
def test_get(test_mdb):
    (b, h) = test_mdb
    drv = GraphDatabase.driver(b)
    assert drv
    node_map = ObjectMap(cls=Node, drv=drv)
    Node.object_map = node_map
    Concept.object_map = ObjectMap(cls=Concept, drv=drv)
    Property.object_map = ObjectMap(cls=Property, drv=drv)
    n_id = None
    with node_map.drv.session() as session:
        result = session.run("match (a:node) where a.nanoid = 'VTUKex' return id(a) limit 1")
        n_id = result.single().value()
    node = Node()
    node.neoid = n_id
    node_map.get(node, refresh=False)
    assert node.dirty == 0
    assert node.__dict__["concept"].dirty == -1  # before dget()
    assert node.concept.dirty == 0  # after dget()
    assert node.concept.nanoid == "NfoVKj"
    assert len(node.props) == 39
    assert node.props.data["AcquisitionMethodType"].dirty == -1  # before dget()
    assert node.props["AcquisitionMethodType"].dirty == 0  # after dget()
    assert node.props["AcquisitionMethodType"].model == "HTAN"
    concept = node.concept
    assert concept.belongs[(id(node), "concept")] == node
    owners = node_map.get_owners(node)
    assert len(owners) == 22
    cncpt = Concept()
    Concept.object_map.get_by_id(cncpt, concept._id)
    assert cncpt.terms[0] == concept.terms[0]


@pytest.mark.docker
def test_put_rm(test_mdb):
    (b, h) = test_mdb
    drv = GraphDatabase.driver(b)
    vs_map = ObjectMap(cls=ValueSet, drv=drv)
    term_map = ObjectMap(cls=Term, drv=drv)
    vs = ValueSet({"nanoid": "narbBB"})
    terms = [Term({"value": x}) for x in ["quilm", "ferb", "narquit"]]
    vs.terms = terms
    assert vs.terms["ferb"].value == "ferb"
    vs_map.put(vs)
    rt = []
    with vs_map.drv.session() as session:
        result = session.run(
            "match (v:value_set)-[:has_term]->(t:term) where v.nanoid='narbBB' return t order by t.value",
        )
        for rec in result:
            rt.append(rec["t"]["value"])
    assert set(rt) == set(["ferb", "narquit", "quilm"])
    quilm = vs.terms["quilm"]
    q_id = quilm.neoid
    del vs.terms["quilm"]
    assert len(vs.terms) == 2
    with pytest.raises(Neo4jError, match=".*Cannot delete"):
        term_map.rm(quilm)

    with term_map.drv.session() as session:
        result = session.run("match (t:term {value:'quilm'}) return id(t)")
        t_id = result.single().value()
    assert t_id == q_id
    term_map.rm(quilm, force=1)
    with term_map.drv.session() as session:
        result = session.run("match (t:term {value:'quilm'}) return t.nanoid")
        assert result.single() == None

    new_term = Term({"value": "belpit"})
    term_map.put(new_term)
    vs_map.add(vs, "terms", new_term)
    assert len(vs.terms) == 2
    vs_map.get(vs, refresh=True)
    assert len(vs.terms) == 3
    assert vs.terms["belpit"]
    old_term = vs.terms["ferb"]
    r = None
    with term_map.drv.session() as session:
        result = session.run(
            "match (t:term {value:'ferb'})<-[r]-(v:value_set) return r",
        )
        r = result.single().value()
        assert isinstance(r, neo4j.graph.Relationship)
    vs_map.drop(vs, "terms", old_term)
    with term_map.drv.session() as session:
        result = session.run(
            "match (t:term {value:'ferb'})<-[r]-(v:value_set) return r",
        )
        assert result.single() == None
    old_term = vs.terms["belpit"]
