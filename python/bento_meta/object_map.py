import re
import sys
sys.path.append('..')
from bento_meta.entity import *
from bento_meta.objects import *
from neo4j import GraphDatabase
from warnings import warn


class ObjectMap(object):
  cache = {}
  def __init__(self,*,cls=None,drv=None):
    if not cls:
      raise ArgError("arg cls= is required")
    self.cls = cls
    self.drv=drv
    self.maps={}
  @classmethod
  def cls_by_label(cls,lbl):
    if not hasattr(cls,_clsxlbl):
      cls._clsxlbl={}
      for o in (Node,Edge,Property,ValueSet,Term,Concept,Origin,Tag):
        clx._clsxlbl[o.mapspec()["label"]]=o
    return cls._clsxlbl[lbl]
                     
  @classmethod
  def _quote_val(cls,value,single=None): # double quote unless single is set
    if value == None:
      return
    if isinstance(value, (int, float)):
      return value # no quote
    else:
      if single:
        return "'{val}'".format(val=value) # quote
      else:
        return "\"{val}\"".format(val=value) # quote

  def get(self,obj, refresh=False):
    if not self.drv:
      raise ArgError("get() requires Neo4j driver instance")
    if not (obj.neoid in ObjectMap.cache) or refresh or ObjectMap.cache[obj.neoid].dirty < 0:
      return obj
    with self.drv.session() as session:
      result = session.run( self.get_q(obj) )
      rec = result.single()
      if not rec:
        raise RuntimeError("object with id {neoid} not found in db".format(neoid=obj.neoid))
    if not obj.neoid in ObjectMap.cache:
      ObjectMap.cache[obj.neoid] = obj
    with self.drv.session() as session:
      for att in self.cls.mapspec()["relationship"]:
        result = session.run( self.get_att_q(obj, att) )
        values={}
        first_val=None
        for rec in result:
          o = ObjectMap.cache[r['a'].id]
          if o:
            if not first_val:
              first_val=o
            values[o['handle'] if hasattr(o,'handle') else o['value']]=o
          else:
            c=None
            for l in r['a'].labels:
              c = ObjectMap.cls_by_label(l)
              if c:
                break
            if not c:
              raise RuntimeError('node labels {lbls} have no associated class in the object model'.format(
                lbls=r['a'].labels))
            o=c(r['a'])
            o.dirty=-1
            ObjectMap.cache[o.neoid]=o
            if not first_val:
              first_val=o
            values[o['handle'] if hasattr(o,'handle') else o['value']]=o
        if (self.cls.attspec[att]=='object' and len(values) > 1):
          warn('expected one node for attribute {att} on class {cls}, but got {n}; using first one'.format(
            att=att,
            cls=self.cls.__name__,
            n=len(values)))
        if (self.cls.attspec[att]=='object'):
          obj[att]=first_val
        elif (self.cls.attspec[att]=='collection'):
          obj[att]=values
        else:
          raise RuntimeError("attribute '{att}' has unknown attribute type '{atype}'".format(
            att=att,
            atype=self.cls.attspec[att]))
    obj.clear_removed_entities()
    obj.dirty=0
    return obj

  
  def put(self,obj):
    if not self.drv:
      raise ArgError("put() requires Neo4j driver instance")
      pass
    with self.drv.session() as session:
      result=None
      with session.begin_transaction() as tx:
        for qry in self.put_q(obj):
          result = tx.run(qry)
        obj.neoid = result.single().value('id(n)')
        if obj.neoid==None:
          raise RuntimeError("no neo4j id retrived on put for obj '{name}'".format(
            name=obj['handle'] if hasattr(obj,'handle') else obj['value']))
        for att in self.cls.mapspec()["relationship"]:
          values = obj[att]
          if not values:
            continue
          if not isinstance(values, CollValue):
            values = {'val':values}
          for val in values.values():
            if val.neoid != None:
              continue
            # put val as a node
            for qry in self.put_q(val):
              result = tx.run(qry)
            val.neoid = result.single().value('id(n)')
            if val.neoid == None:
              raise RuntimeError("no neo4j id retrived on put for obj '{name}'".format(
                name=val['handle'] if hasattr(val,'handle') else val['value']))
            val.dirty=1
            ObjectMap.cache[val.neoid]=val
          for qry in self.put_attr_q(obj, att, values.values()):
            tx.run(qry)
          # drop removed entities here
          while obj.removed_entities:
            ent = obj.removed_entities.pop()
            self.drop(obj,*ent,tx)
    ObjectMap.cache[obj.neoid] = obj
    obj.dirty=0
    return obj
        
  def rm(self,obj,force=False):
    if not self.drv:
      raise ArgError("rm() requires Neo4j driver instance")
    if obj.neoid == None:
        raise ArgError("object must be mapped (i.e., obj.neoid must be set)")
    with self.drv.session() as session:
      result = session.run( self.rm_q(obj,force) )
      n_id = result.single().value()
      if n_id == None:
        warn("rm() - corresponding db node not found")
      return n_id

  def add(self,obj,att,tgt):
    if not self.drv:
      raise ArgError("rm() requires Neo4j driver instance")
    with self.drv.session() as session:
      result = self.put_attr_q( obj, att, tgt)
      tgt_id = result.single().value()
      if tgt_id == None:
        warn("add() - corresponding db node not found")
      return tgt_id
      
    
  def drop(self, obj, att, tgt, tx):
    if not self.drv:
      raise ArgError("rm() requires Neo4j driver instance")
    if (tx):
      result = tx.run(self.rm_att_q(obj, att, tgt))
      tgt_id = result.single().value()
      if tgt_id == None:
        warn("drop() - corresponding target db node not found")
      return tgt_id
    else:
      with self.drv.session() as session:
        result = session.run(self.rm_att_q(obj, att, tgt))
        tgt_id = result.single().value()
        if tgt_id == None:
          warn("drop() - corresponding target db node not found")
          return tgt_id

  

  def get_q(self, obj):
    if not isinstance(obj, self.cls):
      raise ArgError("arg1 must be object of class {cls}".format(cls=self.cls.__name__))
    if obj.neoid == None:
      raise ArgError("object must be mapped (i.e., obj.neoid must be set)")
    return "MATCH (n:{lbl}) WHERE id(n)={neoid} RETURN n,id(n)".format(
        lbl=self.cls.mapspec()["label"], neoid=obj.neoid)

  def get_attr_q(self, obj, att):
    if not isinstance(obj, self.cls):
      raise ArgError("arg1 must be object of class {cls}".format(cls=self.cls.__name__))
    if obj.neoid==None:
      return ''
    label = self.cls.mapspec()["label"]
    if att in self.cls.mapspec()["property"]:
      pr = self.cls.mapspec()["property"][att]
      return "MATCH (n:{lbl}) WHERE id(n)={neoid} RETURN n.{pr}".format(
        lbl=label,
        neoid=obj.neoid,
        pr=pr)
    elif att in self.cls.mapspec()["relationship"]:
      spec = self.cls.mapspec()["relationship"][att]
      end_cls = spec['end_cls']
      if isinstance(end_cls,str):
        end_cls = {end_cls}
      end_lbls = [ eval(x).mapspec()["label"] for x in end_cls]
      rel = re.sub('^([^:]?)(:[a-zA-Z0-9_]+)(.*)$',r'\1-[\2]-\3', spec['rel'])
      if len(end_lbls) == 1:
        qry = "MATCH (n:{llbl}){rel}(a:{rlbl}) WHERE id(n)={neoid} RETURN a".format(
          neoid=obj.neoid,
          llbl=label,
          rel=rel,
          rlbl=end_lbls[0])
        if self.cls.attspec[att] == 'object':
          qry += " LIMIT 1"
        return qry
      else: # multiple end classes possible
        cond=[]
        for l in end_lbls:
          cond.append("'{lbl}' IN labels(a)".format(lbl=l))
        cond = ' OR '.join(cond)
        return "MATCH (n:{lbl}){rel}(a) WHERE id(n)={neoid} AND ({cond}) RETURN a".format(
          lbl=label,
          rel=rel,
          neoid=obj.neoid,
          cond=cond)
    else:
      raise ArgError("'{att}' is not a registered attribute for class '{cls}'".format(
        att=att,
        cls=self.cls.__name__))
          
  def get_owners_q(self, obj):
    if not isinstance(obj, self.cls):
      raise ArgError("arg1 must be object of class {cls}".format(cls=self.cls.__name__))
    if obj.neoid==None:
      raise ArgError("object must be mapped (i.e., obj.neoid must be set)")
    label = self.cls.mapspec()["label"]
    return "MATCH (n:{lbl})<--(a) WHERE id(n)={neoid} RETURN TYPE(r), a".format(
      neoid=obj.neoid,
      llbl=label)

  def put_q(self, obj):
    if not isinstance(obj, self.cls):
      raise ArgError("arg1 must be object of class {cls}".format(cls=self.cls.__name__))
    props = {}
    null_props = []
    for pr in self.cls.mapspec()["property"]:
      if obj[pr]==None:
        null_props.append(self.cls.mapspec()["property"][pr])
      else:
        props[self.cls.mapspec()["property"][pr]]=obj[pr]
    stmts=[]
    if obj.neoid != None:
      set_clause=[]
      for pr in props:
        set_clause.append("n.{pr}={val}".format(
          pr=pr,
          val=ObjectMap._quote_val(props[pr])))
      set_clause = "SET "+','.join(set_clause)
      stmts.append(
        "MATCH (n:{lbl}) WHERE id(n)={neoid} {set_clause} RETURN n,id(n)".format(
          lbl=self.cls.mapspec()["label"],
          neoid=obj.neoid,
          set_clause=set_clause))
      for pr in null_props:
        stmts.append(
          "MATCH (n:{lbl}) WHERE id(n)={neoid} REMOVE n.{pr} RETURN n,id(n)".format(
            lbl=self.cls.mapspec()["label"],
            neoid=obj.neoid,
            pr=pr))
      return stmts
    else:
      spec=[]
      for pr in props:
        spec.append("{pr}:{val}".format(
          pr=pr,
          val=ObjectMap._quote_val(props[pr])))
      spec=','.join(spec)
      return "CREATE (n:%s {%s}) RETURN n,id(n)" % (self.cls.mapspec()["label"],spec)
        
  def put_attr_q(self,obj,att,values):
    if not isinstance(obj, self.cls):
      raise ArgError("arg1 must be object of class {cls}".format(cls=self.cls.__name__))
    if obj.neoid == None:
      raise ArgError("object must be mapped (i.e., obj.neoid must be set)")
    if not isinstance(values, list):
      raise ArgError("'values' must be a list of values suitable for the attribute")
    if att in self.cls.mapspec()['property']:
      return "MATCH (n:{lbl}) WHERE id(n)={neoid} SET {pr}={val} RETURN id(n)".format(
        lbl=self.cls.mapspec()["label"],
        neoid=obj.neoid,
        pr=self.cls.mapspec()['property'][att],
        val=ObjectMap._quote_val(values[0]))
    elif att in self.cls.mapspec()['relationship']:
      if not self._check_values_list(att,values):
        raise ArgError("'values' must be a list of mapped Entity objects of the appropriate subclass for attribute '{att}'".format(att=att))
      stmts=[]
      spec = self.cls.mapspec()["relationship"][att]
      end_cls = spec['end_cls']
      if isinstance(end_cls,str):
        end_cls = {end_cls}
      end_lbls = [ eval(x).mapspec()["label"] for x in end_cls]      
      rel = re.sub('^([^:]?)(:[a-zA-Z0-9_]+)(.*)$',r'\1-[\2]-\3', spec['rel'])
      cond=[]
      for l in end_lbls:
        cond.append("'{lbl}' IN labels(a)".format(lbl=l))
      cond = ' OR '.join(cond)
      for avalue in values:
        if len(end_lbls) == 1:
          stmts.append(
            "MATCH (n:{lbl}),(a:{albl}) WHERE id(n)={neoid} AND id(a)={aneoid} MERGE (n){rel}(a) RETURN id(a)".format(
              lbl=self.cls.mapspec()["label"],
              albl=end_lbls[0],
              neoid=obj.neoid,
              aneoid=avalue.neoid,
              rel=rel))
        else:
          stmts.append(
            "MATCH (n:{lbl}),(a) WHERE id(n)={neoid} AND id(a)={aneoid} AND ({cond}) MERGE (n){rel}(a) RETURN id(a)".format(
              lbl=self.cls.mapspec()["label"],
              cond=cond,
              neoid=obj.neoid,
              aneoid=avalue.neoid,
              rel=rel))
      return stmts

    else:
      raise ArgError("'{att}' is not a registered attribute for class '{cls}'".format(
        att=att,
        cls=self.cls.__name__))

  def rm_q(self,obj,detach=False):
    if not isinstance(obj, self.cls):
      raise ArgError("arg1 must be object of class {cls}".format(cls=self.cls.__name__))
    if obj.neoid == None:
      raise ArgError("object must be mapped (i.e., obj.neoid must be set)")
    dlt = "DETACH DELETE n" if detach else "DELETE n"
    qry = "MATCH (n:{lbl}) WHERE id(n)={neoid} ".format(
      lbl=self.cls.mapspec()["label"],
      neoid=obj.neoid)
    return qry+dlt
    pass
  
  def rm_att_q(self,obj,att,values=None):
    if not isinstance(obj, self.cls):
      raise ArgError("arg1 must be object of class {cls}".format(cls=self.cls.__name__))
    if obj.neoid == None:
      raise ArgError("object must be mapped (i.e., obj.neoid must be set)")
    if values and not isinstance(values, list):
      values = [values]
    if att in self.cls.mapspec()["property"]:
      return "MATCH (n:{lbl}) WHERE id(n)={neoid} REMOVE n.{att}".format(
        lbl=self.cls.mapspec()["label"],
        neoid=obj.neoid,
        att=att)
    elif att in self.cls.mapspec()["relationship"]:
      many = self.cls.attspec[att]=='collection'
      spec = self.cls.mapspec()["relationship"][att]
      end_cls = spec['end_cls']
      if isinstance(end_cls,str):
        end_cls = {end_cls}
      end_lbls = [ eval(x).mapspec()["label"] for x in end_cls]      
      cond=[]
      for l in end_lbls:
        cond.append("'{lbl}' IN labels(a)".format(lbl=l))
      cond = ' OR '.join(cond)
      rel = re.sub('^([^:]?)(:[a-zA-Z0-9_]+)(.*)$',r'\1-[r\2]-\3', spec['rel'])
      if values[0]==':all':
        if len(end_lbls)==1:
          return "MATCH (n:{lbl}){rel}(a) WHERE id(n)={neoid} DELETE r".format(
            lbl=self.cls.mapspec()["label"],
            albl=end_lbls[0],
            rel=rel,
            neoid=obj.neoid)
        else:
          return "MATCH (n:{lbl}){rel}(a) WHERE id(n)={neoid} AND ({cond}) DELETE r".format(
            lbl=self.cls.mapspec()["label"],
            cond=cond,
            neoid=obj.neoid,
              rel=rel)
      else:
        stmts=[]
        if not self._check_values_list(att,values):
          raise ArgError("'values' must be a list of mapped Entity objects of the appropriate subclass for attribute '{att}'".format(att=att))
        for val in values:
          qry=''
          if len(end_lbls)==1:
            qry = "MATCH (n:{lbl}){rel}(a:{albl}) WHERE id(n)={neoid} AND id(a)={aneoid} DELETE r".format(
              lbl=self.cls.mapspec()["label"],
              albl=end_lbls[0],
              neoid=obj.neoid,
              aneoid=val.neoid,
              rel=rel)
          else:
            qry = "MATCH (n:{lbl}){rel}(a) WHERE id(n)={neoid} AND id(a)={aneoid} AND ({cond}) DELETE r".format(
              lbl=self.cls.mapspec()["label"],
              albl=end_lbls[0],
              neoid=obj.neoid,
              cond=cond,
              rel=rel)
          stmts.append(qry)
        return stmts    
    else:
      raise ArgError("'{att}' is not a registered attribute for class '{cls}'".format(
        att=att,
        cls=self.cls.__name__))

  def _check_values_list(self,att,values):
    chk = [ not x.neoid for x in values ]
    if True in chk:
      return False
    end_cls = self.cls.mapspec()['relationship'][att]['end_cls']
    if isinstance(end_cls,str):
      end_cls = {end_cls}
    cls_set = tuple([ eval(x) for x in end_cls ])
    chk = [ isinstance(x, cls_set) for x in values ]
    if False in chk:
      return False
    return True
  
