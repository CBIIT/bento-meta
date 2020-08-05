# MDB MVP Inital data loading - tests

## Concept nodes

* Every Node, Relationship, Property is linked (`has_concept`) to a Concept

        match (n:node) where not (n)-[:has_concept]->(:concept) return count(n) # returns 0
		match (n:node)-[:has_concept]->(c:concept) with count(c) as ct, id(n) as nid return distinct ct; # returns "1"
		match (n:relationship) where not (n)-[:has_concept]->(:concept) return count(n) # 0
		match (n:node)-[:has_concept]->(c:concept) with count(c) as ct, id(n) as nid return  distinct ct; # returns "1"
		match (n:property) where not (n)-[:has_concept]->(:concept) return count(n) # 0
		match (n:node)-[:has_concept]->(c:concept) with count(c) as ct, id(n) as nid return  distinct ct; # returns "1"

  * ValueSets should have concepts when they are represented by an externally defined set

        match (n:value_set) where not (n)-[:has_concept]->(:concept) return count(n)
        ### 202 value sets. None of these has an externally defined set associated with it.

* Relationships of the same handle (type) and model are linked to the same Concept node
  * This query should return no rows

	    match (r:relationship)-[:has_concept]->(c:concept) with r.handle as hdl, count(distinct c) as cct where cct > 1 return hdl,cct

* Concepts are not necessarily unique, but
  * ICDC, CTDC, Bento entities having the same subclass and handle should be linked to a single Concept - the following queries should return 1 for cct for every row.

        match (n:node) with count(n) as ct, n.handle as hdl where ct > 1 match (n:node)--(c:concept) where n.handle = hdl return hdl, ct, count(distinct c) as cct; 
        match (n:relationship) with count(n) as ct, n.handle as hdl where ct > 1 match (n:relationship)--(c:concept) where n.handle = hdl return hdl, ct, count(distinct c);
        match (n:property) with count(n) as ct, n.handle as hdl where ct > 1 match (n:property)--(c:concept) where n.handle = hdl return hdl, ct, count(distinct c);

## Term nodes

* Every Term node is linked (:represents) to a single Concept and linked (`has_origin`) to a single Origin. 

        match (t:term) where not (t)--(:origin) return count(t) # return 0
		match (t:term) where not (t)--(:concept) return count(t) # return 0
        ### returns 1 terms - NCIt (UUID) - missing in ICDC model
        match (o:origin)<-[:has_origin]-(t:term)-[:represents]->(c:concept) with count(distinct o) as oct, count(distinct c) as cct, id(t) as tid return distinct [oct,cct];
	    # return [1,1]

* Every Node, Relationship, and Property is associated with a Term via a Concept, and  entity.handle = term.value

        match (a) where 'node' in labels(a) or 'relationship' in labels(a) or 'property' in labels(a) with collect(a) as aa with aa, size(aa) as n unwind aa as a match (a)-->(:concept)<--(t:term) where t.value = a.handle return count(distinct a) =n; # return TRUE
    
   * Each such Term is linked to an Origin such that entity.model = origin.name

	    	  match (a) where 'node' in labels(a) or 'relationship' in labels(a) or 'property' in labels(a) with collect(a) as aa with aa, size(aa) as n unwind aa as a match (a)-->(:concept)<--(t:term)-->(o:origin) where o.name = a.model return count(distinct a) =n; # return TRUE

* Every Property with `value_domain` == `value_set` is linked (`has_value_set`) to a single ValueSet; no Property with `value_domain` != `value_set` is linked to a ValueSet.

		match (p:property) where p.value_domain='value_set' with p match (p) where not (p)-[:has_value_set]->(:value_set) return count(p) # return 0
	    match (p:property)-->(v:value_set) with id(p) as pid, count(v) as vct return distinct vct; # return 1
	    match (p:property) where p.value_domain <> 'value_set' with p match (p)--(v:value_set) return count(v); # return 0

## Mapped terms

* Basic test - each NCIt term should point to a concept that has another term, not NCIt, also pointing to it:

        match (t:term)-->(o:origin {name:"NCIt"}) with collect(t) as tt with size(tt) as n, tt unwind tt as t match (t)-->(c:concept)<--(u:term)-->(o:origin) where o.name <> 'NCIt' return count(distinct t) = n; # return TRUE
        ### returns FALSE because NCIt for UUID is unmapped; ICDC model needs to add the property definition for uuid.

