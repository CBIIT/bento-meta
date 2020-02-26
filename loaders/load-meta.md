# Working notes for loading the MDB

## Load MDB with MDF 

Create local Origin node with Origin.name = <model handle>.

If multiple models have `case` node (for example), each model will have its own instance of a Node with Node.handle='case'. The equivalence of meaning among such Nodes will be represented by links from each instance to a single Concept node.
(so a unique key for Nodes, Properties, Relationships would be (n.model, n.handle) - not just n.handle)

Terms from different origins may have the same value (string or data physical representation). The unique key for Terms is (origin_id) plus Origin.name

Create model representation from MDF (a 'model instance')

For each instance node (inode)
- create Node node, set handle to inode name, set model to model handle  (ICDC, CTDC...)
- if no Concept node connected to this Node, create Concept node, new uuid for Concept.id, link Node to Concept with has\_concept
  - create Term node with Term.value = Node.handle, link to Origin[name=local] with has_origin, link to Concept with represents

For each instance relationship (irel) and  Src/Dst node pair
- create Relationship node, set handle to irel name, set model to model handle
- if no Concept node connected to this Relationship, create Concept node, new uuid for Concept.id, link Relationship to Concept with has\_concept - connect all relationships of the same type to the same concept node - although the Src+Dst pair may be different
   - this can be altered if the tuple (type,src,dst) have different semantics depending on the src+dst pair
  - create Term node with Term.value = Relationship.handle, link to Origin[name=local] with has_origin, link to Concept with represents
  - link Relationship to Node[handle=Src] with has\_src
  - link Relationship to Node[handle=Dst] with has\_dst
  - link Node[handle=Src] to Node[handle=Dst] with a relationship with
    type = \_<Relationship.handle> and property of model = <model handle>


For each inode property (iprop)
- create Property node, set handle to iprop name, set model to model handle
- create has_property from inode or irel to iprop
- if no Concept node connected to this Property, create Concept node, new uuid for Concept.id, link Property to Concept with has\_concept
  - create Term node with Term.value = Property.handle, link to Origin[name=local] with has_origin, link to Concept with represents

For each instance propdefn:
- set Property node props from propdef attributes
- if propdef.type is enum - create Value\_set node and link to Property with has\_value\_set
  - for each enum value - create Term, set Term.value to enum value, 
  - create Concept node, new uuid for Concept.id, link Term to Concept with has\_concept

Load mappings from models to external origins/authorities:

This is a process of creating Terms linked to new Origin, and linking those Terms to Concepts.

The mappings are generally provided in the form:
         
    local term -> external term

So adding these to the metamodel goes like:

- merge Origin node for external authority
- create new Term node, set Term.value=<external term>, Term.origin\_id=<external code>, 
   (Term.origin\_version=<external version>?)
- link new Term to Origin node with has\_origin
- find local Term node by Term.value, find linked Concept 
- link new Term to this Concept by represents

`
    match (o:origin), (c:concept) 
    where origin.name = <external origin> and (c)<--(t:Term) and t.value = <local term>
    merge (o)<-[:has_origin]-(t:term {value:<external term>, origin_id:<external code>})-[:represents]->(c)
`

Curation is about deciding whether which existing Concept a Term should link to, or if a new Concept is needed.
- Concepts are implicitly defined by the Terms that are linked to them - they need to remain abstract aggregating points

Cleaning up after loading multiple models
- are there duplicate terms => identical in value (and semantics)?
   - squish to a single term by moving link endpts from a redundant term and attaching them to the single term
- are there duplicate concepts => identical terms pointing to different concepts?
   - squish to a single concept by moving link endpts from a redudant concept and attaching them to the single concept

## Example Cypher queries

Query: what is the enumerated value domain for a property?

    match (p:property {handle:<localname>})-->(v:value_set)-[:has_term]->(t:term)
    return collect(t.value) as value_domain

Query: is blerf a valid value for property glarb?

    match (p:property {handle:"glarb"})-->(:value_set)-->(t:term)
    with collect(t.value) as value_domain
    return case when "blerf" in value_domain then true else false

Query: what are the known synonyms for "frelb"

    match (t:term) where t.value = "frelb"
    with t
    match (t)-[:represents]->(c:concept)<-[:represents]-(s:term)
    return c.id, collect(s.value) group by c.id


## Semantics for Relationships

In the property graph, a relationship (specification) is characterized by its type, source node (label), and destination node (label). 

Pulling a model in MDF into the metamodel, we assign all relationships of a given type to the same concept. Mapping to another model, like BRIDG, however, the source and destination node labels may impart different semantics to different relationships having the same type. 

* The MDF relationship type alone is a more general concept than the concept applying the type to two particular endpoint nodes.
* Example: 'member of' relationships to a destination node may be mapped to a situation in the foreign model where the destination node is a property of the source node.

In the mapping, it is probably better to create a new concept for the foreign semantic, and link that concept to the relationship object that has the specfied source and destination. 

Now two concepts are linked to the relationship - the MDF concept and the foreign model concept. This starts to suggest a "semantic neighborhood" of the relationship. The term for the relationship type is not a 'synonym' for the term representing the foreign concept -- the terms are not linked to the same concept node. But they can be said to be related, because the two concepts link to the same relationship node. (This is a legitimate real-world statement, because the foreign mapping was created by a subject matter expert in the foreign model.)

## Recording BRIDG mappings

BRIDG mapping entails relating single BRIDG entities (Classes, Attributes, Associations) to single MDF entity (node, property, relationship, term). However, because BRIDG entities tend to represent more general concepts than a given concept in a model created for a pragmatic application (a given clinical study, for example), a context called a _mapping path_ accompanies each entity mapping. 

### Mapping Paths

The mapping path particularizes the mapping, to indicate how the general BRIDG entity is used in the context of the pragmatic model. It can indicate (using BRIDG classes and relationships) where the entity appears in the workflow or process of the pragmatic model For example, a productDose is a single BRIDG attribute, but it in different contexts, it may refer to (1) the dose of a drug that was specified in a trial protocol, (2) a dose that was in fact administered to a participant in the trial, or (3) a dose that led to an adverse event in a participant, among others. 

The mapping path also allows the SME to specify codes and other terminology from the pragmatic model to further constrain the context. For example, the BRIDG attribute nameCode can be specified in a mapping path ( " ...WHERE DefinedActivity.nameCode.originalText == 'narf'..." ) to precisely refer to the term and related entity in the pragmatic model.

(Note: DefinedActivity.nameCode has HL7 data type [CD](http://www.hl7.org/documentcenter/private/standards/v3/edition_web/infrastructure/datatypes_r2/datatypes_r2.html#dt-CD), a complex type with a field "originalText". BRIDG data types are borrowed from HL7, as described in the BRIDG 5.3 Users Guide.)

The mapping path provided by the SME is generally a shorthand: associations are represented by '>', not usually named. The syntax is not precise.

### Representing BRIDG mappings as concepts

As a first pass, we associate each BRIDG mapping with a separate concept node, rather than attempt to create a synonym to an exist concept pointed to by the pragmatic model entity.

The BRIDG component of the mapping is represented with a Term node, with value = <Class>\[.<Element>\]. The mapping path is stored in a mapping\_path property on the Term.

The origin_id is taken from the BRIDG XMI element that defines the BRIDG entity.


