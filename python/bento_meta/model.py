import re
import sys
import neo4j.graph
sys.path.append('..')
from bento_meta.objects import Node, Property, Edge, Term, ValueSet, Concept, Origin

class ArgError(Exception):
  pass

class Model(object):
  def __init__(self,handle=None):
    if not handle:
      raise ArgError("model requires arg 'handle' set")
    self.handle = handle
    self.nodes={}
    self.edges={}
    self.props={}
    self.__edge_table={}
    # neo4j cxn here later

  def get(self):
    # get from neo4j if connected
    pass

  def put(self):
    # put to neo4j if connected
    pass

  def add_node(self, init):
    if isinstance(init, dict, neo4j.graph.Node):
      init = Node(init)
    
    pass

  def add_edge(self, init):
    if isinstance(init, dict, neo4j.graph.Node):
      init = Edge(init)
    pass

  def add_prop(self, init):
    if isinstance(init, dict, neo4j.graph.Node):
      init = Property(init)
    pass

  def add_term(self, prop, *terms):
    if isinstance(init, dict, neo4j.graph.Node):
      init = Term(init)
    pass

  def rm_node(self, node):
    if not isinstance(node, Node):
      raise ArgError("arg must be a Node object")
    pass

  def rm_edge(self, edge):
    if not isinstance(edge, Edge):
      raise ArgError("arg must be an Edge object")
    pass

  def rm_prop(self, prop):
    if not isinstance(prop, Property):
      raise ArgError("arg must be a Property object")
    pass

  def rm_term(self, term):
    if not isinstance(term, Term):
      raise ArgError("arg must be a Term object")
    pass

  def contains(self, ent):
    pass

  def edges_in(self, node):
    pass

  def edges_out(self, node):
    pass

  def edges_by(self, key):
    if not key in ['src','dst','type']:
      raise ArgError("arg 'key' must be one of src|dst|type")
    
    pass

  def edges_by_src(self,node):
    pass

  def edges_by_dst(self,node):
    pass

  def edges_by_type(self,edge_handle):
    pass
