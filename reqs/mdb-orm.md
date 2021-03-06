# Metamodel DB Object Graph Model

To be serious about the Meta DB as the official source of models and terms, we need to be able to compute with it - i.e., perform CRUD actions programmatically, rather than manually (by executing ad hoc queries directly). A dev will need to be able to interact with an object model of the database, that has a standardized API based on typical actions that need to be performed. The API can encapsulate the actual database queries and connections.

The [Bento::MakeModel::Model](https://github.com/CBIIT/bento-mdf/drivers/Perl/makemodel/) API is fairly complete and intuitive. Nodes, edges (relationships), edge types, and properties each have their own object classes, with methods that access relevant attributes and that represent the interactions between classes. For example, edges have source and destination nodes: an edge object can be queried for each of these, and in each case a node object is returned.

An object graph model would enable each of these objects to pull in and push to  corresponding entities in the MDB. Object methods that query the objects and their interactions could pull their results from the MDB, caching the results in appropriate objects (lazy loading).

Objects created "from scratch" or loaded from another source (such as MDF YAML files) require a facility for checking whether a corresponding MDB entity exists. An "equality" operation needs to be defined for this purpose.

Objects representing MDB entities need to be flagged as "dirty" if any of their attributes are changed.

Bringing the database in line with the object model is a process of identifying dirty objects and commiting the corresponding changes in a database transaction. The transaction must be monitored- if successful, the objects are flagged as "clean", if it fails or is rolled back, flags are unchanged. Object deletions need tracking and an internal "rollback" method.

The goal is to create a relatively simple custom OGM for the Metamodel schema, and not a fully general system.

- objects for Origin, Term, Concept, and Value Set may also be required.

The Bento::MakeModel::Model API is essentially read-only; creating the objects from scratch is a custom process that reads MDF YAML and builds the entire model at initialization.

## Use Cases

Level of object - DB communication?

1. READ - Represent a model currently in the DB as objects.
   * Pull a model atomically into objects 
   * Read attributes of entities
   * Get list of model nodes 
   * Get list of model edges
   * Get list of node properties
   * Get list of edge properties
   * Get value set of property
   * Get list of terms in value set

2. WRITE - Update objects and push to DB
   * Add properties to nodes
   * Update existing properties on nodes
   * Delete properties from nodes
   * Add properties to edges
   * Update existing properties on nodes
   * Delete properties from edges
   * Add a value set to a property
   * Add terms to a value set
   * Update terms on a value set
   * Delete terms from a value set

3. WRITE - Create objects as part of model and push model to DB
   * Create objects in model context and push to DB
     * i.e., "model creates objects", rather than creating singleton objects that map to DB
     * Update is a public model method, but individual objects do not have public update methods?

## Not in scope

  * Getting or putting arbitrary objects from/to DB (need to use model object to manage?)
  * Automagical DB push/pull (need to manually commit from model)

## Connecting DB with objects

In the Neo4j instance of the metamodel, all entities (Node, Edge, Property, ValueSet, Concept, Term, Origin) are represented by Neo4j nodes. Collections of entities associated with another entity (e.g., Properties of a Node) are represented by Neo4j relationships connecting the elements of the collection to the associated entity (e.g., Node has_property Properties). 

The Neo4j instance _also_ represents Edge/Relationship entities as Neo4j relationships between Node Neo4j nodes. These have relationship types equal to underscore+Edge.handle, with from-node set to Edge.src Neo4j node and to-node set to Edge.dst Neo4j node.

Objects represent Neo4j relationships between entities by attibutes that take other objects (or collections of objects) as values. 

Object represent Neo4j properties on entities by attributes that take scalar simple type values.

"mapped" entity - existing object that is associated with a unique Neo4j node in the DB. If an object is mapped, its neoid property is set to the Neo4j id of the mapped Neo4j node.

"equivalent" - an object and a Neo4j node are equivalent if the object entity type (Node, Edge, ...) is a member of the labels of the node, and every scalar simple attribute of the object has a corresponding node property, and the values of the corresponding object attribute and node property are equal.


* get entity - read an equivalent node from DB into a new object, map object to entity.

* put entity - write an object to DB - create a new node, even if an equivalent node exists, map object to new node.

* merge entity - write an object to DB if an equivalent node does not exist, or retrieve the id of the equivalent node (this is a "merge" in the Cypher sense), map object to node.

* pull entity - for an object that is mapped to a node, update scalar simple attributes in object to values of corresponding properties in node. (Remove object attributes corresponding to properties no longer present on node; add attributes to entity that are present on node but are not present on object. -?-)

* push object - for an object that is mapped to a node, update corresponding properties on node to scalar simple-valued attribute values in object.

Converting attributes into nodes/relationships and vice versa.

Some object attributes encode properties, others encode relationships with other objects. Attributes that are collection-valued are always relationship-encoding. Scalar-valued attributes that take an object as a value are relationship-encoding. Scalar-valued attributes that take a simple type as a value are property-encoding.

To pull a relationship and its end nodes into a new object:
* identify or pull objects for both ends and map
* set the attribute on the object corresponding to the relationship with the remaining object

To push a relationship-encoding attribute from an existing object:
* ensure both objects are mapped - (can refuse to proceed, or automatically map)
* create relationship between the mapped nodes according to the semantics of the attribute

        get - node + properties
        get_via(attr) - load attr with nodes connected by relationship
        put - node + properties
        put_via(attr) - put attr values, connect to calling object with relationship

Object-to-graph map:
* object -> labelled node
* object simple-valued attr -> node properties
* object object-valued attr ->  to-one relationship to labelled node
* object collection attr -> to-many relationship to labelled nodes

Q. Capturing relationship properties? Later.














