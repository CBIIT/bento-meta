"""Command line interface for python script to format CDA mapping excel file"""

import csv
from ast import literal_eval
from pathlib import Path

import click
from bento_meta.objects import Edge, Node, Property, Term
from mdb_tools import NelsonMDB, get_entity_type


@click.command()
@click.option(
    "--csv_filepath",
    required=True,
    type=str,
    prompt=True,
    help=(
        "file path to CSV with entities to be linked. Each line should contain data "
        "needed to uniquely identify two synonymous entities.")
    )
@click.option(
    "--mdb_uri",
    required=True,
    type=str,
    prompt=True,
    help="metamodel database URI")
@click.option(
    "--mdb_user",
    required=True,
    type=str,
    prompt=True,
    help="metamodel database username")
@click.option(
    "--mdb_pass",
    required=True,
    type=str,
    prompt=True,
    help="metamodel database password")
@click.option(
    "--entity_type",
    required=True,
    type=click.Choice(["node", "property", "relationship", "term"], case_sensitive=False),
    prompt=True,
    help="type of entity to be linked (node, property, relationship, term)")
@click.option(
    "--add_missing_ent",
    default=False,
    type=bool,
    prompt=True,
    help="if set to true, will add entities not already in the database.")
def main(
    csv_filepath: str,
    mdb_uri,
    mdb_user,
    mdb_pass,
    entity_type: str,
    add_missing_ent: bool = False
    ) -> None:
    """
    Given CSV file of synonymous entities, links them in MDB via Concept.

    csv_filepath: file path to CSV with entities to be linked. Each line should contain data
        needed to uniquely identify two synonymous entities.
    mdbn: metamodel database object
    entity_type: type of entity to be linked (node, property, relationship, term)
    add_missing_ent: if set to true, will add entities not found in the database.
    """
    mdbn = NelsonMDB(uri=mdb_uri, user=mdb_user, password=mdb_pass)
    csv_path = Path(csv_filepath)
    with open(csv_path, encoding="UTF-8") as csvfile:
        syn_reader = csv.DictReader(csvfile)
        for row in syn_reader:
            ent_type = entity_type.lower()
            # get entity models and handles (used by all ent types)
            ent_1_model = row["ent_1_model"]
            ent_1_handle = row["ent_1_handle"]
            ent_2_model = row["ent_2_model"]
            ent_2_handle = row["ent_2_handle"]
            ent_1_extra_handles = literal_eval(row["ent_1_extra_handles"])
            ent_2_extra_handles = literal_eval(row["ent_2_extra_handles"])
            row_extra_ents = [] # collects any extra entities for creation in mdb later
            if ent_type in ["relationship", "edge"]:
                if len(ent_1_extra_handles) != 2 or len(ent_2_extra_handles) != 2:
                    raise RuntimeError(
                        "Relationship entities must have two extra handles "
                        "for unique id. Format: [src_handle, dst_handle]")
                # get extra handles from row
                ent_1_src_handle = ent_1_extra_handles[0]
                ent_1_dst_handle = ent_1_extra_handles[1]
                ent_2_src_handle = ent_2_extra_handles[0]
                ent_2_dst_handle = ent_2_extra_handles[1]
                # instantiate bento-meta entities
                ent_1 = Edge({"handle": ent_1_handle, "model": ent_1_model})
                ent_2 = Edge({"handle": ent_2_handle, "model": ent_2_model})
                ent_1_src = Node({"handle": ent_1_src_handle, "model": ent_1_model})
                ent_1_dst = Node({"handle": ent_1_dst_handle, "model": ent_1_model})
                ent_2_src = Node({"handle": ent_2_src_handle, "model": ent_2_model})
                ent_2_dst = Node({"handle": ent_2_dst_handle, "model": ent_2_model})
                # add nanoid to entities (needed to id them for creation and linking)
                ent_1.nanoid = mdbn.get_or_make_nano(ent_1, ent_1_src_handle, ent_1_dst_handle)
                ent_2.nanoid = mdbn.get_or_make_nano(ent_2, ent_2_src_handle, ent_2_dst_handle)
                ent_1_src.nanoid = mdbn.get_or_make_nano(ent_1_src)
                ent_1_dst.nanoid = mdbn.get_or_make_nano(ent_1_dst)
                ent_2_src.nanoid = mdbn.get_or_make_nano(ent_2_src)
                ent_2_dst.nanoid = mdbn.get_or_make_nano(ent_2_dst)
                row_extra_ents.extend([ent_1_src, ent_1_dst, ent_2_src, ent_2_dst])
            elif ent_type == "property":
                if len(ent_1_extra_handles) != 1 or len(ent_2_extra_handles) != 1:
                    raise RuntimeError(
                        "Property entities must have one extra handle "
                        "for unique id. Format: [node_handle]")
                # get extra handles from row
                ent_1_node_handle = ent_1_extra_handles[0]
                ent_2_node_handle = ent_2_extra_handles[0]
                # instantiate bento-meta entities
                ent_1 = Property({"handle": ent_1_handle, "model": ent_1_model})
                ent_2 = Property({"handle": ent_2_handle, "model": ent_2_model})
                ent_1_node = Node({"handle": ent_1_node_handle, "model": ent_1_model})
                ent_2_node = Node({"handle": ent_2_node_handle, "model": ent_2_model})
                # add nanoid to entities (needed to id them for creation and linking)
                ent_1.nanoid = mdbn.get_or_make_nano(ent_1, ent_1_node_handle)
                ent_2.nanoid = mdbn.get_or_make_nano(ent_2, ent_2_node_handle)
                ent_1_node.nanoid = mdbn.get_or_make_nano(ent_1_node)
                ent_2_node.nanoid = mdbn.get_or_make_nano(ent_2_node)
                row_extra_ents.extend([ent_1_node, ent_2_node])
            elif ent_type == "node":
                # instantiate bento-meta entities
                ent_1 = Node({"handle": ent_1_handle, "model": ent_1_model})
                ent_2 = Node({"handle": ent_2_handle, "model": ent_2_model})
                # add nanoid to entities (needed to id them for creation and linking)
                ent_1.nanoid = mdbn.get_or_make_nano(ent_1)
                ent_2.nanoid = mdbn.get_or_make_nano(ent_2)
            elif ent_type == "term":
                # instantiate bento-meta entities
                ent_1 = Term({"value": ent_1_handle, "origin_name": ent_1_model})
                ent_2 = Term({"value": ent_2_handle, "origin_name": ent_2_model})
                # add nanoid to entities (needed to id them for creation and linking)
                ent_1.nanoid = mdbn.get_or_make_nano(ent_1)
                ent_2.nanoid = mdbn.get_or_make_nano(ent_2)
            else:
                raise RuntimeError(
                    "entity_type must be node, property, relationship, or term")

            row_ents = [ent_1, ent_2]
            row_ents.extend(row_extra_ents)

            if add_missing_ent:
                # add entities if not in MDB
                for ent in row_ents:
                    ent_count = mdbn.get_entity_count(ent)[0]
                    if not ent_count:
                        mdbn.create_entity(ent)
                    else:
                        print(
                            f"{get_entity_type(ent).capitalize()} entity with properties: "
                            f"{mdbn.get_entity_attrs(ent)} already exists in the database.")
                # add relationships between relevant entities if not in MDB
                if ent_type in ["relationship", "edge"]:
                    mdbn.create_relationship(ent_1, ent_1_src, "has_src") # type: ignore
                    mdbn.create_relationship(ent_1, ent_1_dst, "has_dst") # type: ignore
                    mdbn.create_relationship(ent_2, ent_2_src, "has_src") # type: ignore
                    mdbn.create_relationship(ent_2, ent_2_dst, "has_dst") # type: ignore
                elif ent_type == "property":
                    mdbn.create_relationship(ent_1_node, ent_1, "has_property") # type: ignore
                    mdbn.create_relationship(ent_2_node, ent_2, "has_property") # type: ignore

            mdbn.link_synonyms(ent_1, ent_2, add_missing_ent=add_missing_ent)

if __name__ == "__main__":
    main() # pylint: disable=no-value-for-parameter
