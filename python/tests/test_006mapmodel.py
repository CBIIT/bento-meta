import re
import sys
sys.path.extend(['.','..'])
import pytest
import pytest_docker
from neo4j import GraphDatabase
import neo4j.graph
from neo4j.exceptions import Neo4jError
from pdb import set_trace
from bento_meta.object_map import ObjectMap
from bento_meta.entity import *
from bento_meta.objects import *

def test_model(bento_neo4j):
  (b,h)=bento_neo4j
  drv = GraphDatabase.driver(b)
  assert drv
