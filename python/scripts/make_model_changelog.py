"""
Script takes one MDF file representing a model and produces a Liquibase 
Changelog with the necessary changes to add the model to an MDB
"""
import configparser
from pathlib import Path
from typing import Dict, Generator, List, Optional, Union

import click
from bento_mdf.mdf import MDF
from bento_meta.entity import Entity
from bento_meta.model import Model
from bento_meta.objects import Concept
from bento_meta.util.cypher.clauses import Match, Merge, Statement
from bento_meta.util.cypher.entities import N, R, T, _plain_var
from liquichange.changelog import Changelog, Changeset, CypherChange


def convert_model_to_changelog(
    model: Model, author: str, config_file_path: str
) -> Changelog:
    """converts bento meta model to a changelog"""

    cypher_stmts: Dict[str, List[Statement]] = {
        "merge_ents": [],
        "merge_rels": [],
    }

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

    def update_config_changeset_id(
        config_file_path: str, new_changeset_id: int
    ) -> None:
        """Updates changelog config file with new changeset id"""
        config = configparser.ConfigParser()
        config.read(config_file_path)
        config.set(
            section="changelog", option="changeset_id", value=str(new_changeset_id)
        )
        with open(file=config_file_path, mode="w", encoding="UTF-8") as config_file:
            config.write(fp=config_file)

    def escape_quotes_in_attr(entity: Entity) -> None:
        for attr_name in ["desc", "origin_definition", "value"]:
            if hasattr(entity, attr_name) and getattr(entity, attr_name) is not None:
                setattr(
                    entity,
                    attr_name,
                    # removing 's for now. converting to \\' & '' didn't work
                    getattr(entity, attr_name).replace("'", "").replace('"', ""),
                )

    def cypherize_entity(entity: Entity) -> N:
        """returns cypher utils version of bento meta entity"""
        return N(label=entity.get_label(), props=entity.get_attr_dict())

    def merge_ent(
        entity: Entity,
        cypher_stmts: Dict[str, List[Statement]],
    ) -> None:
        """generate cypher statement to merge entity (property graph node)"""
        escape_quotes_in_attr(entity)
        cypher_ent = cypherize_entity(entity)
        cypher_stmts["merge_ents"].append(Statement(Merge(cypher_ent)))

    def merge_rel(
        src: Entity,
        rel: str,
        dst: Entity,
        cypher_stmts: Dict[str, List[Statement]],
    ) -> None:
        """generate cypher statement to merge relationship from src to dst entity"""
        cypher_src = cypherize_entity(src)
        cypher_dst = cypherize_entity(dst)
        cypher_stmts["merge_rels"].append(
            Statement(
                Match(cypher_src, cypher_dst),
                Merge(T(_plain_var(cypher_src), R(Type=rel), _plain_var(cypher_dst))),
            )
        )

    def process_tags(entity: Entity, cypher_stmts):
        if not entity.tags:
            return
        for tag in entity.tags.values():
            merge_ent(tag, cypher_stmts)
            merge_rel(entity, "has_tag", tag, cypher_stmts)

    def process_origin(entity: Entity, cypher_stmts):
        if not entity.origin:
            return
        merge_ent(entity.origin, cypher_stmts)
        merge_rel(entity, "has_origin", entity.origin, cypher_stmts)
        process_tags(entity.origin, cypher_stmts)

    def process_terms(entity: Entity, cypher_stmts):
        if not entity.terms:
            return
        for term in entity.terms.values():
            merge_ent(term, cypher_stmts)
            if isinstance(entity, Concept):
                merge_rel(term, "represents", entity, cypher_stmts)
            else:
                merge_rel(entity, "has_term", term, cypher_stmts)
            process_tags(term, cypher_stmts)
            process_origin(term, cypher_stmts)

    def process_concept(entity: Entity, cypher_stmts):
        if not entity.concept:
            return
        merge_ent(entity.concept, cypher_stmts)
        merge_rel(entity, "has_concept", entity.concept, cypher_stmts)
        process_tags(entity.concept, cypher_stmts)
        process_terms(entity.concept, cypher_stmts)

    def process_value_set(entity: Entity, cypher_stmts):
        if not entity.value_set:
            return
        merge_ent(entity.value_set, cypher_stmts)
        merge_rel(entity, "has_value_set", entity.value_set, cypher_stmts)
        process_tags(entity.value_set, cypher_stmts)
        process_origin(entity.value_set, cypher_stmts)
        process_terms(entity.value_set, cypher_stmts)

    def process_props(entity: Entity, cypher_stmts):
        if not entity.props:
            return
        for prop in entity.props.values():
            merge_ent(prop, cypher_stmts)
            merge_rel(entity, "has_property", prop, cypher_stmts)
            process_tags(prop, cypher_stmts)
            process_concept(prop, cypher_stmts)
            process_value_set(prop, cypher_stmts)

    def process_model_nodes(model: Model, cypher_stmts):
        for node in model.nodes.values():
            merge_ent(node, cypher_stmts)
            process_tags(node, cypher_stmts)
            process_concept(node, cypher_stmts)
            process_props(node, cypher_stmts)

    def process_model_edges(model: Model, cypher_stmts):
        for edge in model.edges.values():
            merge_ent(edge, cypher_stmts)
            merge_rel(edge, "has_src", edge.src, cypher_stmts)
            merge_rel(edge, "has_dst", edge.dst, cypher_stmts)
            process_tags(edge, cypher_stmts)
            process_concept(edge, cypher_stmts)
            process_props(edge, cypher_stmts)

    process_model_nodes(model, cypher_stmts)
    process_model_edges(model, cypher_stmts)

    changeset_id = changeset_id_generator(config_file_path=config_file_path)
    changelog = Changelog()

    for stmt in cypher_stmts["merge_ents"] + cypher_stmts["merge_rels"]:
        changelog.subelements.append(
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
    mdf = MDF(*mdf_files, handle=model_handle, _commit=_commit, raiseError=True)
    if not mdf.model:
        raise RuntimeError("Error getting model from MDF")

    changelog = convert_model_to_changelog(
        model=mdf.model, author=author, config_file_path=config_file_path
    )
    changelog.save_to_file(str(Path(output_file_path)), encoding="UTF-8")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
