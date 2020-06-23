import re
import sys
sys.path.append('.')
import pytest

from bento_meta.entity import Entity, CollValue, ArgError

def test_create_entity():
  assert Entity(attspec={"a":"simple","b":"object","c":"collection"})
  with pytest.raises(ArgError, match="^attribute spec required"):
    Entity()
  with pytest.raises(ArgError, match="^unknown attribute type"):
    Entity(attspec={"a":"frelb"})

def test_entity_attrs():
  attspec={"a":"simple","b":"object","c":"collection"}
  ent = Entity(attspec=attspec)
  val = Entity(attspec=attspec)
  assert ent.__attspec == attspec
  ent.a = 1
  ent['a'] = 1
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
  attspec={"a":"simple","b":"object","c":"collection"}
  val = Entity(attspec=attspec)
  col = {}
  good = {"a":1,"b":val,"c":col,"d":"ignored"}
  bad = {"a":val,"b":val,"c":col,"d":"ignored"}
  ent = Entity(attspec=attspec, init=good)
  with pytest.raises(ArgError,match=".*is not a simple scalar"):
    Entity(attspec=attspec,init=bad)

def test_entity_belongs():
  e = Entity({'C':'collection'})
  ee = Entity({'a':'simple'})
  cc = CollValue({},owner=e,owner_key='C')
  e['C']=cc
  cc['k']=ee
  assert e['C'] == cc
  assert e['C']['k'] == ee
  
