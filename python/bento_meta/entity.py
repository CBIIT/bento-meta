
# need to specify the attribute types for each new subclass
#
# attspec : { <att_name> : "simple|object|collection", ... }
import re
from copy import deepcopy
from pdb import set_trace
from collections import UserDict

class ArgError(Exception):
  pass

class Entity(object):
  pvt_attr=['pvt','neoid','dirty','removed_entities','attspec',
            'mapspec','belongs']
  attspec_={"_id":"simple", "desc":"simple",
           "_next":"object", "_prev":"object",
           "_from":"simple", "_to":"simple",
           "tags":"collection"}
  attspec=attspec_
  mapspec_={
    "label":None,
    "key":"_id",
    "property": {
      "_id":"id",
      "desc":"desc",
      "_from":"_from",
      "_to":"_to"
      },
    "relationship": {
      "_next": { "rel" : ":_next>",
                 "end_cls" : set() },
      "_prev": { "rel" : ":_prev>",
                 "end_cls" : set() },
      "tags": { "rel" : ":has_tag",
                "end_cls" : {"Tag"} }
    }}
  object_map=None
  
  def __init__(self,init=None):
    if not set(type(self).attspec.values()) <= set(['simple','object','collection']):
      raise ArgError("unknown attribute type in attspec")
    # private
    self.pvt={}
    self.neoid=None
    self.dirty=1
    self.removed_entities=[]
    self.belongs = {}

    # merge to universal map
    type(self).mergespec()

    if init:
      if isinstance(init,Entity):
        self.set_with_entity(init)
      elif isinstance(init, dict):
        self.set_with_dict(init)
      elif type(init).__name__ == 'Node': # neo4j.graph.Node - but don't want to import that
        self.set_with_node(init)
    for att in type(self).attspec:
      if not att in self.__dict__:
        if self.attspec[att] == 'collection':
          setattr(self,att, CollValue({},owner=self,owner_key=att))
        else:
          setattr(self,att,None)
          
  @classmethod
  def mergespec(cls):
    cls.attspec.update(Entity.attspec_)
    mo=deepcopy(Entity.mapspec_)
    cs=cls.mapspec_
    if "label" in cs:
      mo["label"] = cs["label"]
    if "key" in cs:
      mo["key"] = cs["key"]
    if "property" in cs:
      mo["property"].update(cs["property"])
    if "relationship" in cs:
      mo["relationship"].update(cs["relationship"])    
    mo["relationship"]["_next"]["end_cls"]={cls.__name__}
    mo["relationship"]["_prev"]["end_cls"]={cls.__name__}
    cls._mapspec=mo

  @classmethod
  def mapspec(cls):
    if not hasattr(cls,'_mapspec'):
      cls.mergespec()
    return cls._mapspec

  @property
  def dirty(self):
    return self.pvt['dirty']
  @dirty.setter
  def dirty(self,value):
    self.pvt['dirty']=value

  @property
  def removed_entities(self):
    return self.pvt['removed_entities']
  @property
  def object_map(self):
    return self.pvt['object_map']
  @property
  def belongs(self):
    return self.pvt['belongs']
  def clear_removed_entities(self):
    self.pvt['removed_entities']=[]
  def set_with_dict(self, init):
    for att in type(self).attspec:
      if att in init:
        if type(self).attspec[att] == 'collection':
          setattr(self,att,CollValue(init[att],owner=self,owner_key=att))
        else:
          setattr(self,att,init[att])
  def set_with_node(self, init):
    # this unsets any attribute that is not present in the Node's properties
    for att in [a for a in type(self).attspec if type(self).attspec[a]=='simple']:
      patt = type(self).mapspec()['property'][att]
      if patt in init:
        setattr(self,att,init[patt])
      else:
        setattr(self,att,None)
    self.neoid = init.id

  def __getattribute__(self, name):
    if name in type(self).attspec:
      # declared attr, send to __getattr__ for magic
      return self.__getattr__(name)
    else:
     return object.__getattribute__(self,name)
    
  def __getattr__(self, name):
    if name in Entity.pvt_attr:
      return self.__dict__['pvt'][name]
    elif name in type(self).attspec:
      if not name in self.__dict__ or self.__dict__[name]==None:
        return None
      if type(self).attspec[name] == 'object':
        # magic - lazy getting
        if self.__dict__[name].dirty < 0:
          self.__dict__[name].dget()
      return self.__dict__[name]
    else:
      raise AttributeError("get: attribute '{name}' neither private nor declared for subclass {cls}".format(name=name,cls=type(self).__name__))

  def __setattr__(self, name, value):
    if name == 'pvt':
      self.__dict__['pvt'] = value
    elif name in Entity.pvt_attr:
      self.__dict__['pvt'][name]=value
    elif name in type(self).attspec:
      self._check_value(name,value)
      if type(self).attspec[name] == 'object':
        oldval = self.__dict__.get(name)
        if oldval:
          del oldval.belongs[(id(self),name)]
          self.removed_entities.append( (name, oldval) )
        if isinstance(value, Entity):
          value.belongs[(id(self),name)] = self
      elif type(self).attspec[name] == 'collection':
        if isinstance(value, dict):
          value = CollValue(value,owner=self,owner_key=name)
        if isinstance(value,list): # convert list of objs to CollValue
          d={}
          for v in value:
            d[ getattr(v,type(v).mapspec()["key"]) ] = v
          value = CollValue(d,owner=self,owner_key=name)
      self.dirty=1
      self.__dict__[name] = value
    else:
      raise AttributeError("set: attribute '{name}' neither private nor declared for subclass {cls}".format(name=name, cls=type(self).__name__))
    
  def __delattr__(self, name):
    del self.__dict__[name]

  def _check_init(self,init):
    for att in type(self).attspec:
      if init[att]:
        self._check_value(att,init[att])
                               
  def _check_value(self,att,value):
    spec = type(self).attspec[att]
    try:
      if spec == 'simple':
        if not (isinstance(value,int) or
                isinstance(value,str) or
                isinstance(value,float) or
                isinstance(value,bool) or
                value == None):
          raise ArgError(
            "value for key '{att}' is not a simple scalar".format(att=att)
          )
      elif spec == 'object':
        if not (isinstance(value,Entity) or
                value == None):
          raise ArgError(
            "value for key '{att}' is not an Entity subclass".format(att=att)
            )
      elif spec == 'collection':
        if not (isinstance(value,(dict,list,CollValue))):
          raise AttributeError(
              "value for key '{att}' is not a dict,list, or CollValue".format(att=att)
          )
      else:
        raise ArgError("unknown attribute type '{type}' for attribute '{att}' in attspec".format(type=spec,att=att) )
    except Exception:
      raise
    
  def dget(self,refresh=False):
    if (type(self).object_map):
      return type(self).object_map.get(self,refresh)
    else:
      pass

  def dput(self):
    if (type(self).object_map):
      return type(self).object_map.put(self)
    else:
      pass

  def rm(self,force):
    if (type(self).object_map):
      return type(self).object_map.rm(self,force)
    else:
      pass

class CollValue(UserDict):
  """A UserDict for housing Entity collection attributes

  A UserDict that contains a hook for recording the Entity that
  own the value that is being set. The value is marked as belonging
  to the containing object, not this collection object.
  Also protects against adding arbitrarily typed elements to the
  collection (throws unless a value to set is an Entity)

  :param owner: Entity object of which this collection is an attribute
  :param owner_key: the attribute name of this collection on the owner

  """
  def __init__(self,init=None,*,owner,owner_key):
    self.__dict__["__owner"]=owner
    self.__dict__["__owner_key"]=owner_key
    super().__init__(init)
    
  @property
  def owner(self):
    return self.__dict__["__owner"]
  @property
  def owner_key(self):
    return self.__dict__["__owner_key"]
    
  # def __setattr__(self, name, value):
  def __setitem__(self, name, value):
    # pfx = "_{cls}".format(cls=type(self).__name__)
    # if re.match(pfx,name): # private
    #   self.__dict__[name] = value
    if not isinstance(value, Entity):
      raise ArgError("a collection-valued attribute can only accept Entity members, not '{tipe}'s".format(tipe=type(value)))
    if name in self:
      oldval = self.data.get(name)
      if oldval:
        del oldval.belongs[(id(self.owner),self.owner_key,name)]
        self.owner.removed_entities.append( (self.owner_key, oldval) )
    value.belongs[(id(self.owner),self.owner_key,name)] = self.owner
    # smudge the owner
    self.owner.dirty = 1
    self.data[name]=value
    return
  def __getitem__(self, name):
    if not name in self.data:
      return
    if self.data[name].dirty < 0:
       self.data[name].dget()
    return self.data[name]
  
