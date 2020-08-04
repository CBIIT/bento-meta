import sys
sys.path.insert(1,'../../python')
from bento_meta.mdf import MDF
from bento_meta.model import Model
from bento_meta.object_map import ObjectMap
from bento_meta.objects import *
from warnings import warn
from pdb import set_trace
from neo4j import GraphDatabase
import csv
import uuid

port= sys.argv[1] if len(sys.argv) > 1 else 7687
bolt_url = 'bolt://localhost:{}'.format(port)
try:
    drv = GraphDatabase.driver(bolt_url) if bolt_url else None
except:
    drv = None
    
origin_om = ObjectMap(cls=Origin,drv=drv);
term_om = ObjectMap(cls=Term,drv=drv)
concept_om = ObjectMap(cls=Concept,drv=drv)

# create local origin objects for terms
origins = {"icdc":Origin({"name":"ICDC"}),
  "ctdc":Origin({"name":"CTDC"}),
  "bento":Origin({"name":"Bento"}),
  "ncit":Origin({"name":"NCIt"}) }
  

# latest MDF for each model

mdf = {
  "bento":[
    "https://cbiit.github.io/bento-model/model-desc/bento_model_file.yaml",
    "https://cbiit.github.io/bento-model/model-desc/bento_model_properties.yaml"
    ],
  "icdc":[
    "https://cbiit.github.io/icdc-model-tool/model-desc/icdc-model.yml",
    "https://cbiit.github.io/icdc-model-tool/model-desc/icdc-model-props.yml"
    ],
  "ctdc":[
    "https://cbiit.github.io/ctdc-model/model-desc/ctdc_model_file.yaml",
    "https://cbiit.github.io/ctdc-model/model-desc/ctdc_model_properties_file.yaml"
    ]}

print("read models")
models = { "icdc":MDF(*mdf["icdc"],handle='ICDC').model,
  "ctdc":MDF(*mdf["ctdc"],handle='CTDC').model,
  "bento":MDF(*mdf["bento"],handle='Bento').model}

# pulling from MDF auto-creates value set objects and their terms
# uniquify the terms within models

mdl_terms = {}
concepts = {}
put_terms = []


for mdl in models:
    m = models[mdl]
    mdl_terms[mdl] = {}
    for v in [p.value_set for p in m.props.values() if p.value_domain=='value_set']:
        for t in v.terms.values():
            if not mdl_terms[mdl].get(t.value):
                mdl_terms[mdl][t.value] = {'VS':[]}
            mdl_terms[mdl][t.value]['VS'].append(v) # value sets
    for tv in mdl_terms[mdl]: #term value
        term = mdl_terms[mdl][tv]['VS'][0].terms[tv]
        for vs in mdl_terms[mdl][tv]['VS']:
            vs.terms[tv] = term
            vs.clear_removed_entities()
        mdl_terms[mdl][tv]['TERM'] = term # = unique term for all value sets
        if not concepts.get(term.value):
          concepts[term.value] = Concept({"_id":str(uuid.uuid4())}) # create unique concept 
        term.concept = concepts[term.value]
        term.origin = origins[mdl]
        pass
    pass

# now mdl_terms contains a unique Term for each term value, for each model:
# e.g., mdl_terms['bento']['submission_enabled']['TERM'] is a single Term object
# each Term has a Concept (possibly reused) and an Origin
    
# Issue with versioning - MDF() doesn't version the objects. Turning on versioning
# confuses bento_meta on the non-versioned mdf-derived models
#Model.versioning(True)
#Model.set_version_count(1)

# create concept and term nodes that represent Nodes, Relationships, and Properties
# create Term objects for each N/R/P linked to model origin, where
# term.value = entity.handle

# creating separate term objects for each entity type - term.value is unique
# within an entity type, not nec between types

# creating concepts for the edge type, not the edge triplet (which can be
# different semantically) - so all Relationships with the same handle
# will point to the same Concept

# multiply terms, conserve concepts

# compare N/R/P handles among the models, identify those N/R/P that are
# synonymous in meaning among them, connect these to single concept nodes

# link the entity term objects to the appropriate concepts

print("create concepts and terms")
entity_concepts = {}
for mdl in ['icdc','ctdc','bento']: # models:
  for n in models[mdl].nodes.values():
    if not entity_concepts.get(n.handle):
      entity_concepts[n.handle] = Concept({"_id":str(uuid.uuid4())})
    t = Term({"value":n.handle, "_id":str(uuid.uuid4())})
    put_terms.append(t)
    t.origin = origins[mdl]
    t.concept = entity_concepts[n.handle]
    n.concept = entity_concepts[n.handle]

  for e in models[mdl].edges.values():
    terms = {}
    if not entity_concepts.get(e.handle):
      entity_concepts[e.handle] = Concept({"_id":str(uuid.uuid4())})
    if not terms.get(e.handle):
      t= Term({"value":e.handle, "_id":str(uuid.uuid4())})
      put_terms.append(t)
      terms[e.handle] = t
      t.origin = origins[mdl]
      t.concept = entity_concepts[e.handle]
    e.concept = entity_concepts[e.handle]

  for p in models[mdl].props.values():
    if not entity_concepts.get(p.handle):
      entity_concepts[p.handle] = Concept({"_id":str(uuid.uuid4())})
    t = Term({"value":p.handle, "_id":str(uuid.uuid4())})
    put_terms.append(t)
    t.origin = origins[mdl]
    t.concept = entity_concepts[p.handle]
    p.concept = entity_concepts[p.handle]

# examine NCIt mappings to identify NCIt terms to create;
# link these to appropriate concepts 
# NCIt Term object property values:
# term.value -> NCI PT (preferred term)
# term.origin_id -> NCI Code, Concept Code
# term.origin_definition -> NCI DEF, NCIt Definition

nci_terms = {}

print("create and link NCIt terms")
with open("ICDC_Property_Terminology_20_06d.txt") as f:
  rdr = csv.DictReader(f,dialect='excel-tab')
  for dta in rdr:
    if not nci_terms.get(dta["Concept Code"]):
      nci_terms[dta["Concept Code"]] = Term({"value":dta["NCIt Preferred Term"],
                    "origin_id":dta["Concept Code"],
                    "origin_definition":dta["NCIt Definition"]})
      put_terms.append(nci_terms[dta["Concept Code"]])
      nci_terms[dta["Concept Code"]].origin = origins["ncit"]
    t = nci_terms[dta["Concept Code"]]

    pp = [ models["icdc"].props[x] for x in models["icdc"].props if dta["ICDC Preferred Term"] in x ]
    if len(pp) > 1:
      if len({ x for x in pp }) > 1:
        warn("Multiple instances of property object {}".format(pp[0].handle))
    if len(pp):
      if not t.concept:
        t.concept = pp[0].concept
    else:
      warn("No property in model matching {}".format(dta["ICDC Preferred Term"]))


with open("CTDC_node_and_property_map_05282020.nodes.txt") as f:
  rdr = csv.DictReader(f,dialect='excel-tab')
  for dta in rdr:
    if not nci_terms.get(dta["NCI Code"]):
      nci_terms[dta["NCI Code"]] = Term({"value":dta["NCI PT"],
                  "origin_id":dta["NCI Code"],
                  "origin_definition":dta["NCI DEF"]})
      put_terms.append(nci_terms[dta["NCI Code"]])
      nci_terms[dta["NCI Code"]].origin = origins["ncit"]
    t = nci_terms[dta["NCI Code"]]
    # find concept based on local node
    if dta['Node'] in models["ctdc"].nodes:
      model_n = models["ctdc"].nodes[dta['Node']]
      if not t.concept:
        t.concept = model_n.concept
    else:
      warn("Can't find CTDC node with handle {}".format(dta['Node']))
    
with open("CTDC_node_and_property_map_05282020.nodeprops.txt") as f:
  rdr = csv.DictReader(f,dialect='excel-tab')
  for dta in rdr:
    if dta["Node"].find(';') >= 0:
        dta["Node"] = dta["Node"].split(";")[0]
    if not nci_terms.get(dta["NCI Code"]):
      nci_terms[dta["NCI Code"]] = Term({"value":dta["NCI PT"],
                  "origin_id":dta["NCI Code"],
                  "origin_definition":dta["NCI DEF"]})
      put_terms.append(nci_terms[dta["NCI Code"]])
      nci_terms[dta["NCI Code"]].origin = origins["ncit"]
    t = nci_terms[dta["NCI Code"]]
    # find concept based on local property
    key = (dta["Node"],dta["Property"])
    if key in models["ctdc"].props:
      model_p = models["ctdc"].props[key]
      if not t.concept:
        t.concept = model_p.concept
    else:
      warn("Can't find CTDC property with key {}".format(key))
    
with open("CTDC_node_and_property_map_05282020.edgeprops.txt") as f:
  rdr = csv.DictReader(f,dialect='excel-tab')
  for dta in rdr:
    if dta["Relationship"].find(';') >= 0:
        dta["Relationship"] = dta["Relationship"].split(";")[0]
    ee = models["ctdc"].edges_by_type(dta["Relationship"])
    if ee:
        if dta["Property"] in ee[0].props:
            model_p = ee[0].props[dta["Property"]]
            if not nci_terms.get(dta["NCI Code"]):
              nci_terms[dta["NCI Code"]] = Term({"value":dta["NCI PT"],
                    "origin_id":dta["NCI Code"],
                    "origin_definition":dta["NCI DEF"]})
              put_terms.append(nci_terms[dta["NCI Code"]])
              nci_terms[dta["NCI Code"]].origin = origins["ncit"]
            t = nci_terms[dta["NCI Code"]]
            if not t.concept:
                t.concept = model_p.concept
        else:
            warn("Property {} is not found among edge {} properties".format(dta["Property"],ee[0].triplet))
    else:
        warn("No edge found with type {}".format(dta["Relationship"]))

print("Put to db")

# put from models does not reach origin nodes.
for o in origins:
  origin_om.put(origins[o])

print("Put terms and concepts")
# term concepts
for c in concepts.values():
    concept_om.put(c)

# entity concepts
for c in entity_concepts.values():
    concept_om.put(c)

# model terms
for mdl in mdl_terms:
    for val in mdl_terms[mdl]:
        if 'TERM' in mdl_terms[mdl][val]:
            term_om.put(mdl_terms[mdl][val]['TERM'])
        else:
            print("No TERM for {}:{}".format(mdl,val))

# entity and NCIt terms
for t in put_terms:
    term_om.put(t)

for mdl in models:
    print("Put {}".format(mdl))
    models[mdl].drv = drv
    models[mdl].dput()


