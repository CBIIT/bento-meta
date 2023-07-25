"""converts mapping MDF to changelog"""
import configparser
from ast import literal_eval
from pathlib import Path
from typing import Dict, Generator, List, Optional, Union

import click
import yaml
from bento_meta.util.cypher.clauses import (
    Case,
    Create,
    ForEach,
    Match,
    Merge,
    OptionalMatch,
    Statement,
    When,
    With,
)
from bento_meta.util.cypher.entities import G, N, R, T, _anon, _plain_var
from liquichange.changelog import Changelog, Changeset, CypherChange


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


def load_yaml(
    file: str,
) -> Dict[
    str,
    Union[
        str,
        List[str],
        Dict[
            str,
            Dict[
                str,
                Dict[str, Dict[str, List[Dict[str, Dict[str, Union[str, bool]]]]]],
            ],
        ],
    ],
]:
    """loads mapping Dict from yaml"""
    with open(file, "r", encoding="UTF8") as stream:
        try:
            data = yaml.safe_load(stream)
            return data
        except yaml.YAMLError as exc:
            print(exc)
            raise exc


def get_mapping_source(mapping_dict: Dict) -> str:
    """returns source of cross-model mappings"""
    return mapping_dict.get("Source", "")


def get_target_models(mapping_dict: Dict) -> Dict[str, str]:
    """returns target models"""
    return mapping_dict.get("Models", dict())


def get_parents_as_list(parent_str: str) -> List[str]:
    """Returns parent nodes as a list."""
    if not parent_str or not isinstance(parent_str, str):
        raise ValueError("Input must be a non-empty string.")
    if parent_str.startswith("[") and parent_str.endswith("]"):
        return literal_eval(parent_str)
    if "." in parent_str:
        return parent_str.split(".")
    return [parent_str]


def generate_mapping_cypher(
    src_ent: N,
    dst_ent: N,
    src_parent: N,
    dst_parent: N,
    parent_child_rel: R,
    mapping_source: str,
    _commit: Optional[str] = None,
) -> Statement:
    """
    Matches existing src_ent & dst_ent with given parents/ancestors and
    generates cypher query to link synonymous entities via a Concept node.

    Adds Tag node {mapping_source: src_model} to generated concept.

    _commit will be added to newly created nodes
    """
    src_triple = T(src_parent, _anon(parent_child_rel), src_ent)
    dst_triple = T(dst_parent, _anon(parent_child_rel), dst_ent)
    src_concept = N(label="concept")
    dst_concept = N(label="concept")
    src_concept_path = G(
        T(_plain_var(src_ent), R(Type="has_concept"), src_concept),
        T(
            _plain_var(src_concept),
            R(Type="has_tag"),
            N(label="tag", props={"key": "mapping_source", "value": mapping_source}),
        ),
    )
    dst_concept_path = G(
        T(_plain_var(dst_ent), R(Type="has_concept"), dst_concept),
        T(
            _plain_var(dst_concept),
            R(Type="has_tag"),
            N(label="tag", props={"key": "mapping_source", "value": mapping_source}),
        ),
    )
    new_concept = N(label="concept", props={"_commit": _commit})
    new_tag = N(
        label="tag",
        props={"key": "mapping_source", "value": mapping_source, "_commit": _commit},
    )
    return Statement(
        # find src & dst entities using parent triples
        Match(src_triple, dst_triple),
        # check if src or dst ents have a concept tagged by the mapping src
        OptionalMatch(src_concept_path),
        OptionalMatch(dst_concept_path),
        With(src_ent.var, dst_ent.var, src_concept.var, dst_concept.var),
        # src ent has existing concept tagged by mapping src, link dst ent to it
        ForEach(),
        f"(_ IN {Case()}{When(f'{src_concept.var} IS NOT NULL', f'{dst_concept.var} IS NULL')} ",
        "THEN [1] ELSE [] END |",
        Merge(T(_plain_var(dst_ent), R(Type="has_concept"), _plain_var(src_concept))),
        ")",
        # dst ent has existing concept tagged by mapping src, link src ent to it
        ForEach(),
        f"(_ IN {Case()}{When(f'{src_concept.var} IS NULL', f'{dst_concept.var} IS NOT NULL')} ",
        "THEN [1] ELSE [] END |",
        Merge(T(_plain_var(src_ent), R(Type="has_concept"), _plain_var(dst_concept))),
        ")",
        # neither ent has a concept, create a new one, tag it, link ents to it
        ForEach(),
        f"(_ IN {Case()}{When(f'{src_concept.var} IS NULL', f'{dst_concept.var} IS NULL')} ",
        "THEN [1] ELSE [] END |",
        Create(T(new_concept, R(Type="has_tag"), new_tag)),
        Create(
            T(
                _plain_var(src_ent),
                R(Type="has_concept", props={"_commit": _commit}),
                _plain_var(new_concept),
            )
        ),
        Create(
            T(
                _plain_var(dst_ent),
                R(Type="has_concept", props={"_commit": _commit}),
                _plain_var(new_concept),
            )
        ),
        ")",
    )


def process_props(mapping_dict: Dict, _commit: Optional[str] = None) -> List[Statement]:
    """processes mappings between model Property entities"""
    cypher_stmts = []
    src_model = get_mapping_source(mapping_dict)
    prop_map = mapping_dict.get("Props")
    if not prop_map:
        raise RuntimeError("error loading 'Props'")
    for src_parent, src_prop_dict in prop_map.items():
        for src_prop, dst_model_dict in src_prop_dict.items():
            for dst_model, dst_prop_list in dst_model_dict.items():
                for dst_prop_dict in dst_prop_list:
                    dst_prop = next(iter(dst_prop_dict))
                    dst_parents = dst_prop_dict.get(dst_prop).get("Parents", "CONST")
                    cypher_stmts.append(
                        generate_mapping_cypher(
                            src_ent=N(
                                label="property",
                                props={"handle": src_prop, "model": src_model},
                            ),
                            dst_ent=N(
                                label="property",
                                props={"handle": dst_prop, "model": dst_model},
                            ),
                            src_parent=N(
                                props={
                                    "handle": get_parents_as_list(src_parent)[-1],
                                    "model": src_model,
                                }
                            ),
                            dst_parent=N(
                                props={
                                    "handle": get_parents_as_list(dst_parents)[-1],
                                    "model": dst_model,
                                }
                            ),
                            parent_child_rel=R(Type="has_property"),
                            mapping_source=src_model,
                            _commit=_commit,
                        )
                    )
    return cypher_stmts


def convert_mappings_to_changelog(
    mapping_mdf: str, config_file_path: str, author: str, _commit: Optional[str] = None
) -> Changelog:
    """converts mapping MDF to liquibase changelog"""
    changeset_id = changeset_id_generator(config_file_path=config_file_path)
    changelog = Changelog()

    mapping_dict = load_yaml(mapping_mdf)
    cypher_stmts = process_props(mapping_dict, _commit)
    for stmt in cypher_stmts:
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
    "--mapping_mdf",
    required=True,
    type=click.Path(exists=True),
    prompt=True,
    help="Mapping MDF File to be converted to changelog",
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
    mapping_mdf: str,
    output_file_path: str,
    config_file_path: str,
    author: str,
    _commit: str,
) -> None:
    """main function to convert mapping mdf file to changelog"""
    changelog = convert_mappings_to_changelog(
        mapping_mdf=mapping_mdf,
        config_file_path=config_file_path,
        author=author,
        _commit=_commit,
    )
    changelog.save_to_file(str(Path(output_file_path)), encoding="UTF-8")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
