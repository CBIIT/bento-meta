import sys
sys.path.append('..')
import os
from bento_meta.entity import Entity
from bento_meta.objects import *

gen_attr_doc_output=''
if __name__=='__main__':
  for cls in [Entity, Node, Edge, Property, Term, Concept, Origin, Tag]:
    gen_attr_doc_output += cls.attr_doc()

  with open('index.rst','r') as fidx:
    for line in fidx:
      if "gen_attr_doc_output" in line:
        print(gen_attr_doc_output,end="")
      else:
        print(line,end="")


  
    
