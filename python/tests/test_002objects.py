import sys
import json
sys.path.insert(0, ".")
sys.path.insert(0, "..")
from bento_meta.entity import Entity
from bento_meta.objects import (
    Concept,
    Edge,
    Node,
    Origin,
    Predicate,
    Property,
    Tag,
    Term,
    ValueSet,
)
from bento_meta.tf_objects import (
    Transform,
    TfStep,
)


def test_create_objects():
    for cls in [Node, Property, Edge, Term, ValueSet,
                Concept, Origin, Tag, Transform, TfStep]:
        n = cls()
        assert n
        assert isinstance(n, Entity)


def test_init_and_link_objects():
    case = Node({"model": "test", "handle": "case"})
    assert case
    assert case.model == "test"
    assert case.handle == "case"
    sample = Node({"model": "test", "handle": "sample"})
    assert sample
    of_sample = Edge({"model": "test", "handle": "of_sample"})
    assert of_sample
    assert of_sample.model == "test"
    assert of_sample.handle == "of_sample"
    of_sample.src = sample
    of_sample.dst = case
    assert of_sample.dst == case
    assert of_sample.src == sample
    term = Term({"value": "sample"})
    concept = Concept()
    term.concept = concept
    other_concept = Concept()
    concept.terms[("sample", None, None, None)] = term
    sample.concept = concept
    [o] = [x for x in term.belongs.values()]
    assert o == concept
    assert of_sample.src.concept.terms[("sample", None, None, None)].value == "sample"
    assert of_sample.src.annotations[("sample", None, None, None)].value == "sample"
    pred = Predicate({"subject": concept, "object": other_concept, "handle": "isa"})
    assert isinstance(pred.subject, Concept)
    assert isinstance(pred.object, Concept)


def test_init_and_link_tf_objects():
    p_src = Property({
        "handle": "from_prop",
        "model": "test1",
        "version": "1.0",
        "value_domain": "integer",
        "nanoid": "ooga"
        })
    p_dst = Property({
        "handle": "to_prop",
        "model": "test2",
        "version": "1.1",
        "value_domain": "string",
        "nanoid":"BooGA"
        })
    trans = Transform({
        "handle": "test_transform",
        "desc": "it's a test",
        "version": "Q32",
        "source": "human",
        "input_props": {1:p_src},
        "output_props": {2:p_dst}
        })
    assert isinstance(trans, Transform)
    assert trans.source == "human"
    assert trans.desc == "it's a test"

    tfstep1 = TfStep({
        "package": "bento-transforms@1.0.1",
        "entrypoint": "bento_transforms.arith.days_to_years",
        "params_json": '{"divisor":365}',
        })
    assert isinstance(tfstep1, TfStep)
    assert tfstep1.params_json == '{"divisor":365}'
    assert tfstep1.params["divisor"] == 365

    tfstep2 = TfStep({
        "package": "bento-transforms@1.0.1",
        "entrypoint": "bento_transforms.format",
        "params_json": '{"format_string": "%s years"}'
    })

    tfstep3 = TfStep({
        "package": "bento-transforms@1.0.1",
        "entrypoint": "bento_transforms.to_lang",
        "params_json": '{"language": "Klingon"}'
    })

    tfstep1.next_step = tfstep2
    tfstep2.next_step = tfstep3
    trans.first_step = tfstep1
    trans.last_step = tfstep3

    assert trans.steps == [tfstep1, tfstep2, tfstep3]
    
        

def test_tags_on_objects():
    nodeTag = Tag({"key": "name", "value": "Neddy"})
    relnTag = Tag({"key": "name", "value": "Robby"})
    conceptTag = Tag({"key": "name", "value": "Catty"})
    conceptTag2 = Tag({"key": "aka", "value": "Jehoshaphat"})
    termTag = Tag({"key": "name", "value": "Termy"})
    propTag = Tag({"key": "name", "value": "Puppy"})
    transTag = Tag({"key": "name", "value": "Cissy"})
    stepTag = Tag({"key": "name", "value":"Steppy"})

    case = Node({"model": "test", "handle": "case"})
    of_sample = Edge({"model": "test", "handle": "of_sample"})
    sample = Node({"model": "test", "handle": "sample"})
    of_sample.src = sample
    of_sample.dst = case
    term = Term({"value": "sample"})
    concept = Concept()
    term.concept = concept
    concept.terms[("sample", None, None, None)] = term
    sample.concept = concept
    sample.props["this"] = Property({"that": "this"})

    case.tags[nodeTag.key] = nodeTag
    of_sample.tags[relnTag.key] = relnTag
    term.tags[termTag.key] = termTag
    concept.tags[conceptTag.key] = conceptTag
    concept.tags[conceptTag2.key] = conceptTag2
    sample.props["this"].tags["name"] = propTag

    trans = Transform({
        "handle": "test_transform",
        "desc": "it's a test",
        "version": "Q32",
        "source": "human",
        })
    tfstep1 = TfStep({
        "package": "bento-transforms@1.0.1",
        "entrypoint": "bento_transforms.arith.days_to_years",
        "params_json": '{"divisor":365}',
        })
    trans.tags[transTag.key] = transTag
    tfstep1.tags[stepTag.key] = stepTag
    names = [
        x.tags["name"].value
        for x in [case, of_sample, term, concept, sample.props["this"], trans, tfstep1]
    ]
    assert names == ["Neddy", "Robby", "Termy", "Catty", "Puppy", "Cissy", "Steppy"]
    assert concept.tags["aka"].value == "Jehoshaphat"


def test_some_object_methods():
    p = Property({"handle": "complaint"})
    assert p
    t = Term({"value": "halitosis"})
    assert t
    u = Term({"value": "ptomaine"})
    assert u
    vs = ValueSet({"_id": "1"})
    assert vs
    p.value_set = vs
    p.value_types.append("glarp")
    assert "glarp" in p.value_types
    vs.terms["ptomaine"] = u
    assert p.terms["ptomaine"].value == "ptomaine"
    p.terms["halitosis"] = t
    assert vs.terms["halitosis"].value == "halitosis"
    vals = p.values
    assert isinstance(vals, list)
    assert "ptomaine" in vals
    assert "halitosis" in vals
    s = Node({"handle": "case"})
    assert s
    d = Node({"handle": "cohort"})
    assert d
    e = Edge({"handle": "member_of", "src": s, "dst": d})
    assert e
    assert e.triplet == ("member_of", "case", "cohort")
    # test get_label() method
    assert p.get_label() == "property"
    assert t.get_label() == "term"
    assert vs.get_label() == "value_set"
    assert s.get_label() == "node"
    assert e.get_label() == "relationship"


def test_get_key_prop() -> None:
    """Test get_key_prop() method."""
    pk1 = Property({"handle": "major_key", "is_key": True})
    pk2 = Property({"handle": "minor_key", "is_key": True})
    nk1 = Property({"handle": "keyless", "is_key": False})
    n = Node({"handle": "lock", "model": "test"})
    assert n.get_key_prop() is None
    n.props[pk1.handle] = pk1
    assert n.get_key_prop() == pk1
    n.props[nk1.handle] = nk1
    assert n.get_key_prop() == pk1
    n.props[pk2.handle] = pk2
    assert n.get_key_prop() == [pk1, pk2]

def test_edp_related_updates() -> None:
    """Test that an EDP term can have a valueset"""
    vs = ValueSet({"handle": "icd_o_3_morphology"})
    edp = Term({"origin_name": "CRDC",
                "value": "ICD-O-3 Morphology v3.2",
                "origin_id": "CRDC00001",
                "origin_version": "1"})
    t1 = Term({"value": "Neoplasm, malignant",
               "origin_name": "ICDO3",
               "origin_version": "3.2",
               "origin_id": "8000/6"})
    t2 = Term({"value": "Squamous cell carcinoma, keratinizing, NOS",
               "origin_name": "ICDO3",
               "origin_version": "3.2",
               "origin_id": "8071/3"})
    t3 = Term({"value": "Glomus tumor, NOS",
               "origin_name": "ICDO3",
               "origin_version": "3.2",
               "origin_id": "8711/0"})
    vs.terms["Neoplasm, malignant"] = t1
    vs.terms["Squamous cell carcinoma, keratinizing, NOS"] = t2
    vs.terms["Glomus tumor, NOS"] = t3
    vs.edp_term = edp
    edp.value_set = vs

    assert len(edp.terms) == 3
    assert edp.terms == vs.terms
    assert vs.edp_term == edp

    # ensure you can reference the attributes and get back None
    # (instead of exception)
    # when appropriate (ie, value set is not an edp valueset,
    # term is not an edp term
    vs = ValueSet({"handle": "not_an_edp_valueset"})
    assert vs.edp_term is None
    assert t1.terms is None
    
