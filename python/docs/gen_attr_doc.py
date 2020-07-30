import sys
sys.path.insert(1,'..')
import os
from bento_meta.entity import Entity
from bento_meta.objects import *

gen_attr_doc_output=''
if __name__=='__main__':
  for cls in [Entity, Node, Edge, Property, Term, Concept, Origin, Tag]:
    gen_attr_doc_output += cls.attr_doc()

  with open('the_object_model.rst','r') as fidx:
    for line in fidx:
      if "_object_attribute_lists" in line:
        print(line,end="")
        print("""\

Objects and their Attributes
____________________________

""")
        print(gen_attr_doc_output,end="")
        break
      else:
        print(line,end="")


  
    
