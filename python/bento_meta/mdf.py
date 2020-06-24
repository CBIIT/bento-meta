import sys
sys.path.extend(['.','..'])
from  bento_meta.model import Model
from bento_entity import ArgError,CollValue
from bento_meta.objects import Node,Property,Edge, Term, ValueSet, Concept, Origin
import re
import yaml
import option_merge as om
from collections import ChainMap

class MDF(object):
  default_mult = 'one_to_one'
  default_type = 'TBD'
  def __init__(self, *yaml_files,*,handle=None):
    if not handle or not isinstance(handle,str):
      raise ArgError("arg handle= must be a str - name for model")
    self.handle = handle
    self.files = yaml_files
    self.schema = om.MergedOptions()
    self.model = None
    self.load_yaml()
    self.create_model()
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
    for n in nodes:
      yn = ynodes[n]
      init = { "handle":n, "model":self.handle }
      for a in ['category','desc']:
        if yn[a]:
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
    for ent in ChainMap(model.nodes, model.edges).values():
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
      for pname in pnames:
        ypdef = ypropdefs[pname]
        init = { "handle":pname, "model":self.handle,
                 "type":self.calc_value_domain(ypdef['Type']) or
                 MDF.default_type }
      prop = self.model.add_prop(ent, init)
      if ypdef.get('Tags'):
        tags=CollValue({},owner=node,owner_key='tags')
        for t in ypdef['Tags']:
          tags[t]=Tag({"value":t})
        prop['tags'] = tags
    return self.model

  def calculate_value_domain(self,typedef):
    if isinstance(typedef,dict):
      pass
    elif isinstance(typedef,list):
      pass
    else:
      return MDF.default_type
                             
    
