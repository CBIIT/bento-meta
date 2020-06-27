
# need to specify the attribute types for each new subclass
#
# attspec : { <att_name> : "simple|object|collection", ... }
import re
from pdb import set_trace
from collections import UserDict
from option_merge import MergedOptions

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
    for att in type(self).attspec:
      if not att in self.__dict__:
        if self.attspec[att] == 'collection':
          self[att] = CollValue({},owner=self,owner_key=att)
        else:
          self[att] = None
          
  @classmethod
  def mergespec(cls):
    cls.attspec.update(Entity.attspec_)
    mo=MergedOptions()
    mo.update(Entity.mapspec_)
    if hasattr(cls,'mapspec_'):
      mo.update(cls.mapspec_)
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
    return self.pvt.dirty
  @property
  def removed_entities(self):
    return self.pvt.removed_entities
  @property
  def object_map(self):
    return self.pvt.object_map
  @property
  def belongs(self):
    return self.pvt.belongs
  
  def set_with_dict(self, init):
    for att in type(self).attspec:
      if att in init:
        if type(self).attspec[att] == 'collection':
          self[att] = CollValue(init[att],owner=self,owner_key=att)
        else:
          self[att] = init[att] 

  def __getattr__(self, name):
    if name in Entity.pvt_attr:
      return self.__dict__['pvt'][name]
    elif name in type(self).attspec:
      if not name in self.__dict__:
        return None
      return self.__dict__[name]
    else:
      raise AttributeError("get: attribute '{name}' neither private nor declared".format(name=name))

  def __getitem__(self, name):
    return self.__getattr__(name)

  def __setattr__(self, name, value):
    if name == 'pvt':
      self.__dict__['pvt'] = value
    elif name in Entity.pvt_attr:
      self.__dict__['pvt'][name]=value
    elif name in type(self).attspec:
      self._check_value(name,value)
      if isinstance(value, Entity):
        value.belongs[(id(self),name)] = self
      if isinstance(value, dict) and type(self).attspec[name] == 'collection':
        value = CollValue(value,owner=self,owner_key=name)
      self.__dict__[name] = value
    else:
      raise AttributeError("set: attribute '{name}' neither private nor declared".format(name=name))
  def __setitem__(self, name, value):
    self.__setattr__(name, value)
    
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
        if not (isinstance(value,(dict,CollValue))):
          raise AttributeError(
              "value for key '{att}' is not a dict or CollValue".format(att=att)
          )
      else:
        raise ArgError("unknown attribute type '{type}' for attribute '{att}' in attspec".format(type=spec,att=att) )
    except Exception:
      raise
    
  def get(self,refresh):
    if (type(self).object_map):
      pass
    else:
      pass

  def put(self,refresh):
    if (type(self).object_map):
      pass
    else:
      pass

  def rm(self,refresh):
    if (type(self).object_map):
      pass
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
    super().__init__(init)
    self.__dict__["__owner"]=owner
    self.__dict__["__owner_key"]=owner_key
    
  @property
  def owner(self):
    return self.__dict__["__owner"]
  @property
  def owner_key(self):
    return self.__dict__["__owner_key"]
    
  # def __setattr__(self, name, value):
  def __setitem__(self, name, value):
    pfx = "_{cls}".format(cls=type(self).__name__)
    if re.match(pfx,name): # private
      self.__dict__[name] = value
    if not isinstance(value, Entity):
      raise ArgError("a collection-valued attribute can only accept Entity members, not '{tipe}'s".format(tipe=type(value)))

    # when value.__belongs = x is attempted, the Entity.__setattr__ method
    # is called, but the attribute is mangled to _CollVal__belongs, not
    # _Entity__belongs .. WTH????
    value.belongs[(id(self.owner),self.owner_key,name)] = self.owner
    self.data[name]=value
    return
