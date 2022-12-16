"""Command line interface for python script to compare MDB models using NLP (Spacy Similarity)"""

from pathlib import Path
from typing import List

import click
import pandas as pd
import spacy
from bento_meta.mdb import SearchableMDB


@click.command()
@click.option(
    "--mdb_uri",
    required=True,
    type=str,
    prompt=True,
    help="metamodel database URI"
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
    default=False,
    type=str,
    prompt=True,
    help="model to compare to other model(s) in MDB",
)
@click.option(
    "--comp_models",
    required=True,
    default=False,
    type=List[str],
    prompt=True,
    help="list of model names to compare to base model nodes/props",
)
@click.option(
    "--output_filepath",
    required=True,
    default=False,
    type=str,
    prompt=True,
    help="path to .csv file for output",
)
def main(
    mdb_uri: str,
    mdb_user: str,
    mdb_pass: str,
    base_model: str,
    comp_models: List[str],
    output_filepath: str,
    threshold: float = 0.75
) -> None:
    """
    NLP similarity matching to compare base_model's node/property handles to those of comp_model(s).

    Args:
        mdb_uri (str): MDB instance bolt uri
        mdb_user (str): MDB instance username
        mdb_pass (str): MDB instance password
        base_model (str): model name (e.g., GDC)
        comp_models (List[str]): comparison model name(s)
        output_filepath (str): file path for output CSV
        threshhold (float): terms with similarity scores at or above this
            value will be included in the results csv

    Output:
        .csv file with base node/property handles and any matching
        node/property handles with similarity scores.
    """
    filepath = Path(output_filepath)

    mdb = SearchableMDB(uri=mdb_uri, user=mdb_user,  password=mdb_pass)
    model_prop_dict = {}
    model_np_dict = {}

    # load spaCy NER model
    nlp = spacy.load("en_ner_bionlp13cg_md")

    # instantiate similarity dataframe
    similarity_df = pd.DataFrame(
    columns=[
        "base_prop",
        "base_prop_node",
        "base_prop_model",
        "comp_prop",
        "comp_prop_node",
        "comp_prop_model",
        "similarity"
        ]
    )

    # gather all node and property handles for all models
    for model in comp_models:
        model_props = []
        model_nps = []
        for node in mdb.get_nodes_and_props_by_model(model):
            for prop in node["props"]: # type: ignore
                model_props.append(prop["handle"]) # type: ignore
                model_nps.append([node["handle"], prop["handle"]]) # type: ignore
            model_prop_dict[model] = model_props
            model_np_dict[model] = model_nps

    # remove base model from comp_models if included
    other_models = comp_models
    if base_model in other_models:
        other_models.remove(base_model)

    for base in model_np_dict[base_model]:
        for model in other_models:
            for comp in model_np_dict[model]:
                prop1 = nlp(base[1].replace("_", " ").lower())
                prop2 = nlp(comp[1].replace("_", " ").lower())

                similarity = prop1.similarity(prop2)
                if similarity >= threshold:
                    row = [
                        base[1],
                        base[0],
                        base_model,
                        comp[1],
                        comp[0],
                        model,
                        similarity
                    ]
                    similarity_df.loc[len(similarity_df.index)] = row # type: ignore

    similarity_df.to_csv(filepath)

if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
