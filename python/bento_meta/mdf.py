import sys
sys.path.extend(['.','..'])
from  bento_meta.model import Model
from bento_meta.entity import ArgError,CollValue
from bento_meta.objects import Node,Property,Edge, Term, ValueSet, Concept, Origin
import re
import yaml
import option_merge as om
from collections import ChainMap
from warnings import warn
from uuid import uuid4

from pdb import set_trace

class MDF(object):
  default_mult = 'one_to_one'
  default_type = 'TBD'
  def __init__(self, *yaml_files,handle=None):
    if not handle or not isinstance(handle,str):
      raise ArgError("arg handle= must be a str - name for model")
    self.handle = handle
    self.files = yaml_files
    self.schema = om.MergedOptions()
    self.model = None
    if self.files:
      self.load_yaml()
      self.create_model()
    else:
      warn("No MDF files provided to constructor")
    pass

  def load_yaml(self):
    yloader = yaml.loader.Loader
    for f in self.files:
      if isinstance(f,str):
        f = open(f,"r")
      try:
        yml = yaml.load(f,Loader=yloader)
        self.schema.update(yml)
      except ConstructorError as ce:
        print("YAML constructor failed in '{fn}':\n{e}".format(fn=f.name,e=ce))
        raise ce
      except ParserError as pe:
        print("YAML parser failed in '{fn}':\n{e}".format(fn=f.name,e=pe))
        raise pe
      except Exception:
        raise
      
  def create_model(self):
    if not self.schema.keys():
      raise ValueError("attribute 'schema' not set - are yamls loaded?")
    self.model = Model(handle=self.handle)
    ynodes = self.schema['Nodes']
    yedges = self.schema['Relationships']
    ypropdefs = self.schema['PropDefinitions']
    # create nodes
    for n in ynodes:
      yn = ynodes[n]
      init = { "handle":n, "model":self.handle }
      for a in ['category','desc']:
        if yn.get(a):
          init[a]=yn[a]
      node = self.model.add_node(init)
      if yn.get('Tags'):
        tags=CollValue({},owner=node,owner_key='tags')
        for t in yn['Tags']:
          tags[t]=Tag({"value":t})
        node['tags'] = tags
    # create edges (relationships)
    for e in yedges:
      ye = yedges[e]
      for ends in ye['Ends']:
        init = { "handle":e, "model":self.handle,
                 "src":self.model.nodes[ends['Src']],
                 "dst":self.model.nodes[ends['Dst']],
                 "multiplicity":ends.get("Mul") or ye.get("Mul") or
                 MDF.default_mult,
                 "desc":ends.get("Desc") or ye.get("Desc") }
        edge = self.model.add_edge(init)
        Tags = ye.get('Tags') or ends.get('Tags')
        if Tags:
          tags=CollValue({},owner=edge,owner_key='tags')
          for t in Tags:
            tags[t]=Tag({"value":t})
            edge['tags'] = tags
    # create properties
    for ent in ChainMap(self.model.nodes, self.model.edges).values():
      if isinstance(ent,Node):
        pnames = ynodes[ent.handle]['Props']
      elif isinstance(ent,Edge):
        # props elts appearing Ends hash take
        # precedence over Props elt in the
        # handle's hash
        (hdl,src,dst) = ent.triplet
        [end] = [e for e in yedges[hdl]['Ends'] if e['Src'] == src and
                 e['Dst'] == dst]
        pnames = end.get('Props') or yedges[hdl].get('Props')
      else:
        raise AttributeError("unhandled entity type {type} for properties".format(type=type(ent).__name__))
      if pnames:
        for pname in pnames:
          ypdef = ypropdefs[pname]
          init = { "handle":pname, "model":self.handle}
          if ypdef.get('Type'):
            init.update( self.calc_value_domain(ypdef['Type']) )
          else:
            init['value_domain']=MDF.default_type
          prop = self.model.add_prop(ent, init)
          ent.props[prop.handle]=prop
          if ypdef.get('Tags'):
            tags=CollValue({},owner=node,owner_key='tags')
            for t in ypdef['Tags']:
              tags[t]=Tag({"value":t})
            prop['tags'] = tags
    return self.model

  def calc_value_domain(self,typedef):
    if isinstance(typedef,dict):
      if typedef.get('pattern'):
        return {"value_domain":"regexp",
                "pattern":typedef['pattern']}
      elif typedef.get('units'):
        return {"value_domain":typedef.get('value_type'),
                "units":";".join(typedef.get('units'))}
      else:
        # punt
        warn("MDF type descriptor unrecognized: json looks like {j}".format(j=json.dumps(typedef)))
        return {"value_domain":json.dumps(typedef)}
    elif isinstance(typedef,list): # a valueset: create value set and term objs
      vs = ValueSet({"_id":str(uuid4())})
      vs.handle = self.handle+vs._id[0:8]
      if re.match("^(?:https?|bolt)://",typedef[0]): #looks like url
        vs.url = typedef[0]
      else: # an enum
        for t in typedef:
          vs.terms[t] = Term({"value":t})
      return { "value_domain":"value_set",
               "value_set":vs }
    else:
      return {"value_domain":MDF.default_type}
                             
    