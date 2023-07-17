"""
Script takes two MDF files representing different versions of the same
model and produces a Liquibase Changelog with the necessary changes to
an MDB in Neo4J to update the model from the old version to the new one.
"""

import configparser
import logging
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple, Union

import click
from bento_mdf.diff import diff_models
from bento_mdf.mdf import MDF
from bento_meta.entity import Entity
from bento_meta.objects import Edge, Node, Property, Term
from bento_meta.util.cypher.clauses import (
    Delete,
    DetachDelete,
    Match,
    Merge,
    Remove,
    Set,
    Statement,
)
from bento_meta.util.cypher.entities import G, N, P, R, T, _plain_var
from liquichange.changelog import Changelog, Changeset, CypherChange

logger = logging.getLogger(__name__)

ADD_NODE = "add property graph node"
REMOVE_NODE = "remove property graph node"
ADD_RELATIONSHIP = "add property graph relationship"
REMOVE_RELATIONSHIP = "remove property graph relationship"
ADD_PROPERTY = "add property graph property"
REMOVE_PROPERTY = "remove property graph property"


def split_diff(
    diff: Dict[str, Dict[str, Optional[Union[List, Dict]]]], model_handle: str
) -> List[Tuple[str, Union[Entity, dict]]]:
    """splits model diff into segments that represent one change each"""
    diff_segments = []
    diff_order = [
        REMOVE_NODE,
        ADD_NODE,
        REMOVE_PROPERTY,
        ADD_PROPERTY,
        REMOVE_RELATIONSHIP,
        ADD_RELATIONSHIP,
    ]

    def add_node(entity, diff_segments):
        diff_segments.append((ADD_NODE, entity))

    def remove_node(entity, diff_segments):
        diff_segments.append((REMOVE_NODE, entity))

    def add_relationship(src, rel, dst, diff_segments):
        diff_segments.append((ADD_RELATIONSHIP, {"rel": rel, "src": src, "dst": dst}))

    def remove_relationship(src, rel, dst, diff_segments):
        diff_segments.append(
            (REMOVE_RELATIONSHIP, {"rel": rel, "src": src, "dst": dst})
        )

    def add_property(entity, prop_handle, prop_value, diff_segments):
        diff_segments.append(
            (
                ADD_PROPERTY,
                {
                    "entity": entity,
                    "prop_handle": prop_handle,
                    "prop_value": prop_value,
                },
            )
        )

    def remove_property(entity, prop_handle, prop_value, diff_segments):
        diff_segments.append(
            (
                REMOVE_PROPERTY,
                {
                    "entity": entity,
                    "prop_handle": prop_handle,
                    "prop_value": prop_value,
                },
            )
        )

    node_diff = diff.get("nodes")
    edge_diff = diff.get("edges")
    prop_diff = diff.get("props")

    if node_diff:
        if node_diff.get("a"):
            for node_hdl in node_diff.get("a"):
                remove_node(
                    Node({"handle": node_hdl, "model": model_handle}), diff_segments
                )
        if node_diff.get("b"):
            for node_hdl in node_diff.get("b"):
                add_node(
                    Node({"handle": node_hdl, "model": model_handle}), diff_segments
                )
        for node_hdl, change in node_diff.items():
            if node_hdl in {"a", "b"}:
                continue
            node_props = change["props"]
            node = Node({"handle": node_hdl, "model": model_handle})
            if node_props.get("a"):
                for prop_hdl in node_props.get("a"):
                    remove_relationship(
                        node,
                        "has_property",
                        Property({"handle": prop_hdl, "model": model_handle}),
                        diff_segments,
                    )
            if node_props.get("b"):
                for prop_hdl in node_props.get("b"):
                    add_relationship(
                        node,
                        "has_property",
                        Property({"handle": prop_hdl, "model": model_handle}),
                        diff_segments,
                    )
    if edge_diff:
        if edge_diff.get("a"):
            for edge_hdl, src_hdl, dst_hdl in edge_diff.get("a"):
                edge = Edge(
                    {
                        "handle": edge_hdl,
                        "src": Node({"handle": src_hdl, "model": model_handle}),
                        "dst": Node({"handle": dst_hdl, "model": model_handle}),
                    }
                )
                remove_node(edge, diff_segments)
        if edge_diff.get("b"):
            for edge_hdl, src_hdl, dst_hdl in edge_diff.get("b"):
                edge = Edge(
                    {
                        "handle": edge_hdl,
                        "src": Node({"handle": src_hdl, "model": model_handle}),
                        "dst": Node({"handle": dst_hdl, "model": model_handle}),
                    }
                )
                add_node(edge, diff_segments)
                add_relationship(edge, "has_src", edge.src, diff_segments)
                add_relationship(edge, "has_dst", edge.dst, diff_segments)
        for edge_tup, change_dict in edge_diff.items():
            if edge_tup in {"a", "b"}:
                continue
            edge = Edge(
                {
                    "handle": edge_tup[0],
                    "src": Node({"handle": edge_tup[1], "model": model_handle}),
                    "dst": Node({"handle": edge_tup[2], "model": model_handle}),
                }
            )
            for edge_attr, change in change_dict.items():
                if edge_attr == "props" and change.get("a"):
                    for prop_hdl in change.get("a"):
                        remove_relationship(
                            edge,
                            "has_property",
                            Property({"handle": prop_hdl, "model": model_handle}),
                            diff_segments,
                        )
                if edge_attr == "props" and change.get("b"):
                    for prop_hdl in change.get("b"):
                        add_relationship(
                            edge,
                            "has_property",
                            Property({"handle": prop_hdl, "model": model_handle}),
                            diff_segments,
                        )
                else:
                    if change.get("a"):
                        remove_property(
                            edge,
                            edge_attr,
                            change.get("a"),
                            diff_segments,
                        )
                    if change.get("b"):
                        add_property(
                            edge,
                            edge_attr,
                            change.get("b"),
                            diff_segments,
                        )
    if prop_diff:
        if prop_diff.get("a"):
            for prop_tuple in prop_diff.get("a"):
                # parent_hdls = prop_tuple[:-1]
                prop_hdl = prop_tuple[-1]
                prop = Property({"handle": prop_hdl, "model": model_handle})
                remove_node(prop, diff_segments)
        if prop_diff.get("b"):
            for prop_tuple in prop_diff.get("b"):
                # parent_hdls = prop_tuple[:-1]
                prop_hdl = prop_tuple[-1]
                prop = Property({"handle": prop_hdl, "model": model_handle})
                add_node(prop, diff_segments)
        for prop_tup, change_dict in prop_diff.items():
            if prop_tup in {"a", "b"}:
                continue
            prop = Property({"handle": prop_tup[1]})
            for prop_attr, change in change_dict.items():
                if prop_attr == "value_set" and change.get("a"):
                    value_set = change.get("a")
                    remove_relationship(
                        prop,
                        "has_value_set",
                        value_set,
                        diff_segments,
                    )
                if prop_attr == "value_set" and change.get("b"):
                    value_set = change.get("b")
                    add_node(value_set, diff_segments)
                    add_relationship(
                        prop,
                        "has_value_set",
                        value_set,
                        diff_segments,
                    )
                    for term in value_set.terms:
                        term_ent = Term({"value": term})
                        add_node(term_ent, diff_segments)
                        add_relationship(value_set, "has_term", term_ent, diff_segments)
                else:
                    if change.get("a"):
                        remove_property(
                            prop,
                            prop_attr,
                            change.get("a"),
                            diff_segments,
                        )
                    if change.get("b"):
                        add_property(
                            prop,
                            prop_attr,
                            change.get("b"),
                            diff_segments,
                        )
    return sorted(diff_segments, key=lambda x: diff_order.index(x[0]))


def convert_diff_segment_to_cypher_statement(
    diff_segment: Tuple[str, Union[Entity, dict]]
) -> Statement:
    """converts a diff segment to a changeset"""
    change, item = diff_segment
    if change == ADD_NODE:
        ent = N(label=item.get_label(), props=item.get_attr_dict())
        stmt = Statement(Merge(ent))
    elif change == REMOVE_NODE:
        ent = N(label=item.get_label(), props=item.get_attr_dict())
        if type(item) == Edge:
            src = N(label="node", props=item.src.get_attr_dict())
            dst = N(label="node", props=item.dst.get_attr_dict())
            src_trip = T(ent, R(Type="has_src"), src)
            dst_trip = T(ent, R(Type="has_dst"), dst)
            path = G(src_trip, dst_trip)
            match_clause = Match(path)
        else:
            match_clause = Match(ent)
        stmt = Statement(match_clause, DetachDelete(ent.var))
    elif change == ADD_RELATIONSHIP:
        rel = R(Type=item["rel"])
        src = N(label=item["src"].get_label(), props=item["src"].get_attr_dict())
        dst = N(label=item["dst"].get_label(), props=item["dst"].get_attr_dict())
        plain_trip = T(_plain_var(src), rel, _plain_var(dst))
        stmt = Statement(Match(src, dst), Merge(plain_trip))
    elif change == REMOVE_RELATIONSHIP:
        rel = R(Type=item["rel"])
        src = N(label=item["src"].get_label(), props=item["src"].get_attr_dict())
        dst = N(label=item["dst"].get_label(), props=item["dst"].get_attr_dict())
        trip = T(src, rel, dst)
        stmt = Statement(Match(trip), Delete(_plain_var(rel)))
    elif change == ADD_PROPERTY:
        prop = P(handle=item["prop_handle"], value=item["prop_value"])
        ent = N(label=item["entity"].get_label(), props=item["entity"].get_attr_dict())
        ent._add_props(prop)
        stmt = Statement(Match(ent), Set(ent.props[item["prop_handle"]]))
    elif change == REMOVE_PROPERTY:
        ent = N(label=item["entity"].get_label(), props=item["entity"].get_attr_dict())
        stmt = Statement(Match(ent), Remove(ent, prop=item["prop_handle"]))
    else:
        raise RuntimeError(f"invalid diff segment {diff_segment}")
    return stmt


def get_initial_changeset_id(config_file_path: str) -> int:
    """Gets initial changeset id from changelog config file"""
    config = configparser.ConfigParser()
    config.read(config_file_path)
    try:
        return config.getint(section="changelog", option="changeset_id")
    except (configparser.NoSectionError, configparser.NoOptionError) as error:
        print(error)
        raise


def changeset_id_generator(config_file_path: str) -> Generator[int, None, None]:
    """
    Iterator for changeset_id. Gets latest changeset id from changelog.ini
    and provides up-to-date changeset id as
    """
    i = get_initial_changeset_id(config_file_path)
    while True:
        yield i
        i += 1


def update_config_changeset_id(config_file_path: str, new_changeset_id: int) -> None:
    """Updates changelog config file with new changeset id"""
    config = configparser.ConfigParser()
    config.read(config_file_path)
    config.set(section="changelog", option="changeset_id", value=str(new_changeset_id))
    with open(file=config_file_path, mode="w", encoding="UTF-8") as config_file:
        config.write(fp=config_file)


def convert_diff_to_changelog(
    diff, model_handle: str, author: str, config_file_path: str
) -> Changelog:
    """converts diff beween two models to a changelog"""
    changeset_id = changeset_id_generator(config_file_path=config_file_path)
    changelog = Changelog()
    diff_segments = split_diff(diff, model_handle)

    for segment in diff_segments:
        cypher_stmt = convert_diff_segment_to_cypher_statement(segment)
        changelog.add_changeset(
            Changeset(
                id=str(next(changeset_id)),
                author=author,
                change_type=CypherChange(text=str(cypher_stmt)),
            )
        )

    update_config_changeset_id(
        config_file_path=config_file_path, new_changeset_id=next(changeset_id)
    )

    return changelog


@click.command()
@click.option(
    "--model_handle",
    required=True,
    type=str,
    prompt=True,
    help="CRDC Model Handle (e.g. 'GDC')",
)
@click.option(
    "--old_mdf_files",
    required=True,
    type=click.Path(exists=True),
    prompt=True,
    multiple=True,
    help="Older version of MDF file(s)",
)
@click.option(
    "--new_mdf_files",
    required=True,
    type=click.Path(exists=True),
    prompt=True,
    multiple=True,
    help="Newer version of MDF file(s)",
)
@click.option(
    "--output_file_path",
    required=True,
    type=click.Path(),
    prompt=True,
    help="File path for output changelog",
)
@click.option(
    "--config_file_path",
    required=True,
    type=click.Path(exists=True),
    help="Changeset config file path",
)
@click.option(
    "--author",
    required=True,
    type=str,
    help="author for changeset. default=MDB_ADMIN",
)
@click.option(
    "--_commit",
    required=False,
    type=str,
    help="commit string",
)
def main(
    model_handle: str,
    old_mdf_files: Union[str, List[str]],
    new_mdf_files: Union[str, List[str]],
    output_file_path: str,
    config_file_path: str,
    author: str,
    _commit: Optional[str],
) -> None:
    """
    get liquibase changelog from different versions of mdf files for a model
    """
    mdf_old = MDF(*old_mdf_files, handle=model_handle, _commit=_commit, raiseError=True)
    mdf_new = MDF(*new_mdf_files, handle=model_handle, _commit=_commit, raiseError=True)
    if not mdf_old.model or not mdf_new.model:
        raise RuntimeError("Error getting model from MDF")

    model_old = mdf_old.model
    model_new = mdf_new.model

    diff = diff_models(mdl_a=model_old, mdl_b=model_new)
    changelog = convert_diff_to_changelog(
        diff=diff,
        model_handle=model_handle,
        author=author,
        config_file_path=config_file_path,
    )

    path = Path(output_file_path)
    changelog.save_to_file(file_path=str(path), encoding="UTF-8")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
