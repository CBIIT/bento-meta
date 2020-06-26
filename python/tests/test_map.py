import re
import sys
sys.path.extend(['.','..'])
import pytest
from pdb import set_trace
from bento_meta.entity import *
from bento_meta.objects import *
from bento_meta.object_map import ObjectMap

def test_class():
  m = ObjectMap(cls=Node)
  assert isinstance(m, ObjectMap)
  assert m.cls.mapspec()["label"] == 'node'
  assert m.cls.attspec["props"] == 'collection'
  assert m.cls.attspec["_next"] == 'object'
  

  
    
