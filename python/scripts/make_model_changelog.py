"""
Script takes one MDF file representing a model and produces a Liquibase 
Changelog with the necessary changes to add the model to an MDB
"""
import configparser
import logging
from pathlib import Path
from typing import Dict, Generator, List, Optional, Union

import click
from bento_mdf.mdf import MDF
from bento_meta.entity import Entity
from bento_meta.mdb.mdb import make_nanoid
from bento_meta.model import Model
from bento_meta.objects import Concept, Term, ValueSet
from bento_meta.util.cypher.clauses import Create, Match, Merge, OnCreateSet, Statement
from bento_meta.util.cypher.entities import N, R, T, _plain_var
from liquichange.changelog import Changelog, Changeset, CypherChange

logger = logging.getLogger(__name__)


def get_initial_changeset_id(config_file_path: str) -> int:
    """Gets initial changeset id from changelog config file"""
    config = configparser.ConfigParser()
    config.read(config_file_path)
    try:
        return config.getint(section="changelog", option="changeset_id")
    except (configparser.NoSectionError, configparser.NoOptionError) as error:
        logger.error(f"Reading changeset ID failed: {error}")
        raise


def changeset_id_generator(config_file_path: str) -> Generator[int, None, None]:
    """Generates sequential changeset IDs by reading the latest ID from a config file."""
    i = get_initial_changeset_id(config_file_path)
    while True:
        yield i
        i += 1


def update_config_changeset_id(config_file_path: str, new_changeset_id: int) -> None:
    """Updates changelog config file with new changeset id."""
    config = configparser.ConfigParser()
    config.read(config_file_path)
    config.set(section="changelog", option="changeset_id", value=str(new_changeset_id))
    with open(file=config_file_path, mode="w", encoding="UTF-8") as config_file:
        config.write(fp=config_file)


def escape_quotes_in_attr(entity: Entity) -> None:
    """
    Escapes quotes in entity attributes.

    Quotes in string attributes may or may not already be escaped, so this function
    unescapes all previously escaped ' and " characters and replaces them with
    """
    for key, val in vars(entity).items():
        if (
            val
            and val is not None
            and key != "pvt"
            and isinstance(
                val,
                str,
            )
        ):
            # First unescape any previously escaped quotes
            val = val.replace(r"\'", "'").replace(r"\"", '"')

            # Escape all quotes
            val = val.replace("'", r"\'").replace('"', r"\"")

            # Update the modified value back to the attribute
            setattr(entity, key, val)


def cypherize_entity(entity: Entity) -> N:
    """Represents metamodel Entity object as a property graph Node."""
    return N(label=entity.get_label(), props=entity.get_attr_dict())


def generate_cypher_to_add_entity(
    entity: Entity,
    cypher_stmts: Dict[str, List],
) -> None:
    """Generates cypher statement to create or merge Entity."""
    if entity in cypher_stmts["added_entities"]:
        return
    escape_quotes_in_attr(entity)
    cypher_ent = cypherize_entity(entity)
    if isinstance(entity, (Term, ValueSet)):
        if "_commit" not in cypher_ent.props:
            cypher_stmts["add_ents"].append(Statement(Merge(cypher_ent)))
        # remove _commit prop of Term/VS cypher_ent for Merge
        else:
            commit = cypher_ent.props.pop("_commit")
            cypher_stmts["add_ents"].append(
                Statement(Merge(cypher_ent), OnCreateSet(commit))
            )
    else:
        cypher_stmts["add_ents"].append(Statement(Create(cypher_ent)))
    cypher_stmts["added_entities"].append(entity)


def generate_cypher_to_add_relationship(
    src: Entity,
    rel: str,
    dst: Entity,
    cypher_stmts: Dict[str, List],
) -> None:
    """Generates cypher statement to create relationship from src to dst entity"""
    cypher_src = cypherize_entity(src)
    cypher_dst = cypherize_entity(dst)
    # remove _commit attr from Term and VS ents
    for cypher_ent in (cypher_src, cypher_dst):
        if isinstance(cypher_ent, (Term, ValueSet)) and "_commit" in cypher_ent.props:
            cypher_ent.props.pop("_commit")
    cypher_stmts["add_rels"].append(
        Statement(
            Match(cypher_src, cypher_dst),
            Merge(T(_plain_var(cypher_src), R(Type=rel), _plain_var(cypher_dst))),
        )
    )


def process_tags(entity: Entity, cypher_stmts) -> None:
    """Generates cypher statements to create/merge an entity's tag attributes."""
    if not entity.tags:
        return
    for tag in entity.tags.values():
        tag.nanoid = make_nanoid()
        generate_cypher_to_add_entity(tag, cypher_stmts)
        generate_cypher_to_add_relationship(entity, "has_tag", tag, cypher_stmts)


def process_origin(entity: Entity, cypher_stmts) -> None:
    """Generates cypher statements to create/merge an entity's origin attribute."""
    if not entity.origin:
        return
    generate_cypher_to_add_entity(entity.origin, cypher_stmts)
    generate_cypher_to_add_relationship(
        entity, "has_origin", entity.origin, cypher_stmts
    )
    process_tags(entity.origin, cypher_stmts)


def process_terms(entity: Entity, cypher_stmts) -> None:
    """Generates cypher statements to create/merge an entity's term attributes."""
    if not entity.terms:
        return
    for term in entity.terms.values():
        generate_cypher_to_add_entity(term, cypher_stmts)
        if isinstance(entity, Concept):
            generate_cypher_to_add_relationship(
                term, "represents", entity, cypher_stmts
            )
        else:
            generate_cypher_to_add_relationship(entity, "has_term", term, cypher_stmts)
        process_tags(term, cypher_stmts)
        process_origin(term, cypher_stmts)


def process_concept(entity: Entity, cypher_stmts) -> None:
    """Generates cypher statements to create/merge an entity's concept attribute."""
    if not entity.concept:
        return
    generate_cypher_to_add_entity(entity.concept, cypher_stmts)
    generate_cypher_to_add_relationship(
        entity, "has_concept", entity.concept, cypher_stmts
    )
    process_tags(entity.concept, cypher_stmts)
    process_terms(entity.concept, cypher_stmts)


def process_value_set(entity: Entity, cypher_stmts) -> None:
    """Generates cypher statements to create/merge an entity's value_set attribute."""
    if not entity.value_set:
        return
    generate_cypher_to_add_entity(entity.value_set, cypher_stmts)
    generate_cypher_to_add_relationship(
        entity, "has_value_set", entity.value_set, cypher_stmts
    )
    process_tags(entity.value_set, cypher_stmts)
    process_origin(entity.value_set, cypher_stmts)
    process_terms(entity.value_set, cypher_stmts)


def process_props(entity: Entity, cypher_stmts) -> None:
    """Generates cypher statements to create/merge an entity's props attribute."""
    if not entity.props:
        return
    for prop in entity.props.values():
        generate_cypher_to_add_entity(prop, cypher_stmts)
        generate_cypher_to_add_relationship(entity, "has_property", prop, cypher_stmts)
        process_tags(prop, cypher_stmts)
        process_concept(prop, cypher_stmts)
        process_value_set(prop, cypher_stmts)


def process_model_nodes(model: Model, cypher_stmts) -> None:
    """Generates cypher statements to create/merge an model's nodes."""
    for node in model.nodes.values():
        generate_cypher_to_add_entity(node, cypher_stmts)
        process_tags(node, cypher_stmts)
        process_concept(node, cypher_stmts)
        process_props(node, cypher_stmts)


def process_model_edges(model: Model, cypher_stmts) -> None:
    """Generates cypher statements to create/merge an model's edges."""
    for edge in model.edges.values():
        generate_cypher_to_add_entity(edge, cypher_stmts)
        generate_cypher_to_add_relationship(edge, "has_src", edge.src, cypher_stmts)
        generate_cypher_to_add_relationship(edge, "has_dst", edge.dst, cypher_stmts)
        process_tags(edge, cypher_stmts)
        process_concept(edge, cypher_stmts)
        process_props(edge, cypher_stmts)


def convert_model_to_changelog(
    model: Model, author: str, config_file_path: str
) -> Changelog:
    """
    Converts a bento meta model to a Liquibase Changelog.

    Parameters:
    model (Model): The bento meta model to convert
    author (str): The author for the changesets
    config_file_path (str): The path to the changeset config file

    Returns:
    Changelog: The generated Liquibase Changelog

    Functionality:
    - Generates Cypher statements to add entities and relationships from the model
    - Appends Changesets with the Cypher statements to a Changelog
    - Updates the changeset ID in the config file after generating each Changeset
    - Returns the completed Changelog
    """

    cypher_stmts: Dict[str, List] = {
        "add_ents": [],
        "add_rels": [],
        # cypher_stmts["added_entities"] used to prevent duplicate props/terms
        # from being created when they are shared by >1 node/prop
        "added_entities": [],
    }

    # track created props and terms to prevent duplication

    process_model_nodes(model, cypher_stmts)
    process_model_edges(model, cypher_stmts)

    changeset_id = changeset_id_generator(config_file_path=config_file_path)
    changelog = Changelog()

    for stmt in cypher_stmts["add_ents"] + cypher_stmts["add_rels"]:
        changelog.add_changeset(
            Changeset(
                id=str(next(changeset_id)),
                author=author,
                change_type=CypherChange(text=str(stmt)),
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
    "--mdf_files",
    required=True,
    type=click.Path(exists=True),
    prompt=True,
    multiple=True,
    help="MDF file(s)",
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
    help="author for changeset",
)
@click.option(
    "--_commit",
    required=False,
    type=str,
    help="commit string",
)
def main(
    model_handle: str,
    mdf_files: Union[str, List[str]],
    output_file_path: str,
    config_file_path: str,
    author: str,
    _commit: Optional[str],
) -> None:
    """get liquibase changelog from mdf files for a model"""
    logger.info("Script started")

    mdf = MDF(*mdf_files, handle=model_handle, _commit=_commit, raiseError=True)
    if not mdf.model:
        raise RuntimeError("Error getting model from MDF")
    logger.info("Model MDF loaded successfully")

    changelog = convert_model_to_changelog(
        model=mdf.model, author=author, config_file_path=config_file_path
    )
    logger.info("Changelog converted from MDF successfully")

    changelog.save_to_file(str(Path(output_file_path)), encoding="UTF-8")
    logger.info("Changelog saved at: {output_file_path}")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
