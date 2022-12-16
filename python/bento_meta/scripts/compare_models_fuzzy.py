"""Command line interface for python script to compare MDB models using fuzzy matching"""

from pathlib import Path
from typing import List

import click
from bento_meta.mdb import SearchableMDB
from bento_meta.mdb.mdb_tools import ToolsMDB
from bento_meta.objects import Property


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
    help="model to compare to other models in MDB",
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
    help="path to .txt file for output",
)
@click.option(
    "--output_filepath",
    required=True,
    default=False,
    type=str,
    prompt=True,
    help="add commit string to newly created nodes/relationships",
)
def main(
    mdb_uri: str,
    mdb_user: str,
    mdb_pass: str,
    base_model: str,
    comp_models: List[str],
    output_filepath: str
) -> None:
    """
    Fuzzy matching to compare base_model's node/property handles to those of comp_model(s).

    Args:
        mdb_uri (str): MDB instance bolt uri
        mdb_user (str): MDB instance username
        mdb_pass (str): MDB instance password
        base_model (str): model name (e.g., GDC)
        comp_models (List[str]): comparison model name(s)
        output_filepath (str): file path for output CSV

    Output:
        .txt file with base node/property handles and any matching node/property handles
    """
    filepath = Path(output_filepath)

    base_handles = {"nodes": [], "props": [], "nodes-props": []}
    matches = {"nodes": [], "props": [], "nodes-props": []}
    comp_models.insert(0, "base")

    mdb = SearchableMDB(uri=mdb_uri, user=mdb_user,  password=mdb_pass)
    tmdb = ToolsMDB(uri=mdb_uri, user=mdb_user,  password=mdb_pass)

    # gather all node and property handles for given base model
    for node in mdb.get_nodes_and_props_by_model(model=base_model):
        base_handles["nodes"].append(node["handle"]) # type: ignore
        for prop in node["props"]: # type: ignore
            base_handles["props"].append(prop["handle"]) # type: ignore
            base_handles["nodes-props"].append([node["handle"], prop["handle"]]) # type: ignore

    # search fulltext index of node/prop handles for base model node handles
    for hdl in base_handles["nodes"]:
        items = mdb.search_entity_handles(hdl.replace("_", "*"))
        dta = {}
        for it in items["nodes"]: # type: ignore
            ent = it["ent"]
            if not ent["model"] in dta:
                dta[ent["model"]] =  [ent["handle"]]
            else:
                dta[ent["model"]].append( ent["handle"] )
        if dta:
            matches["nodes"].append(dta)

    # search fulltext index of node/prop handles for base model property handles
    for np in base_handles["nodes-props"]:
        p_hdl = np[1]
        dta = {"base": [": ".join(np)]}
        p_hdl_wc = p_hdl.replace("_", "*")
        items = mdb.search_entity_handles(p_hdl_wc)    
        for it in items["properties"]: # type: ignore
            ent = it["ent"]
            if not ent["model"] in dta:
                dta[ent["model"]] = [ent["handle"]]
            else:
                dta[ent["model"]].append(ent["handle"])

            p_ent = Property({
                "nanoid": ent["nanoid"],
                "handle": ent["handle"],
                "model": ent["model"],
                })

            syn_list = []
            syn_nanos = []
            synonym_result = tmdb.get_property_synonyms(p_ent)
            # get all synonyms (props linked by concept) of base prop
            if synonym_result:
                for synonym in synonym_result:
                    for var_name in synonym:
                        syn_mod_hdl = [synonym[var_name]['model'], synonym[var_name]['handle']] # type: ignore
                        if syn_mod_hdl not in syn_list:
                            syn_nanos.append(synonym[var_name]['nanoid']) # type: ignore
                            syn_list.append(syn_mod_hdl)

                # workaround to get "bonus synonyms" (not linked by concept to base_prop, but linked to syns of base_prop)
                for syn_nano in syn_nanos:
                    bonus_synonym_result = tmdb.get_property_synonyms(Property({"nanoid": syn_nano}))
                    for bonus_synonym in bonus_synonym_result:
                        for bonus_var_name in bonus_synonym:
                            if bonus_synonym[bonus_var_name]['nanoid'] != p_ent.nanoid: # type: ignore
                                bonus_syn_mod_hdl = [
                                    bonus_synonym[bonus_var_name]['model'], # type: ignore
                                    bonus_synonym[bonus_var_name]['handle'] # type: ignore
                                    ]
                                if bonus_syn_mod_hdl not in syn_list:
                                    syn_list.append(bonus_syn_mod_hdl)

                # append synonyms to results of fuzzy matching for prop handles
                for mod_hdl in syn_list:
                    mod = mod_hdl[0]
                    hdl = mod_hdl[1]
                    if mod not in dta.keys():
                        dta[mod] = []
                    dta[mod].append(hdl)

        # eliminate any duplicate prop handles
        for mod in dta.keys():
            dta[mod] = list(set(dta[mod]))

        # add dta to matches
        if dta:
            matches["props"].append(dta)

    nodes = []
    props = []
    for nds in matches["nodes"]:
        nodes.append("\t".join( [ "" if x not in nds else "|".join(nds[x]) for x in comp_models ] ))

    for prs in matches["props"]:
        props.append("\t".join( [ "" if x not in prs else "|".join(prs[x]) for x in comp_models ] ))

    with open(filepath, "w", encoding="UTF-8") as f:
        f.write("Nodes\n")
        f.write("\t".join(comp_models))
        f.write("\n")
        for l in sorted(list({x for x in nodes})):
            f.write(f"{l}\n")
        f.write("Properties\n")
        f.write("\t".join(comp_models))
        f.write("\n")
        for l in sorted(list({x for x in props})):
            f.write(f"{l}\n")
            
if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
