
# need to specify the attribute types for each new subclass
#
# attspec : { <att_name> : "simple|object|collection", ... }
import re

class ArgError(Exception):
  pass

class Entity(object):
  def __init__(self,attspec=None,init=None):
    if not attspec:
      raise ArgError("attribute spec required as arg attspec");
    if not set(attspec.values()) <= set(['simple','object','collection']):
      raise ArgError("unknown attribute type in attspec")
    # universal attributes
    attspec.update( {"id":"simple", "desc":"simple",
                     "_next":"object", "_prev":"object",
                     "_from":"simple", "_to":"simple"} )
    # private
    self.__neoid=1
    self.__dirty=1
    self.__removed_entities=[]
    self.__attspec=attspec
    self.__object_map=None
    if init:
      if isinstance(init,Entity):
        self.set_with_entity(init)
      elif isinstance(init, dict):
        self.set_with_dict(init)
    for att in self.__attspec:
      if not att in self.__dict__:
        if self.__attspec[att] == 'collection':
          self[att] = {}
        else:
          self[att] = None
      
      
  def set_with_dict(self, init):
    for att in self.__attspec:
      if att in init:
        self[att] = init[att] 

  def __getattr__(self, name):
    if re.match('__',name):
      cls = re.match(".*'([^']+)'",str(type(self))).group(1)
      cls = cls.split('.')[-1]
      name = "_{cls}{name}".format(cls=cls,name=name)
    elif (not name in self.__attspec):
      raise AttributeError("attribute '{name}' neither private nor declared".format(name=name))
    return self.__dict__[name]
  def __getitem__(self, name):
    return self.__getattr__(name)

  def __setattr__(self, name, value):
    if re.match('^(?:_.*)?__',name): # private
      self.__dict__[name] = value
    elif  name in self.__attspec:
      self._check_value(name,value)
      self.__dict__[name] = value
    else:
      raise AttributeError("attribute '{name}' neither private nor declared".format(name=name))
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
        if not (isinstance(value,dict)):
          raise AttributeError(
              "value for key '{att}' is not a dict of Entity subclasses ".format(att=att)
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

