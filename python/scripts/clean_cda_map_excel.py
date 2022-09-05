"""Command line interface for python script to format CDA mapping excel file"""

from pathlib import Path

import click
import numpy as np
import pandas as pd


@click.command()
@click.option(
    "--input_filepath",
    required=True,
    type=str,
    prompt=True,
    help="Path to input spreadsheet file; each sheet contains mappings for different endpoint.")
def main(
    input_filepath: str
) -> None:
    """
    Formats Cancer Data Aggregator mappings input spreadsheet to CSVs for entity synonym linking.

    Args:
        input_filepath: Path to input spreadsheet file; each sheet has mappings for a CDA endpoint.

    Returns:
        Creates two CSV files in same directory as input spreadsheet.
        _cleaned CSV contains output with formatted synonyms.
        _other CSV contains other mappings that aren't 1-1 synonyms for further processing.
    """
    # set file paths for output and other files based on input directory
    input_path = Path(input_filepath)
    if not input_path.exists():
        raise RuntimeError(f"Filepath {input_path} not found.")
    output_path = Path(input_path.with_name(f"{input_path.stem}_clean.csv"))
    other_path = Path(input_path.with_name(f"{input_path.stem}_other.csv"))

    endpoints = []
    mapping_dfs = []
    for sheet in pd.read_excel(input_filepath, None).keys():
        endpoint = sheet.split(" ")[0] # type: ignore
        endpoints.append(endpoint)
        df = pd.read_excel(input_filepath, sheet_name=sheet)
        df.name = endpoint
        mapping_dfs.append(df)
    models = list(col for col in mapping_dfs[0].columns if col != "field")

    cda_mapping_df = pd.DataFrame(
        columns=[
            "ent_1_model", "ent_1_handle", "ent_1_extra_handles",
            "ent_2_model", "ent_2_handle", "ent_2_extra_handles"
        ]
    )

    for df in mapping_dfs:
        df_ent_1_handle = np.tile(df.iloc[:, 0], len(models))
        df_ent_1_model = np.repeat("CDA", len(df_ent_1_handle))
        df_ent_2_model = np.repeat(models, len(df.iloc[:, 0]))
        df_ent_1_extra_handle = np.repeat(df.name, len(df_ent_1_handle))
        ent_2_extra_handles_list = []
        for model in models:
            ent_2_extra_handles_list.extend(df[model].tolist())
        ent_2_handle_list = []
        for handle in ent_2_extra_handles_list:
            if not "." in handle or "{" in handle:
                ent_2_handle_list.append(handle)
            else:
                ent_2_handle_list.append(handle.split(".")[-1])

        formatted_df = pd.DataFrame({
            "ent_1_model": df_ent_1_model,
            "ent_1_handle": df_ent_1_handle,
            "ent_1_extra_handles": df_ent_1_extra_handle,
            "ent_2_model": df_ent_2_model,
            "ent_2_handle": ent_2_handle_list,
            "ent_2_extra_handles": ent_2_extra_handles_list
            })
        cda_mapping_df = pd.concat([cda_mapping_df, formatted_df], ignore_index=True)

    # remove unmapped entities
    cda_mapping_df = cda_mapping_df[cda_mapping_df.ent_2_extra_handles != "NOT CURRENTLY MAPPED"]
    cda_mapping_df = cda_mapping_df[cda_mapping_df.ent_2_extra_handles != "NOT APPLICABLE"]

    # move special cases (i.e., fields w/o 1-1 mapping) to other df
    cda_mapping_other_df = cda_mapping_df[
        cda_mapping_df["ent_2_extra_handles"] == cda_mapping_df["ent_2_handle"]]
    cda_mapping_df = cda_mapping_df.drop(cda_mapping_other_df.index) # type: ignore

    # clean up ent_1_handle identifier fields
    cda_mapping_df["ent_1_handle"].mask(cda_mapping_df["ent_1_handle"] == "identifier.value",
                                        "identifier", inplace=True)

    # File off ent 2 handle and extraneous handles from node handle 2.
    # This is because extra handles should be lists of 1-2 strings of handles needed to
    # uniquely identify property and relaitonship nodes in the database.
    cda_mapping_df["ent_2_extra_handles"] = cda_mapping_df[
        "ent_2_extra_handles"].str.rsplit(".", n=1).str[0]
    cda_mapping_df["ent_2_extra_handles"] = cda_mapping_df[
        "ent_2_extra_handles"].str.split(".").str[-1]

    # match MDB naming for ent 1 & 2 extra handles
    cda_mapping_df["ent_1_extra_handles"].replace(
        to_replace=["subject", "researchsubject", "diagnosis", "treatment", "specimen", "file"],
        value=["Subject", "ResearchSubject", "Diagnosis", "Treatment", "Specimen", "File"],
        inplace=True
    )
    cda_mapping_df["ent_2_extra_handles"].replace(
        to_replace=[
            "files", "cases", "demographics", "projects", "diagnoses", "treatments", "samples"],
        value=[
            "file", "case", "demographic", "project", "diagnosis", "treatment", "sample"],
        inplace=True
    )

    # format extra handles for both entities to lists
    # since ent could be relationship, 2 handles may be needed to uniquely id node
    cda_mapping_df["ent_1_extra_handles"] = [[l] for l in cda_mapping_df["ent_1_extra_handles"]]
    cda_mapping_df["ent_2_extra_handles"] = [[l] for l in cda_mapping_df["ent_2_extra_handles"]]

    cda_mapping_df.to_csv(output_path, index=False)
    cda_mapping_other_df.to_csv(other_path, index=False)

    click.echo(f"Cleaned CDA file now at {output_path}")
    click.echo(f"Other CDA file now at {other_path}")

if __name__ == "__main__":
    main() # pylint: disable=no-value-for-parameter
