"""
mdb.loaders: load models into an MDB instance consistently
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from minicypher.clauses import (
    Create,
    Match,
    Merge,
    Remove,
)
from minicypher.entities import N, R, _plain_var
from minicypher.statement import Statement
from tqdm import tqdm

from bento_meta.mdb.writeable import WriteableMDB

if TYPE_CHECKING:
    from minicypher.entities import Entity as CypherEntity

    from bento_meta.entity import Entity
    from bento_meta.model import Model


class MDFProtocol(Protocol):
    """
    Protocol defining the expected interface for MDF objects from bento-mdf package.

    This protocol is used to provide type hints without creating a circular dependency,
    since bento-mdf depends on bento-meta.
    """

    model: Model


def load_mdf(mdf: MDFProtocol, mdb: WriteableMDB, _commit: str | None = None) -> None:
    """Load an MDF object into an MDB instance."""
    load_model(mdf.model, mdb, _commit)


def load_model(model: Model, mdb: WriteableMDB, _commit: str | None = None) -> None:
    """Load a model object into an MDB instance."""
    if not isinstance(mdb, WriteableMDB):
        msg = "mdb object must be a WriteableMDB"
        raise TypeError(msg)
    cstmts = load_model_statements(model, _commit)
    for stmt in tqdm(cstmts):
        mdb.put_with_statement(str(stmt), stmt.params)


def load_model_statements(model: Model, _commit: str | None = None) -> list[Statement]:
    """
    Create Cypher statements from a model to load it de novo into an MDB instance.

    :param :class:`mdb.Model` model: Model instance for loading
    :param str _commit: 'Commit string' for marking entities in DB. If set,
        this will override _commit attributes already existing on Model entities.
    """
    c_statements: list[Statement] = []
    c_nodes = {}
    for nd in model.nodes:
        node = model.nodes[nd]
        c_node = _c_entity(node, model, _commit)
        c_statements.append(
            Statement(
                Merge(c_node),
                use_params=True,
            ),
        )
        c_nodes[node.handle] = c_node
        c_props = []
        if node.tags:
            c_statements.extend(
                _tag_statements(node, c_node, _commit),
            )
        if node.props:
            c_statements.extend(
                _prop_statements(node, c_node, model, _commit),
            )
        if node.concept:
            c_statements.extend(
                _annotate_statements(node, c_node, _commit),
            )
    # node nodes and node-property nodes now exist
    # nodes are linked to properties
    for rl in model.edges:
        edge = model.edges[rl]
        c_edge = _c_entity(edge, model, _commit)
        c_src = _c_entity(edge.src, model, _commit)
        c_dst = _c_entity(edge.dst, model, _commit)

        if edge.multiplicity:
            c_edge._add_props({"multiplicity": edge.multiplicity})
        if edge.is_required:
            c_edge._add_props({"is_required": edge.is_required})
        # ensure uniqueness for merge
        c_edge._add_props({"__u": str(rl)})
        c_statements.extend(
            [
                Statement(
                    Create(c_edge),
                    use_params=True,
                ),
                Statement(
                    Match(c_edge, c_src, c_dst),
                    Merge(
                        R(Type="has_src").relate(_plain_var(c_edge), _plain_var(c_src)),
                    ),
                    Merge(
                        R(Type="has_dst").relate(_plain_var(c_edge), _plain_var(c_dst)),
                    ),
                    use_params=True,
                ),
            ],
        )
        if edge.tags:
            c_statements.extend(
                _tag_statements(edge, c_edge, _commit),
            )
        if edge.props:
            c_statements.extend(
                _prop_statements(edge, c_edge, model, _commit),
            )
        if edge.concept:
            c_statements.extend(
                _annotate_statements(edge, c_edge, _commit),
            )
        c_statements.append(
            Statement(
                Match(c_edge),
                Remove(c_edge, prop="__u"),
                use_params=True,
            ),
        )
    # edge node and edge-property nodes now exist

    # now go through all properties that the model object knows about
    # - these should already have been created or merged, but
    # - if the property list on the model is missing any properties
    # - that nodes or edges have on themselves, then this indicates
    # - a bug/inconsistency  - and the property won't receive its
    # - value_set/term list in the DB in the following code.

    for pr in [x for x in model.props.values() if x.value_domain == "value_set"]:
        c_value_set = _c_entity(pr.value_set, model, _commit)
        c_prop = _c_entity(pr, model, _commit)
        c_statements.extend(
            [
                Statement(
                    Merge(c_value_set),
                    use_params=True,
                ),
                Statement(
                    Match(c_prop, c_value_set),
                    Merge(
                        R(Type="has_value_set").relate(
                            _plain_var(c_prop),
                            _plain_var(c_value_set),
                        ),
                    ),
                    use_params=True,
                ),
            ],
        )
        if pr.concept:
            c_statements.extend(
                _annotate_statements(pr, c_prop, _commit),
            )
        for tm in pr.terms.values():
            c_term = _c_entity(tm, model, _commit)
            c_statements.extend(
                [
                    Statement(
                        Merge(c_term),
                        use_params=True,
                    ),
                    Statement(
                        Match(c_value_set, c_term),
                        Merge(
                            R(Type="has_term").relate(
                                _plain_var(c_value_set),
                                _plain_var(c_term),
                            ),
                        ),
                        use_params=True,
                    ),
                ],
            )
    return c_statements


def _c_entity(ent: Entity, model: Model | None, _commit: str | None = None) -> N:
    label = type(ent).__name__.lower()
    c_ent = None

    # translate labels
    if label == "edge":
        label = "relationship"
    if label == "valueset":
        label = "value_set"

    # special handling
    if label == "term":
        c_ent = N(label=label, props={"value": ent.value})
        if ent.origin_name:
            c_ent._add_props({"origin_name": ent.origin_name})
        if ent.origin_id:
            c_ent._add_props({"origin_id": ent.origin_id})
        if ent.origin_version:
            c_ent._add_props({"origin_version": ent.origin_version})
        if ent.origin_definition:
            c_ent._add_props({"origin_defintion": ent.origin_definition})
        if ent.handle:
            c_ent._add_props({"handle": ent.handle})
    elif label == "value_set":
        c_ent = N(label="value_set", props={"handle": ent.handle})
        if ent.url:
            c_ent._add_props({"url": ent.url})
    elif label == "concept":
        c_ent = N(label="concept")
    elif label == "tag":
        c_ent = N(label="tag", props={"key": ent.key, "value": ent.value})

    else:
        model_handle = model.handle if model else None
        c_ent = N(label=label, props={"handle": ent.handle, "model": model_handle})
    # all ents
    if _commit:
        c_ent._add_props({"_commit": _commit})
    elif ent._commit:
        c_ent._add_props({"_commit": ent._commit})
    if ent.nanoid:
        c_ent._add_props({"nanoid": ent.nanoid})
    if ent.desc:
        c_ent._add_props({"desc": ent.desc})
    return c_ent


def _tag_statements(
    ent: Entity,
    c_ent: CypherEntity,
    _commit: str | None = None,
) -> list[Statement]:
    if not ent.tags:
        return []

    c_tags = [_c_entity(t, None, _commit) for t in ent.tags.values()]
    return [
        Statement(
            Match(c_ent),
            Merge(R(Type="has_tag").relate(_plain_var(c_ent), ct)),
            use_params=True,
        )
        for ct in c_tags
    ]


def _prop_statements(
    ent: Entity,
    c_ent: CypherEntity,
    model: Model | None,
    _commit: str | None = None,
) -> list[Statement]:
    stmts = []
    for p in ent.props.values():
        c_prop = _c_entity(p, model, _commit)
        c_prop._add_props({"value_domain": p.value_domain})
        stmts.extend(
            [
                Statement(
                    Merge(c_prop),
                    use_params=True,
                ),
                Statement(
                    Match(c_ent, c_prop),
                    Merge(
                        R(Type="has_property").relate(
                            _plain_var(c_ent),
                            _plain_var(c_prop),
                        ),
                    ),
                    use_params=True,
                ),
            ],
        )
        if p.tags:
            stmts.extend(
                _tag_statements(p, c_prop, _commit),
            )
    return stmts


def _annotate_statements(
    ent: Entity,
    c_ent: CypherEntity,
    _commit: str | None = None,
) -> list[Statement]:
    stmts = []
    if not ent.concept:
        return []
    c_concept = _c_entity(ent.concept, None, _commit)
    stmts = []
    for tm in ent.concept.terms.values():
        c_term = _c_entity(tm, None, _commit)
        stmts.extend(
            [
                Statement(
                    Merge(c_term),
                    use_params=True,
                ),
                Statement(
                    Match(c_ent),
                    Merge(R(Type="has_concept").relate(_plain_var(c_ent), c_concept)),
                    use_params=True,
                ),
                Statement(
                    Match(R(Type="has_concept").relate(c_ent, c_concept), c_term),
                    Merge(
                        R(Type="represents").relate(
                            _plain_var(c_term),
                            _plain_var(c_concept),
                        ),
                    ),
                    use_params=True,
                ),
            ],
        )
    return stmts
