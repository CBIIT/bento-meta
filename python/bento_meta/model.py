import re
import sys
from uuid import uuid4
from warnings import warn
from neo4j import BoltDriver, Neo4jDriver
import neo4j.graph
sys.path.append('..')
from bento_meta.object_map import ObjectMap
from bento_meta.entity import Entity
from bento_meta.objects import Node, Property, Edge, Term, ValueSet, Concept, Origin, Tag

from pdb import set_trace

class ArgError(Exception):
  pass

class Model(object):
  def __init__(self,handle=None,drv=None):
    if not handle:
      raise ArgError("model requires arg 'handle' set")
    self.handle = handle
    self.nodes={}
    self.edges={} # keys are (edge.handle, src.handle, dst.handle) tuples
    self.props={} # keys are ({edge|node}.handle, prop.handle) tuples
    self.terms={}
    self.removed_entities=[]

    if drv:
      if isinstance(drv,(BoltDriver, Neo4jDriver)):
        self.drv=drv
        for cls in ( Node, Property, Edge, Term, ValueSet, Concept, Origin, Tag ):
          cls.object_map=ObjectMap(cls=cls,drv=drv)
      else:
        raise ArgError("drv= arg must be Neo4jDriver or BoltDriver (returned from GraphDatabase.driver())")
    else:
      self.drv=None

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
    return node

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
    return edge

  def add_prop(self, ent, prop=None):
    if not isinstance(ent, (Node, Edge)):
      raise ArgError("arg 1 must be Node or Edge")
    if not prop:
      raise ArgError("arg 2 must be Property, dict, or graph.Node")
    if isinstance(prop, (dict, neo4j.graph.Node)):
      prop = Property(prop)
    if not prop.model:
      prop.model = self.handle
    key = [ent.handle] if isinstance(ent,Node) else list(ent.triplet)
    key.append(prop.handle)
    self.props[tuple(key)] = prop
    return prop

  def add_terms(self, prop, *terms):
    if not isinstance(prop, Property):
      raise ArgError("arg1 must be Property")
    if not re.match('value_set|enum',prop.value_domain):
      raise AttributeError("Property value domain is not value_set or enum, can't add terms")
    if not prop.value_set:
      warn("Creating ValueSet object for Property "+prop.handle)
      prop.value_set = ValueSet({ "prop":prop,
                                  "_id":str(uuid4())})
      prop.value_set.handle=self.handle+prop.value_set._id[0:8]
      
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
    self.removed_entities.append(node)
    return node
      

  def rm_edge(self, edge):
    if not isinstance(edge, Edge):
      raise ArgError("arg must be an Edge object")
    if not self.contains(edge):
      warn("edge '{edge}' not contained in model '{model}'".format(edge=edge.triplet, model=model.handle))
      return
    for p in edge.props:
      try:
        k = list(edge.triplet)
        k.append(p.handle)
        del self.props[tuple(k)]
      except:
        pass
    del self.edges[edge.triplet]
    edge.src = None
    edge.dst = None
    self.removed_entities.append(edge)
    return edge


  def rm_prop(self, prop):
    if not isinstance(prop, Property):
      raise ArgError("arg must be a Property object")
    if not self.contains(prop):
      warn("prop '{prop}' not contained in model '{model}'".format(prop=prop.handle, model=model.handle))
      return
    for okey in prop.belongs:
      owner = prop.belongs[okey]
      (i,att,key) = okey
      getattr(owner,att)[key]==None
      k = [owner.handle] if isinstance(owner, Node) else list(owner.triplet)
      k.append(key)
      del self.props[tuple(k)]
    self.removed_entities.append(prop)
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


  def dget(self,refresh=False):
    if not self.drv:
      return
    if (refresh):
      ObjectMap.clear_cache()
    nodes=[]
    edges=[]
    props=[]
    with self.drv.session() as session:
      result = session.run("MATCH (n) WHERE n.model='{handle}' RETURN n".format(
        handle=self.handle))
      graph = result.graph()
      for nod in graph.nodes:
        if 'node' in nod.labels:
          n=Node(nod)
          nodes.append(n)
        elif 'relationship' in nod.labels:
          e=Edge(nod)
          edges.append(e)
        elif 'property' in nod.labels:
          p=Property(nod)
          props.append(p)
        else:
          warn("unhandled node type {lbl} encountered in model '{handle}'".format(
            lbl=rec.labels[0],
            handle=self.handle))
    if not nodes:
      warn("no nodes in db for model '{handle}'".format(handle=self.handle))
    for n in nodes:
      n.dget(True)
      self.nodes[n.handle]=n
    for e in edges:
      e.dget(True)
      if None in e.triplet:
        set_trace()
      self.edges[e.triplet] = e
    for p in props:
      p.dget(True)
      for (o, keys) in Property.object_map.get_owners(p):
        k = [o.handle] if isinstance(o,Node) else list(o.triplet)
        k.append(p.handle)
        self.props[tuple(k)]=p
    return self

  def dput(self):
    if not self.drv:
      return
    seen={}
    def do_(obj):
      if id(obj) in seen:
        return
      seen[id(obj)]=1
      if obj.dirty == 1:
        obj.dput()
      atts = [x for x in type(obj).attspec if type(obj).attspec[x]=='object']
      for att in atts:
        ent = getattr(obj,att)
        if ent:
          do_(ent)
      atts = [x for x in type(obj).attspec if type(obj).attspec[x]=='collection']
      for att in atts:
        ents = getattr(obj,att)
        if ents:
          for ent in ents:
            do_(ents[ent])
    for e in self.removed_entities:
      do_(e)
    for e in self.edges.values():
      do_(e)
    for e in self.nodes.values():
      do_(e)
    for e in self.props.values():
      do_(e)
    return
  
  
