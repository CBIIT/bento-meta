"""
mdb.loaders: load models into an MDB instance consistently
"""

from tqdm import tqdm
from bento_meta.mdb import WriteableMDB
from bento_meta.util.cypher.entities import (
    N, R, P, T, G, _plain_var
    )
from bento_meta.util.cypher.clauses import (
    Match, Create, Merge, Set, OnMatchSet, OnCreateSet,
    Remove, Statement,
    )


def load_mdf(mdf, mdb, _commit=None):
    """Load an MDF object into an MDB instance"""
    load_model(mdf.model, mdb, _commit)


def load_model(model, mdb, _commit=None):
    """Load a model object into an MDB instance."""
    if not isinstance(mdb, WriteableMDB):
        raise RuntimeError("mdb object must be a WriteableMDB")
    cstmts = load_model_statements(model, _commit)
    for stmt in tqdm(cstmts):
        mdb.put_with_statement(str(stmt), stmt.params)


def load_model_statements(model, _commit=None):
    """
    Create Cypher statements from a model to load it de novo into an
    MDB instance.

    :param :class:`mdb.Model` model: Model instance for loading
    :param str _commit: 'Commit string' for marking entities in DB. If set, this will override
    _commit attributes already existing on Model entities.
    """
    cStatements = []
    cNodes = {}
    for nd in model.nodes:
        node = model.nodes[nd]
        cNode = _cEntity(node, model, _commit)
        cStatements.append(
            Statement(
                Merge(cNode),
                use_params=True
                )
            )
        cNodes[node.handle] = cNode
        cProps = []
        if node.tags:
            cStatements.extend(
                _tag_statements(node, cNode, _commit)
                )
        if node.props:
            cStatements.extend(
                _prop_statements(node, cNode, model, _commit)
                )
        if node.concept:
            cStatements.extend(
                _annotate_statements(node, cNode, _commit)
            )
    # node nodes and node-property nodes now exist
    # nodes are linked to properties
    for rl in model.edges:
        edge = model.edges[rl]
        cEdge = _cEntity(edge, model, _commit)
        cSrc = _cEntity(edge.src, model, _commit)
        cDst = _cEntity(edge.dst, model, _commit)

        if edge.multiplicity:
            cEdge._add_props({"multiplicity": edge.multiplicity})
        if edge.is_required:
            cEdge._add_props({"is_required": edge.is_required})
        # ensure uniqueness for merge
        cEdge._add_props({"__u":str(rl)})
        cStatements.extend([
            Statement(
                Create(cEdge),
                use_params=True
                ),
            Statement(
                Match(cEdge, cSrc, cDst),
                Merge(
                    R(Type="has_src").relate(_plain_var(cEdge), _plain_var(cSrc))
                    ),
                Merge(
                      R(Type="has_dst").relate(_plain_var(cEdge), _plain_var(cDst))
                ),
                use_params=True
                )])
        if edge.tags:
            cStatements.extend(
                _tag_statements(edge, cEdge, _commit)
                )
        if edge.props:
            cStatements.extend(
                _prop_statements(edge, cEdge, model, _commit)
                )
        if edge.concept:
            cStatements.extend(
                _annotate_statements(edge, cEdge, _commit)
                )
        cStatements.append(
            Statement(
                Match(cEdge),
                Remove(cEdge, prop="__u"),
                use_params=True
                )
            )
    # edge node and edge-property nodes now exist

    # now go through all properties that the model object knows about
    # - these should already have been created or merged, but
    # - if the property list on the model is missing any properties
    # - that nodes or edges have on themselves, then this indicates
    # - a bug/inconsistency  - and the property won't receive its
    # - value_set/term list in the DB in the following code.

    for pr in [x for x in model.props.values()
               if x.value_domain == 'value_set']:
        cValueSet = _cEntity(pr.value_set, model, _commit)
        cProp = _cEntity(pr, model, _commit)
        cStatements.extend([
            Statement(
                Merge(cValueSet),
                use_params=True
                ),
            Statement(
                Match(cProp, cValueSet),
                Merge(R(Type="has_value_set").
                      relate(_plain_var(cProp),
                             _plain_var(cValueSet))),
                use_params=True
                )
            ])
        if pr.concept:
            cStatements.extend(
                _annotate_statements(pr, cProp, _commit)
                )
        for tm in pr.terms.values():
            cTerm = _cEntity(tm, model, _commit)
            cStatements.extend([
                Statement(
                    Merge(cTerm),
                    use_params=True
                    ),
                Statement(
                    Match(cValueSet, cTerm),
                    Merge(R(Type="has_term").relate(_plain_var(cValueSet),
                                                    _plain_var(cTerm))),
                    use_params=True
                    )
                ])
    return cStatements


def _cEntity(ent, model, _commit):
    label = type(ent).__name__.lower()
    cEnt = None

    # translate labels
    if label == 'edge':
        label = 'relationship'
    if label == 'valueset':
        label = 'value_set'

    # special handling
    if label == 'term':
        cEnt = N(label=label,
                 props={"value": ent.value})
        if ent.origin_name:
            cEnt._add_props({"origin_name": ent.origin_name})
        if ent.origin_id:
            cEnt._add_props({"origin_id": ent.origin_id})
        if ent.origin_version:
            cEnt._add_props({"origin_version": ent.origin_version})
        if ent.origin_definition:
            cEnt._add_props({"origin_defintion": ent.origin_definition})
        if ent.handle:
            cEnt._add_props({"handle": ent.handle})
    elif label == 'value_set':
        cEnt = N(label='value_set',
                 props={"handle": ent.handle})
        if ent.url:
            cEnt._add_props({"url": ent.url})
    elif label == 'concept':
        cEnt = N(label='concept')
    elif label == 'tag':
        cEnt = N(label="tag",
                 props={"key": ent.key,
                        "value": ent.value})
        
    else:
        cEnt = N(label=label,
                 props={"handle": ent.handle,
                        "model": model.handle})
    # all ents
    if _commit:
        cEnt._add_props({"_commit": _commit})
    else:
        if ent._commit:
            cEnt._add_props({"_commit": ent._commit})
    if ent.nanoid:
        cEnt._add_props({"nanoid": ent.nanoid})
    if ent.desc:
        cEnt._add_props({"desc": ent.desc})
    return cEnt


def _tag_statements(ent, cEnt, _commit):
    stmts = []
    cTags = []
    if ent.tags:
        for t in ent.tags.values():
            cTag = _cEntity(t, None, _commit)
            cTags.append(cTag)
    for ct in cTags:
        stmts.append(
            Statement(
                Match(cEnt),
                Merge(R(Type="has_tag").relate(_plain_var(cEnt), ct)),
                use_params=True
                )
            )
    return stmts


def _prop_statements(ent, cEnt, model, _commit):
    stmts = []
    for p in ent.props.values():
        cProp = _cEntity(p, model, _commit)
        cProp._add_props({"value_domain": p.value_domain})
        stmts.extend([
            Statement(
                Merge(cProp),
                use_params=True
                ),
            Statement(
                Match(cEnt, cProp),
                Merge(R(Type="has_property").relate(
                    _plain_var(cEnt), _plain_var(cProp))),
                use_params=True
                ),
            ])
        if p.tags:
            stmts.extend(
                _tag_statements(p, cProp, _commit)
                )
    return stmts


def _annotate_statements(ent, cEnt, _commit):
    stmts = []
    if not ent.concept:
        return []
    cConcept = _cEntity(ent.concept, None, _commit)
    stmts = []
    for tm in ent.concept.terms.values():
        cTerm = _cEntity(tm, None, _commit)
        stmts.extend([
            Statement(
                Merge(cTerm),
                use_params=True
            ),
            Statement(
                Match(cEnt),
                Merge(R(Type="has_concept").relate(
                    _plain_var(cEnt), cConcept)),
                use_params=True
            ),
            Statement(
                Match(R(Type="has_concept").relate(
                    cEnt, cConcept), cTerm),
                Merge(R(Type="represents").relate(
                    _plain_var(cTerm), _plain_var(cConcept))),
                use_params=True
            ),
        ])
    return stmts
