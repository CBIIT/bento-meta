import re
import sys
sys.path.append('..')
from bento_meta.entity import Entity

# tags attr?

class Node(Entity):
  attspec = {"handle":"simple","model":"simple",
             "concept":"object",
             "props":"collection"}
  def __init__(self, init=None):
    super().__init__(attspec=Node.attspec,init=init)

class Property(Entity):
 attspec = {"handle":"simple","model":"simple",
            "value_domain":"simple","units":"simple",
            "pattern":"simple","is_required":"simple",
            "concept":"object","value_set":"object"}
 def __init__(self, init=None):
    super().__init__(attspec=Property.attspec,init=init)


class Edge(Entity):
  attspec = {"handle":"simple","model":"simple",
             "multiplicity":"simple","is_required":"simple",
             "src":"object","dst":"object",
             "concept":"object",
             "props":"collection"}
  def __init__(self, init=None):
    super().__init__(attspec=Edge.attspec,init=init)

class Term(Entity):
  attspec={"value":"simple", "origin_id":"simple",
           "origin_definition":"simple",
           "concept":"object", "origin":"object"}
  def __init__(self, init=None):
    super().__init__(attspec=Term.attspec,init=init)

class ValueSet(Entity):
  attspec={"url":"simple",
           "prop":"object", "origin":"object",
           "terms":"collection"}
  def __init__(self, init=None):
    super().__init__(attspec=ValueSet.attspec,init=init)

class Concept(Entity):
  attspec={"terms":"collection"}
  def __init__(self, init=None):
    super().__init__(attspec=Concept.attspec,init=init)

class Origin(Entity):
  attspec={"url":"simple", "is_external":"simple"}
  def __init__(self, init=None):
    super().__init__(attspec=Origin.attspec,init=init)
  
  
