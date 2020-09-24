import fastavro
from fastavro.schema import load_schema
from fastavro.validation import validate


from tempfile import NamedTemporaryFile
from pdb import set_trace
import json

# the following gyrations enable
# * the PFB schema to be modularized with named types,
# * the addition the custom data types to the pfb.Entity schema, and
# * the recursive loading of the named type schemas by fastavro.

pfb_schema = None
with open("pfb.Entity.avsc","r") as Entity:
    # load Entity schema as simple json
    pfb_schema_json = json.load( Entity )
    # find the "object" hash 
    [object] = [ x for x in pfb_schema_json["fields"] if x["name"] == "object" ]
    # add the custom schemas (as names) to the object.type array
    object["type"].extend([ "icdc.case", "icdc.cohort" ])
    # dump json to a tempfile to take advantage of fastavro avsc 
    # name resolution in fastavro.schema.load_schema()
    tf = NamedTemporaryFile(mode="w+",dir=".")
    json.dump(pfb_schema_json,tf)
    tf.seek(0)
    # load the customized schema
    pfb_schema = load_schema(tf.name)
    pass

# metadata for PFB message:
# note that unused fields still must be defined, since in the schema
# null is not allowed (which seems more like oversight than intention)

icdc_cohort_meta = { 
    "name": "icdc.cohort",
    "ontology_reference": "",
    "values": {},
    "links":[],
    "properties": [
        { 
            "name": "cohort_description",
            "ontology_reference": "NCIT",
            "values": {
                "concept_code": "C166209"
                }
        },
        { 
            "name": "cohort_dose",
            "ontology_reference": "NCIT",
            "values": {
                "concept_code": "C166210"
                }
        }
    ]
}

icdc_case_meta = {
    "name": "icdc.case",
    "ontology_reference": "",
    "values": {},
    "properties": [
        { 
            "name": "case_id",
            "ontology_reference": "NCIT",
            "values": {
              "concept_code": "C164324"
            }
        },
        { 
            "name": "patient_id",
            "ontology_reference": "NCIT",
            "values": {
              "concept_code": "C164337"
            }
        }
        ],
        "links": [
            {
                "name": "member_of",
                "dst": "cohort",
                "multiplicity": "MANY_TO_ONE"
            }
        ]
}

# Metadata    
assert validate( {
    "name":"Metadata",
    "misc":{},
    "nodes": [
        icdc_case_meta,
        icdc_cohort_meta
    ]}, pfb_schema)


# data for PFB message:

cohort_data = {
    "id": "n201",
    "cohort_description": "arm1",
    "cohort_dose": "10mg/kg"
}

assert validate( ("icdc.cohort", cohort_data), pfb_schema )

case_data = {
    "id": "n101",
    "case_id": "UBC01-007",
    "patient_id": "007",
    "patient_first_name": "Fluffy"
}    

assert validate( ("icdc.case", case_data), pfb_schema )

link = {
    "dst_name": "icdc.cohort",
    "dst_id": "n201"
}


case_data_entity = {
    "name": "icdc.case",
    "id": "n101",
    "object": case_data,
    "relations": [ link ]
}

assert validate( ("pfb.Entity", case_data_entity), pfb_schema )

cohort_data_entity = {
    "name":"icdc.cohort",
    "id": "n201",
    "object": cohort_data,
    "relations":[]
}

assert validate( ("pfb.Entity", cohort_data_entity), pfb_schema )

payload = [
      { 
        "name": "Metadata",
        "object": {
            "name": "pfb.Metadata",
            "misc": {},
            "nodes": [
                icdc_cohort_meta,
                icdc_case_meta
            ]
        }
      },
      cohort_data_entity,
      case_data_entity
    ]    

# Create PFB message

with open("worked-example.avro","wb") as out:
    fastavro.writer( out, pfb_schema, payload)

# Read records from message

with open("worked-example.avro","rb") as inf:
    rdr = fastavro.reader(inf)
    for rec in rdr:
        print(rec)

