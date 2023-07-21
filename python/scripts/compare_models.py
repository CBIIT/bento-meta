"""Command line interface for python script to compare MDB models using fuzzy & nlp matching"""

from pathlib import Path
from typing import List, Optional, Tuple

import click
import pandas as pd
import spacy
from bento_meta.mdb import SearchableMDB
from bento_meta.mdb.mdb_tools import ToolsMDB
from bento_meta.objects import Property


def _get_prop_fuzzy_matches(smdb, qstring) -> Optional[List[dict]]:
    """
    returns list of fuzzy matching property nodes

    :param smdb
    :param qstring
    """
    items = smdb.search_entity_handles(qstring)
    fuzzy_matches = []
    if not items:
        return fuzzy_matches
    for itm in items["properties"]:
        fuzzy_matches.append(
            {
                "nanoid": itm["ent"]["nanoid"],
                "model": itm["ent"]["model"],
                "handle": itm["ent"]["handle"],
            }
        )
    return fuzzy_matches


def _get_fuzzy_synonyms(mdb: ToolsMDB, fuzzy_match_list) -> list:
    """convert results of get_property_synonyms_all() to list of dicts"""
    fuzzy_synonym_list = []
    for fuzzy_match in fuzzy_match_list:
        fuzzy_synonyms = mdb.get_property_synonyms_all(
            Property({"nanoid": fuzzy_match["nanoid"]})
        )
        if not fuzzy_synonyms:
            continue
        for synonym in fuzzy_synonyms:
            fuzzy_synonym_list.append(
                {
                    "nanoid": synonym.nanoid,
                    "model": synonym.model,
                    "handle": synonym.handle,
                }
            )
    return fuzzy_synonym_list


def _join_model_fuzzy_matches(base_prop_dict, comp_model) -> str:
    """takes a comp model & row of base_node_prop and returns string with joined fuzzy matches"""
    match_list = []
    for fuzzy_synonym in base_prop_dict["fuzzy_matches"]:
        if fuzzy_synonym["model"] == comp_model:
            for node_handle in fuzzy_synonym["node_handles"]:
                match_list.append(f"{node_handle}.{fuzzy_synonym['handle']}")
    if not match_list:
        return ""
    if len(match_list) == 1:
        return match_list[0]
    return "|".join(match_list)


def _join_model_nlp_matches(base_prop_dict, comp_model) -> str:
    """takes a comp model & row of base_node_prop and returns string with joined nlp matches"""
    match_list = []
    for nlp_synonym in base_prop_dict["nlp_matches"]:
        if nlp_synonym["model"] == comp_model:
            round_sim = round(nlp_synonym["similarity"], 2)
            match_list.append(
                f"{nlp_synonym['node_handle']}.{nlp_synonym['handle']} ({round_sim})"
            )
    if not match_list:
        return ""
    elif len(match_list) == 1:
        return match_list[0]
    return "|".join(match_list)


@click.command()
@click.option(
    "--mdb_uri", required=True, type=str, prompt=True, help="metamodel database URI"
)
@click.option(
    "--mdb_user",
    required=True,
    type=str,
    prompt=True,
    help="metamodel database username",
)
@click.option(
    "--mdb_pass",
    required=True,
    type=str,
    prompt=True,
    help="metamodel database password",
)
@click.option(
    "--base_model",
    required=True,
    type=str,
    prompt=True,
    help="model to compare to other models in MDB",
)
@click.option(
    "--comp_model",
    required=True,
    type=str,
    prompt=True,
    multiple=True,
    default=["DST", "PDC", "GDC", "HTAN", "ICDC", "CCDI", "CDA", "CDS"],
    help="model names to compare to base model nodes/props",
)
@click.option(
    "--output_filepath",
    required=True,
    type=str,
    prompt=True,
    help="path to .csv file for output",
)
@click.option(
    "--sim_threshold",
    required=True,
    default=0.8,
    type=float,
    prompt=False,
    help="similarity threshold synonyms must meet to be considered. default = 0.8",
)
@click.option(
    "--num_nlp",
    required=True,
    default=3,
    type=int,
    prompt=False,
    help="similarity threshold synonyms must meet to be considered. default = 0.8",
)
def main(
    mdb_uri: str,
    mdb_user: str,
    mdb_pass: str,
    base_model: str,
    comp_model: Tuple[str],
    output_filepath: str,
    sim_threshold: float = 0.8,
    num_nlp: int = 3,
) -> None:
    """
    Compare base_model's node/property handles to those of comp_model(s)
    using fuzzy matching, existing mappings, and NLP.

    Args:
        :param str mdb_uri: MDB instance bolt uri
        :param str mdb_user: MDB instance username
        :param str mdb_pass: MDB instance password
        :param str base_model: model name (e.g., GDC)
        :param str comp_models: model names to compare to base model nodes/props
        :param str output_filepath: file path for output CSV
        :param float sim_threshold: threshold for similarty score results
        :param float num_nlp: number of nlp matches to return
            (nlp matches sorted by descending similarity score)

    Output:
        .csv file with base node/property handles and any matching node/property handles
    """
    filepath = Path(output_filepath)
    smdb = SearchableMDB(uri=mdb_uri, user=mdb_user, password=mdb_pass)
    tmdb = ToolsMDB(uri=mdb_uri, user=mdb_user, password=mdb_pass)

    # load spaCy NER model
    nlp = spacy.load("en_ner_bionlp13cg_md")

    # remove base model from comp_models if included for some reason
    comp_models = list(comp_model)
    if base_model in comp_models:
        comp_models.remove(base_model)

    base_nodes_props = []

    # gather all node and property handles for given base model
    for node in smdb.get_nodes_and_props_by_model(base_model):
        for prop in node["props"]:
            base_nodes_props.append(
                {
                    "model": base_model,
                    "node_handle": node["handle"],
                    "handle": prop["handle"],
                    "nanoid": prop["nanoid"],
                    "mapped_synonyms": [],
                    "fuzzy_matches": [],
                    "nlp_matches": [],
                }
            )

    comp_nodes_props = []

    # gather all node and property handles for given base model
    for model in comp_models:
        for node in smdb.get_nodes_and_props_by_model(model):
            for prop in node["props"]:
                comp_nodes_props.append(
                    {
                        "model": model,
                        "node_handle": node["handle"],
                        "handle": prop["handle"],
                        "nanoid": prop["nanoid"],
                    }
                )

    # keys=comp property nanoids; values=lists of corresponding node handles
    # used to get node handle for fuzzy props
    comp_nano_node_dict = {}
    for d in comp_nodes_props:
        if d["nanoid"] in comp_nano_node_dict:
            comp_nano_node_dict[d["nanoid"]].append(d["node_handle"])
            continue
        comp_nano_node_dict[d["nanoid"]] = [d["node_handle"]]

    for base_prop in base_nodes_props:
        # replace characters in property handle for fuzzy and nlp matching
        base_hdl_wc = base_prop["handle"].replace("_", "*")
        base_hdl_nlp = nlp(base_prop["handle"].replace("_", " ").lower())

        # get any existing synonyms of property
        base_synonyms = tmdb.get_property_synonyms_all(
            Property({"nanoid": base_prop["nanoid"]})
        )
        if base_synonyms:
            for synonym in base_synonyms:
                base_prop["mapped_synonyms"].append(
                    {
                        "nanoid": synonym.nanoid,
                        "model": synonym.model,
                        "handle": synonym.handle,
                    }
                )

        # fuzzy search on index for property handle matches
        fuzzy_match_list = _get_prop_fuzzy_matches(smdb, base_hdl_wc)
        if fuzzy_match_list:
            # add fuzzy match to fuzzy matches of base property
            for fuzzy_match in fuzzy_match_list:
                if (
                    fuzzy_match["model"] == base_model
                    or fuzzy_match in base_prop["fuzzy_matches"]
                ):
                    continue
                base_prop["fuzzy_matches"].append(fuzzy_match)

            # get list of mapped synonyms to fuzzy matches
            fuzzy_synonym_list = _get_fuzzy_synonyms(tmdb, fuzzy_match_list)

            # add fuzzy match synonyms to fuzzy matches of base property
            for fuzzy_synonym in fuzzy_synonym_list:
                if (
                    fuzzy_synonym["model"] == base_model
                    or fuzzy_synonym in base_prop["fuzzy_matches"]
                ):
                    continue
                base_prop["fuzzy_matches"].append(fuzzy_synonym)

        # add node handles to fuzzy matches
        for f_match in base_prop["fuzzy_matches"]:
            f_match["node_handles"] = comp_nano_node_dict[f_match["nanoid"]]

        # nlp
        nlp_match_list = []
        for comp_prop in comp_nodes_props:
            comp_hdl_nlp = nlp(comp_prop["handle"].replace("_", " ").lower())
            similarity = base_hdl_nlp.similarity(comp_hdl_nlp)
            if similarity >= sim_threshold:
                nlp_match_list.append(
                    {
                        "nanoid": comp_prop["nanoid"],
                        "model": comp_prop["model"],
                        "handle": comp_prop["handle"],
                        "node_handle": comp_prop["node_handle"],
                        "similarity": similarity,
                    }
                )
        # add top n nlp matches by similarity to nlp matches of base property
        base_prop["nlp_matches"] = sorted(
            nlp_match_list, key=lambda d: (d["similarity"], d["handle"]), reverse=True
        )[:num_nlp]

    df_cols = [f"{base_model}_node", f"{base_model}_prop"]
    for mod in comp_models:
        df_cols.extend([f"{mod}_fuzzy", f"{mod}_nlp"])
    df = pd.DataFrame(columns=df_cols)

    for base_prop in base_nodes_props:
        row = [base_prop["node_handle"], base_prop["handle"]]
        for model in comp_models:
            row.extend(
                [
                    _join_model_fuzzy_matches(base_prop, model),
                    _join_model_nlp_matches(base_prop, model),
                ]
            )
        df.loc[len(df.index)] = row

    df.to_csv(filepath, index=False)


if __name__ == "__main__":
    main()
