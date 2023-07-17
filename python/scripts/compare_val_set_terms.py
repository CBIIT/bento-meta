"""
Command line interface for python script to generates tsv file comparing
terms in value sets of properties between 2 models in the MDB.
"""

from pathlib import Path

import click
import pandas as pd
from bento_meta.mdb.mdb_tools.mdb_tools import ToolsMDB
from bento_meta.objects import Property


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
    default=False,
    type=str,
    prompt=True,
    help="model for value set comparison (e.g., 'PDC')",
)
@click.option(
    "--comp_model",
    required=True,
    default=False,
    type=str,
    prompt=True,
    help="comparison model (e.g., 'GDC')",
)
@click.option(
    "--output_filepath",
    required=True,
    default=False,
    type=str,
    prompt=True,
    help="path to .csv file for output",
)
def main(mdb_uri, mdb_user, mdb_pass, base_model, comp_model, output_filepath):
    """
    Generates tsv file comparing terms in value sets of properties
    between 2 models in the MDB.

    :param str mdb_uri: metamodel database URI
    :param str mdb_user: metamodel database username
    :param str mdb_pass: metamodel database password
    :param str base_model: model for value set comparison (e.g., "PDC")
    :param str comp_model: comparison model (e.g., "GDC")
    :param str output_filepath: path to .tsv file for output
    """
    filepath = Path(output_filepath)
    mdb = ToolsMDB(uri=mdb_uri, user=mdb_user, password=mdb_pass)

    # gather all properties w/ val_sets and their terms for models of interest
    # these are lists of dicts where the keys to each dict are 'prop' & 'terms'
    base_props_terms = mdb.get_props_and_terms_by_model(base_model)
    comp_props_terms = mdb.get_props_and_terms_by_model(comp_model)

    # get list of all nanoids in comp_props_terms
    comp_nanos = []
    for prop_term in comp_props_terms:
        comp_nanos.append(prop_term["prop"]["nanoid"])

    # instantiate list of rows for output
    row_list = []

    # iterate through base props, find synonyms, add terms and number shared between them
    for pt_dict in base_props_terms:
        # set base row to only base prop handle, template for new syn rows
        base_row = {
            "base_prop": pt_dict["prop"]["handle"],
            "synonym_prop": "",
            "shared_terms": "",
            "num_shared_terms": "",
            "base_terms_only": "",
            "synonym_terms_only": "",
        }
        prop = Property({"nanoid": pt_dict["prop"]["nanoid"]})

        # get set of all base prop term values
        base_term_val_set = {str(x["value"]) for x in pt_dict["terms"]}

        # get synonyms for each prop
        prop_synonyms = mdb.get_property_synonyms_all(prop)

        if not prop_synonyms:
            # add row with just base_handle and base terms and move on
            row = base_row
            # add base data to row and append to list of rows (no synonyms)
            row["base_terms_only"] = "|".join(sorted(base_term_val_set))
            row[
                "num_shared_terms"
            ] = f"{str(0)}/{str(len(base_term_val_set))} (both/{base_model})"
            row_list.append(row)
            continue

        # check if synonyms in comp_props_terms
        syn_nanos = []
        for synonym in prop_synonyms:
            # add syn_nano if it is in comp model's nano list and not duplicated
            if synonym.nanoid in comp_nanos and synonym.nanoid not in syn_nanos:
                syn_nanos.append(synonym.nanoid)

        # add row to dataframe with synonym info for each synonym
        for nano in syn_nanos:
            # set row to base_row and add information for base and synonym props/terms
            row = base_row

            # get each synonym's prop and term information
            comp_pt_dict = comp_props_terms[comp_nanos.index(nano)]

            # get set of all comp prop term values
            comp_term_val_set = {str(x["value"]) for x in comp_pt_dict["terms"]}

            # compare sets of terms for base and comp
            terms_both = list(base_term_val_set & comp_term_val_set)
            terms_base_only = list(base_term_val_set - comp_term_val_set)
            terms_comp_only = list(comp_term_val_set - base_term_val_set)

            # add data to row and append to list of rows
            row["synonym_prop"] = comp_pt_dict["prop"]["handle"]
            row["shared_terms"] = "|".join(sorted(terms_both))
            row[
                "num_shared_terms"
            ] = f"{str(len(terms_both))}/{str(len(base_term_val_set))} (both/{base_model})"
            row["base_terms_only"] = "|".join(sorted(terms_base_only))
            row["synonym_terms_only"] = "|".join(sorted(terms_comp_only))
            row_list.append(row)

    # create dataframe from list of row dicts
    output_df = pd.DataFrame.from_records(row_list)

    output_df = output_df.rename(
        columns={
            "base_prop": f"{base_model}_property",
            "synonym_prop": f"{comp_model}_property",
            "shared_terms": "shared_terms",
            "num_shared_terms": "num_shared_terms",
            "base_terms_only": f"{base_model}_terms_only",
            "synonym_terms_only": f"{comp_model}_terms_only",
        }
    )

    # drop any duplicate rows
    output_df = output_df.drop_duplicates()

    # output tsv with results
    output_df.to_csv(filepath, index=False, sep="\t")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
