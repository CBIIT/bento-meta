
# need to specify the attribute types for each new subclass
#
# attspec : { <att_name> : "simple|object|collection", ... }
import re
from pdb import set_trace
from collections import UserDict

class ArgError(Exception):
  pass

class Entity(object):
  def __init__(self,attspec=None,init=None):
    if not attspec:
      raise ArgError("attribute spec required as arg attspec");
    if not set(attspec.values()) <= set(['simple','object','collection']):
      raise ArgError("unknown attribute type in attspec")
    # universal attributes
    attspec.update( {"_id":"simple", "desc":"simple",
                     "_next":"object", "_prev":"object",
                     "_from":"simple", "_to":"simple"} )
    # private
    self.__neoid=1
    self.__dirty=1
    self.__removed_entities=[]
    self.__attspec=attspec
    self.__object_map=None
    self.__belongs = {}
    if init:
      if isinstance(init,Entity):
        self.set_with_entity(init)
      elif isinstance(init, dict):
        self.set_with_dict(init)
    for att in self.__attspec:
      if not att in self.__dict__:
        if self.__attspec[att] == 'collection':
          self[att] = CollValue({},owner=self,owner_key=att)
        else:
          self[att] = None
      
  def set_with_dict(self, init):
    for att in self.__attspec:
      if att in init:
        if self.__attspec[att] == 'collection':
          self[att] = CollValue(init[att],owner=self,owner_key=att)
        else:
          self[att] = init[att] 

  def __getattr__(self, name):
    pfx = "_{cls}".format(cls=type(self).__name__)
    if re.match(pfx+'|_Entity',name): #private
      return self.__dict__[name]
    elif re.match('__',name): #private
      return self.__dict__["{pfx}{name}".format(pfx=pfx,name=name)]
    elif (not name in self.__attspec):
      raise AttributeError("get: attribute '{name}' neither private nor declared".format(name=name))
    return self.__dict__[name]
  def __getitem__(self, name):
    return self.__getattr__(name)

  def __setattr__(self, name, value):
    pfx = "_{cls}|_Entity".format(cls=type(self).__name__)
    if re.match(pfx,name): # private
      self.__dict__[name] = value
    elif  name in self.__attspec:
      self._check_value(name,value)
      if isinstance(value, Entity):
        value.__belongs[(id(self),name)] = self
      if isinstance(value, dict) and self.__attspec[name] == 'collection':
        value = CollValue(value,owner=self,owner_key=name)
      self.__dict__[name] = value
    else:
      raise AttributeError("set: attribute '{name}' neither private nor declared".format(name=name))
  def __setitem__(self, name, value):
    self.__setattr__(name, value)
    
  def __delattr__(self, name):
    if re.match('__',name):
      cls = re.match(".*'([^']+)'",str(type(self))).group(1)
      cls = cls.split('.')[-1]
      name = "_{cls}{name}".format(cls=cls,name=name)
    del self.__dict__[name]

  def _check_init(self,init):
    for att in self.__attspec:
      if init[att]:
        self._check_value(att,init[att])
                               
  def _check_value(self,att,value):
    spec = self.__attspec[att]
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
    if (self.__object_map):
      pass
    else:
      pass

  def put(self,refresh):
    if (self.__object_map):
      pass
    else:
      pass

  def rm(self,refresh):
    if (self.__object_map):
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
    # _Entity__belongs .. WTF????
    value['_Entity__belongs'][(id(self.owner),self.owner_key,name)] = self.owner
    self.data[name]=value
    return
