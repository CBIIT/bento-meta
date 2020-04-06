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









