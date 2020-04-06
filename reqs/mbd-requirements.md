# MDB Interface Requirements

MDB is the store for CTOS data models and terms. It needs an SME-friendly interface for performing daily terminology and model tasks.

Listing use cases and requirements here for the database and its interface.

## Use Cases

* I need to update the MDB with model changes made in YAML, so I can keep the MDB concordant with the offical YAML version.

* I need to be able to obtain all the attributes (cardinality,  required, data type, etc) that can be expressed in MDF from the MBD, so I can use the MBD to drive downstream applications and processes.

* I need to add acceptable values to a property value domain, so I can register those additions officially

* I need to see all acceptable values for a property value domain, so  I can determine whether to add a new value.

* I need to search terms across all models, so I can determine if a concept already exists in the MDB that can be reused for a new model.
  * Initially - full text search : e.g. "*disease" - 
  * everything has a (t:term) node connected to it. (thing)-->(concept)<--(term)
    match (t:term) where t.value =~ '.*disease' return t;
    match (t:term) where t.value =~ '.*disease' and (n:node)-->(:concept)<--(t) return n;
    match (t:term) where t.value =~ '.*disease' and (p:property)<--(v:value_set)<--(t) return p.handle, v.name;

    <model>.<property.handle>.valueset 
    (t:term)-->(o:origin)
    (v:value_set)-->(o:origin) ?
   (v:value_set)-->(c:concept)-->(o:origin) ?

* I need to be able to find the external source of a _value set_ of terms, so I can ...

  * how to search concepts that are related by meaning? 

* I need to tag a set of terms according to a given search, to be able to find and work with them in a single step subsequently.

* I need to have automatic backups and a simple restore facility, to enable recovery after database corruption.

## Requirements

* Specify how to handle Concepts for any new Term
  * Create new Concept
  * Link to existing Concept - specific a unique path to the desired concept
    * For example, specify an existing Term node already linked to the desired Concept
    * Specify an NCIt concept code - find existing Term with this code and link to corresponding concept
  * Return the uuid for the concept added/linked

* Loader module for [MDF](https://github.com/CBIIT/bento-mdf) YAML
  * Load a new model from YAML
  * Detect changes between a YAML representation and current MDB model
  * Warn about non-backward compatible (non-additive) changes
  * Modify model structure based on changes - Nodes, Relationships, Properties, Value Sets
  * Create (or link) necessary Concept and Term nodes and links
  * Have dry-run mode to see changes that would be made, but don't execute changes
  * Have a way to roll back changes

* Module to C_UD value sets
  * input a JSON spec of a term and the property it belongs to
  * add, delete, update term as a member of the value set
  * Create or link Concepts as necessary

* Module to create MDF YAML from MDB representation of a model

# Considerations

MDB Loading can be 
* Synchronous/RT - i.e., hit the Neo4j endpoint with each change
* Asynchronous/Batch - i.e., create a dump of cypher statments, load
  all at once
  * Submit in a transaction so that it is atomic (will all rollback if
    a failure)
