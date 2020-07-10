import re
import sys
sys.path.extend(['.','..'])
import pytest
from bento_meta.entity import *
from bento_meta.objects import *
from pdb import set_trace

def test_object_versioning():
  Entity.versioning(True)
  assert Entity.versioning_on
  Entity.set_version_count(3)
  assert Entity.version_count==3
  Entity.set_version_count(1)
  #         r1                                                                    
  #       /   \                                                                   
  #    n1       n2                                                                
  #            /|\                                                                
  #          p1 p2 p3                
  n1=Node({"handle":"n1"})
  n2=Node({"handle":"n2"})  
  r1=Edge({"handle":"r1","src":n1,"dst":n2})
  p1=Property({"handle":"p1"})
  p2=Property({"handle":"p2"})
  p3=Property({"handle":"p3"})
  n2.props['p1']=p1
  n2.props['p2']=p2
  n2.props['p3']=p3

  assert r1.src == n1
  assert r1.dst == n2
  assert n2.props['p1'] == p1

  for e in [n1,n2,r1,p1,p2,p3]:
    assert e._from==1
    assert not e._to

  dup = n1.dup()
  assert dup != n1
  Entity.set_version_count(2) # bump version

  #         r1       r21                                                          
  #       /   \    /    \                                                         
  #    n1       n2       n21                                                      
  #            /|\        |                                                       
  #          p1 p2 p3    p21                                                      

  n21=Node({"handle":"n21"})
  r21=Edge({"handle":"r21","src":n2,"dst":n21})
  p21=Property({"handle":"p21"})
  n21.props['p21']=p21
  assert r1.dst == r21.src

  for e in [r21,n21,p21]:
    assert e._from == 2
    assert not e._to

  for e in [n1,n2,r1,p1,p2,p3]:
    assert e._from == 1

  Entity.set_version_count(3)

  #         r1       r21                                                          
  #       /   \    /    \                                                         
  #    n1       n2       n21                                                      
  #            /|\        |                                                       
  #          p1 p2 p3    p21                                                      

  n31=Node({"handle":"n31"})
  n21.delete()
  r21.dst=n31
  assert r21.dst == n31
  assert r21._prev
  assert r21._prev._next == r21
  assert r21._prev.handle == "r21"
  assert r21._prev.dst == n21

  n1.category = "blarf"
  assert n1.category == "blarf"
  assert not n1._prev.category # prev version attr still empth
  assert not n1._prev._prev # only two versions of n1
  assert r1._prev # changing n1 induced a change on r1 (owner of n1)
  assert r1.src.category == "blarf" # latest r1 src is the latest n1
  assert not r1._prev.src.category # old r1 src, old n1, has empty category attr
  assert not r1._prev._prev # only 2 versions of r1
  prev = n1._prev
  n1.model="test2" # change another attr shouldn't dup
  assert n1._prev == prev # and it didn't dup
  assert prev._next == n1 # yep

  Entity.set_version_count(4)
  #         r1       r21 --                                                       
  #       /   \    /        \                                                     
  #    n1*      n2 --       n31                                                   
  #            /|\    \      /                                                    
  #          p1 p2 p3 p41  p21                                                    

  p41=Property({"handle":"p41"})
  n2.props['p41']=p41
  assert n2._prev
  assert not 'p41' in n2._prev.props
  assert n2.props['p41'] == p41
  
if __name__ == "__main__":
  test_object_versioning()
