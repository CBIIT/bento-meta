import re
import sys
sys.path.append('.')
import pytest
from pdb import set_trace

from bento_meta.entity import Entity, CollValue, ArgError

class TestEntity(Entity):
  attspec = {"a":"simple","b":"object","c":"collection"}
  mapspec_ = {"label":"test","relationship":{"b":{ "rel":":has_object>", "end_cls":"entity"},"c":{ "rel":":has_object>", "end_cls":"entity"}},"property":{"a":"a"}}
  def __init__(self,init=None):
    super().__init__(init)

def test_create_entity():
  assert Entity()

def test_entity_attrs():
  assert TestEntity.attspec == {"a":"simple","b":"object","c":"collection"}
  ent = TestEntity()
  val = TestEntity()
  ent.a = 1
  ent.b = val
  assert ent.a==1
  assert ent.b==val
  with pytest.raises(AttributeError, match="attribute 'frelb' neither"):
    ent.frelb = 42
  with pytest.raises(AttributeError,match="attribute 'frelb' neither"):
    f = ent.frelb
  with pytest.raises(ArgError,match=".*is not an Entity subclass"):
    ent.b={"plain":"dict"}
    
def test_entity_init():
  val = TestEntity({"a":10})
  col = {}
  good = {"a":1,"b":val,"c":col,"d":"ignored"}
  bad = {"a":val,"b":val,"c":col,"d":"ignored"}
  ent = TestEntity(init=good)
  with pytest.raises(ArgError,match=".*is not a simple scalar"):
    TestEntity(init=bad)

def test_entity_belongs():
  e = TestEntity()
  ee = TestEntity()
  cc = CollValue({},owner=e,owner_key='c')
  e.c=cc
  cc['k']=ee
  assert e.c == cc
  assert e.c['k'] == ee
  
