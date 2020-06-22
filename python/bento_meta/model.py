import re
import sys
from uuid import uuid4
from warnings import warn

import neo4j.graph
sys.path.append('..')
from bento_meta.entity import Entity
from bento_meta.objects import Node, Property, Edge, Term, ValueSet, Concept, Origin

class ArgError(Exception):
  pass

class Model(object):
  def __init__(self,handle=None):
    if not handle:
      raise ArgError("model requires arg 'handle' set")
    self.handle = handle
    self.nodes={}
    self.edges={} # keys are (edge.handle, src.handle, dst.handle) tuples
    self.props={} # keys are ({edge|node}.handle, prop.handle) tuples
    self.terms={}
    # neo4j cxn here later

  def get(self):
    # get from neo4j if connected
    pass

  def put(self):
    # put to neo4j if connected
    pass

  def add_node(self, node=None):
    if not node:
      raise ArgError("arg must be Node, dict, or graph.Node")
    if isinstance(node, (dict, neo4j.graph.Node)):
      node = Node(node)
    if not node.model:
      node.model = self.handle
    for p in node.props.values():
      self.add_prop(node, p)
    self.nodes[node.handle] = node

  def add_edge(self, edge=None):
    if not edge:
      raise ArgError("arg must be Edge, dict, or graph.Node")
    if isinstance(edge, (dict, neo4j.graph.Node)):
      edge = Edge(edge)
    if not edge.src or not edge.dst:
      raise ArgError("edge must have both src and dst set")
    if not edge.model:
      edge.model = self.handle
    if not self.contains(edge.src):
      warn("Edge source node not yet in model; adding it")
      self.add_node(edge.src)
    if not self.contains(edge.dst):
      warn("Edge destination node not yet in model; adding it")
      self.add_node(edge.dst)
    for p in edge.props.values():
      self.add_prop(edge,p)
    self.edges[edge.triplet] = edge
    pass

  def add_prop(self, ent, prop=None):
    if not isinstance(ent, (Node, Edge)):
      raise ArgError("arg 1 must be Node or Edge")
    if not prop:
      raise ArgError("arg 2 must be Property, dict, or graph.Node")
    if not prop.model:
      prop.model = self.handle
    if isinstance(prop, (dict, neo4j.graph.Node)):
      init = Property(init)
    key = [ent.handle] if isinstance(ent,Node) else list(ent.triplet)
    key.append(prop.handle)
    self.props[tuple(key)] = prop
    pass

  def add_terms(self, prop, *terms):
    if not isinstance(prop, Property):
      raise ArgError("arg1 must be Property")
    if not re.match('value_set|enum',prop.value_domain):
      raise AttributeError("Property value domain is not value_set or enum, can't add terms")
    if not prop.value_set:
      warn("Creating ValueSet object for Property "+prop.handle)
      prop.value_set = ValueSet({ "prop":prop })
      prop.value_set._id=str(uuid4())
    for t in terms:
      if isinstance(t, str):
        warn("Creating Term object for string '{term}'".format(term=t))
        t = Term({ "value":t })
      elif not isinstance(t,Term):
        raise ArgError("encountered arg that was not a str or Term object")
      prop.value_set.terms[t.value]=t

  def rm_node(self, node):
    if not isinstance(node, Node):
      raise ArgError("arg must be a Node object")
    if not self.contains(node):
      warn("node '{node}' not contained in model '{model}'".format(node=node.handle, model=model.handle))
      return
    if self.edges_by_src(node) or self.edge_by_dst(node):
      raise ValueError("can't remove node '{node}', it is participating in edges".format(node=node.handle))
    for p in node.props:
      try:
        del self.props[(node.handle, p.handle)]
      except:
        pass
    del self.nodes[node.handle]
    return node
      

  def rm_edge(self, edge):
    if not isinstance(edge, Edge):
      raise ArgError("arg must be an Edge object")
    if not self.contains(edge):
      warn("edge '{edge}' not contained in model '{model}'".format(edge=edge.triplet, model=model.handle))
      return
    del self.edges[edge.triplet]
    return edge


  def rm_prop(self, prop):
    if not isinstance(prop, Property):
      raise ArgError("arg must be a Property object")
    pass

  def rm_term(self, term):
    if not isinstance(term, Term):
      raise ArgError("arg must be a Term object")
    pass

  def contains(self, ent):
    if not isinstance(ent, Entity):
      warn("argument is not an Entity subclass")
      return
    if isinstance(ent, Node):
      return ent in set(self.nodes.values())
    if isinstance(ent, Edge):
      return ent in set(self.edges.values())
    if isinstance(ent, Property):
      return ent in set(self.props.values())
    pass

  def edges_in(self, node):
    if not  isinstance(node,Node):
      raise ArgError("arg must be Node")
    return [self.edges[i] for i in self.edges if i[2]==node.handle]
    pass

  def edges_out(self, node):
    if not  isinstance(node,Node):
      raise ArgError("arg must be Node")
    return [self.edges[i] for i in self.edges if i[1]==node.handle]    
    pass

  def edges_by(self, key, item):
    if not key in ['src','dst','type']:
      raise ArgError("arg 'key' must be one of src|dst|type")
    if isinstance(item, Node):
      idx = 1 if key == 'src' else 2
      return [self.edges[x] for x in self.edges if x[idx] == item.handle]
    else:
      return [self.edges[x] for x in self.edge if x[0] == item]

  def edges_by_src(self,node):
    return self.edges_by('src',node)

  def edges_by_dst(self,node):
    return self.edges_by('dst',node)

  def edges_by_type(self,edge_handle):
    if not isinstance(edge_handle,str):
      raise ArgError("arg must be str")
    return self.edges_by('type',edge_handle)    

