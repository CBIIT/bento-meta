# NAME

Bento::Meta::Model - object bindings for Bento Metamodel Database

# SYNOPSIS

    # empty model with name $handle:
    $model = Bento::Meta::Model->new('Test');
    # pull model from database - add bolt connection with Neo4j::Bolt
    $model = Bento::Meta::Model->new('ICDC',Neo4j::Bolt->connect('bolt://localhost:7687))
    # connect model to db after creating 
    $model = Bento::Meta::Model->new('CTDC');
    $model->set_bolt_cxn( Neo4j::Bolt->connect('bolt://localhost:7687') );
    $model->get(); # pulls nodes, properties, relationships with model => 'CTDC'

    # read a model from MDF YAML files:
    use Bento::Meta::MDF;
    $model = Bento::Meta::MDF->create_model(qw/icdc-model.yml icdc-model-props.yml/);
    # connect it and push to db
    $model->set_bolt_cxn( Neo4j::Bolt->connect('bolt://localhost:7687') );
    $model->put(); # writes all to db

    # build model from scratch: add, change, and remove entities

    $model = Bento::Meta::Model->new('Test');
    
    # create some nodes and add them
    ($case, $sample, $file) = 
       map { Bento::Meta::Model::Node->new({handle => $_}) } qw/case sample file/;
    $model->add_node($case);
    $model->add_node($sample);
    $model->add_node($file);
    
    # create some relationships (edges) between nodes
    $of_case = Bento::Meta::Model::Edge->new({ 
      handle => 'of_case',
      src => $sample,
      dst => $case });
    
    $has_file = Bento::Meta::Model::Edge->new({
      handle => 'has_file',
      src => $sample,
      dst => $file });
      
    $model->add_edge($of_case);
    $model->add_edge($has_file);

    # create some properties and add to nodes or to edges
    $case_name = Bento::Meta::Model::Property->new({
      handle => 'name',
      value_domain => 'string' });
    $workflow_type = Bento::Meta::Model::Property->new({
      handle => 'workflow_type',
      value_domain => 'value_set' });

    $model->add_prop( $case => $case_name );
    $model->add_prop( $has_file => $workflow_type );

    # add some terms to a property with a value set (i.e., enum)

    $model->add_terms( $workflow_type => qw/wdl cwl snakemake/ );
     

# DESCRIPTION

[Bento::Meta::Model](/perl/lib/Bento/Meta/Model.md) provides an object representation of a single
[property
graph](https://en.wikipedia.org/wiki/Graph_database#Labeled-property_graph)-based
data model, as embodied in the structure of the [Bento Metamodel
Database](https://github.com/CBIIT/bento-mdf) (MDB). The MDB can store
multiple such models in terms of their nodes, relationships, and
properties. The MDB links these entities according to the structure of
the individual models. For example, model nodes are represented as
metamodel nodes of type "node", model relationships as metamodel nodes
of type "relationship", that themselves link to the relevant source
and destination metamodel nodes, representing the two end nodes in the
model itself. [Bento::Meta::Model](/perl/lib/Bento/Meta/Model.md) can create, read, update, and link
these entities together according to the [MDB
structure](https://github.com/CBIIT/bento-meta#structure).

The MDB also provides entities for defining and maintaining
terminology associated with the stored models. These include the
`term`s themselves, their `origin`, and associated `concept`s. Each
of these entities can be created, read, and updated using
[Bento::Meta::Model](/perl/lib/Bento/Meta/Model.md) and the component objects.

## A Note on "Nodes"

The metamodel is a property graph, designed to store specific property
graph models, in a database built for property graphs. The word "node"
is therefore used in different contexts and can be confusing,
especially since the Cancer Research Data Commons is also set up in
terms of "nodes", which are central repositories of cancer data of
different kinds. This and related documentation will attempt to
distinguish these concepts as follows.

- A "graph node" is a instance of the node concept in the
property graph model, that usually represents a category or item of
interest in the real world, and has associate properties that
distinguish it from other instances.
- A "model node" is a graph node within a specific data model, and represents groups of data items (properties) and can be related to other model nodes via model relationships. 
- A "metamodel node" is a graph node that represents a model node, model 
relationship, or model property, in the metamodel database.
- A "Neo4j node" refers generically to the representation of a node in the Neo4j database engine.
- A "CRDC node" refers to a data commons repository that is part of the CRDC, such as the [ICDC](https://caninecommons.cancer.gov/#/).

## A Note on Objects, Properties, and Attributes

[Bento::Meta](/perl/lib/Bento/Meta.md) creates a mapping between Neo4j nodes and Perl
objects. Of course, the objects have data associated with them,
accessed via setters and getters. These object-associated data are
referred to exclusively as "attributes" in the documentation.

Thus, a `Bento::...::Node` object has an attribute `props`
(properties), which is an (associative) array of
`Bento::...::Property` objects. The `props` attribute is a
representation of the `has_property` relationships between the
metamodel node-type node to its metamodel property-type nodes.

See [below](#object-attributes) for more details.

## Working with Models

Each model stored in the MDB has a simple name, or handle. The word
"handle" is used throughout the metamodel to distinguish internal
names (strings that are used within the system and downstream
applications to refer to entities) and the external "terms" that are
employed by users and standards. Handles can be understood as "local
vocabulary". The handle is usually the name of the CRDC node that the
model supports.

A [Bento::Meta::Model](/perl/lib/Bento/Meta/Model.md) object is meant to represent only one model. The 
[Bento::Meta](/perl/lib/Bento/Meta.md) object can contain and retrieve a number of models.

## Component Objects

Individual entities in the MDB - nodes, relationships, properties,
value sets, terms, concepts, and origins, are represented by instances
of corresponding [Bento::Meta::Model::Entity](/perl/lib/Bento/Meta/Model/Entity.md) subclasses:

- [Bento::Meta::Model::Node](/perl/lib/Bento/Meta/Model/Node.md)
- [Bento::Meta::Model::Edge](/perl/lib/Bento/Meta/Model/Edge.md)

    "Edge" is shorter than "relationship".

- [Bento::Meta::Model::Property](/perl/lib/Bento/Meta/Model/Property.md)
- [Bento::Meta::Model::ValueSet](/perl/lib/Bento/Meta/Model/ValueSet.md)
- [Bento::Meta::Model::Term](/perl/lib/Bento/Meta/Model/Term.md)
- [Bento::Meta::Model::Concept](/perl/lib/Bento/Meta/Model/Concept.md)
- [Bento::Meta::Model::Origin](/perl/lib/Bento/Meta/Model/Origin.md)

`Bento::Meta::Model` methods generally accept these objects as
arguments and/or return these objects. To obtain specific scalar
information (for example, the handle string) of the object, use the
relevant getter on the object itself:

    # print the 'handle' for every property in the model
    for ($model->props) {
      say $_->handle;
    }

### Object attributes

A node in the graph database can possess two kinds of related data. In
the (Neo4j) database, node "properties" are named items of scalar
data. These belong directly to the individual nodes, and are
referenced via the node. These map very naturally to scalar attributes
of a model object. For example, "handle" is a metamodel node property,
and it is accessed simply by the object attribute of the same name,
$node->handle(). In the code, these are referred to as "property
attributes" or "scalar-valued attributes".

The other kind of data related to a given node is present in other nodes
that are linked to it via graph database relationships. In the
MDB, for example, a model edge (e.g., "of\_sample") is represented by
its own graph node of type "Relationship", and the source and
destination nodes for that edge are two graph nodes of type "Node",
one of which is linked to the Relationship node with a graph
relationship "has\_src", and the other with a graph relationship
"has\_dst". (Refer to [this
diagram](https://github.com/CBIIT/bento-meta#structure).)

In the object model, the source and destination nodes of an edge are
also represented as object attributes: in this case, $edge->src
and $edge->dst. This representation encapsulates the "has\_src" and
"has\_dst" graph relationships, so that the programmer can ignore the
metamodel structure and concentrate on the model structure. Note that
the value of such an attribute is an object (or an array of objects).
In the code, such attributes are referred to as "relationship",
"object-valued" or "collection-valued" attributes.

### Object interface

Individual objects have their own interfaces, which are partially described
in ["METHODS"](#methods) below. Essentially, the name of the attribute is the 
name of the getter, while "set\_&lt;name>" is the setter. Getter return 
types depend on whether the attribute is scalar, object, or collection-valued.
Setter arguments have similar dependencies.

    For an attribute "blarg":

                       getter                            setter
    scalar-valued      blarg() returns scalar            set_blarg($scalar)
    object-valued      blarg() returns object            set_blarg($obj)
    collection-valued  blarg() returns array of objects  set_blarg(key => $obj)

A true array is returned by collection-valued getters, not an arrayref.

Collection-valued attributes are generally associative arrays. The key 
is the handle() of the subordinate object (or value() in the case of 
[term](/perl/lib/Bento/Meta/Model/Term.md) objects).

## Model as Container

The Model object is a direct container of nodes, edges (relationships), and
properties. To get a simple list of all relevant entities in a model, use the
model getters:

    @nodes = $model->nodes();

To retrieve a specific entity, provide a key to the getter as the argument. 
The keys are laid out as follows

    Entity    Key                              Example
    ------    ---                              -------
    Node      <node handle>                    sample
    Property  <node handle>:<property handle>  sample:sample_type
    Edge      <edge handle>:<src node handle>:<dst node handle>
                                               of_sample:sample:case

For example:

    $of_sample = $model->edges('of_sample:sample:case');
    # get source and destination node objects from edge object itself
    $sample = $of_sample->src;
    $case = $of_sample->dst;

The component objects are themselves containers of their own attributes, and
their getters and setters are structured similarly. (In fact, 
`Bento::Meta::Model` is, like the component objects, a subclass of 
[Bento::Meta::Model::Entity](/perl/lib/Bento/Meta/Model/Entity.md)). The difference is that keys for collection-
valued attributes at the component object level are simpler. For example:

    $prop1 = $model->props('sample:sample_type');
    $prop2 = $sample->props('sample_type');
    # $prop1 and $prop2 are the same object

## Model as an Interface

The Model object has methods that allow the user to add, remove and
modify entities in the model. The Model object is an interface, in
that loosely encapsulates the MDB structure and tries to relieve the
user from having to remember that structure and guards against
deviations from it. 

The main methods are 

- add\_node()
- add\_edge()
- add\_prop()
- add\_terms()
- rm\_node()
- rm\_edge()
- rm\_prop()
- rm\_terms() (coming soon)

Details are below in ["$model object"](#model-object). The main idea is that these
methods operate on either the relevant component object or on a
hashref that specifies an object by its attributes. In the latter
case, a new component object is created.

Here's a pattern for creating two nodes and an edge in a model:

    $src_node = $model->add_node({ handle => 'sample' });
    $dst_node = $model->add_node({ handle => 'case' });
    $edge = $model->add_edge({ handle => 'of_case',
                                  src => $src_node,
                                  dst => $dst_node });

These new entities are registered in the model, and can be retrieved:

    $case = $model->nodes('case'); # same obj as $dst_node
    $of_case = $model->edges('of_case:sample:case'); # same obj as $edge

Removing entities from the model "deregisters" them, but does not destroy
the object itself. 

    $case = $model->rm_node($case);
    $other_model->add_node($case);

Analogous to Neo4j, attempting to remove a node will throw, if the node 
participates in any relationships/edges. For the above to work, for example,
would require

    $model->rm_edge($of_case);

first.

### Manipulating Terms

One of the key uses of the MDB is for storing lists of acceptable values for
properties that require them. In the MDB schema, a property is linked to 
a value set entity, and the value set aggregates the term entities. The model
object tries to hide some of this structure. It will also create a set of 
Term objects from a list of strings as a shortcut. 

    $prop = $model->add_prop( $sample => { handle => 'sample_type',
                                           value_domain => 'value_set' });
    # $prop has domain of 'value_set', so you can add terms to it
    $value_set = $model->add_terms( $prop => qw/normal tumor/ );
    @terms = $value_set->terms; # set of 2 term objects
    @same_terms = $prop->terms; # prop object also has a shortcut 

## Database Interaction

The approach to the back and forth between the object representation
and the database attempts to be simple and robust. The pattern is a
push/pull cycle to and from the database. The database instrumentation
is also encapsulated from the rest of the object functionality, so
that even if no database is specified or connected, all the object
manipulations are available.

The Model methods are ["get()"](#get) and ["put()"](#put). `get()` pulls the
metamodel nodes for the model with handle `$model->handle` from
the connected database. It will not disturb any modifications made to
objects in the program, unless called with a true argument. In that
case, `get(1)` (e.g.) will refresh all objects from current metamodel
nodes in the database.

`put()` pushes the model objects, with any changes to attributes, to
the database. It will build and execute queries correctly to convert, for
example, collection attributes to multiple nodes and corresponding
relationships. `put()` adds and removes relationships in the database as
necessary, but will not fully delete nodes. To completely remove objects
from the database, use `rm()` on the objects themselves:

    $edge = $model->rm_edge($edge); # edge detached from nodes and removed 
                                    # from model
    $model->put(); # metamodel node representing the edge is still present in db
                   # but is detached from the source node and destination node
    $node->rm(); # metamodel node representing the edge is deleted from db

# METHODS

## $model object

### Write methods

- new($handle)
- add\_node($node\_or\_init)
- add\_edge($edge\_or\_init)
- add\_prop($node\_or\_edge, $prop\_or\_init)
- add\_terms($prop, @terms\_or\_inits)
- rm\_node($node)
- rm\_edge($edge)
- rm\_prop($prop)

### Read methods

- @nodes = $model->nodes()
- $node = $model->node($name)
- @props = $model->props()
- $prop = $model->prop($name)
- $edge = $model->edge($triplet)
- @edges = $model->edges\_in($node)
- @edges = $modee->edges\_out($node)
- @edges = $model->edge\_by\_src()
- @edges = $model->edge\_by\_dst()
- @edges = $model->edge\_by\_type()

### Database methods

- get()

    Pull metamodel nodes from database for the model (given by $model->handle)
    Refresh nodes (reset) by issuing $model->get(1). 

- put()

    Push model changes back to database. This operation will disconnect (remove
    Neo4j relationships) nodes, but will not delete nodes themselves.

## $node object

- $node->name()
- $node->category()
- @props = $node->props()
- $prop = $node->props($name)
- @tags = $node->tags()

## $edge object

- $edge->type()
- $edge->name()
- $edge->is\_required()
- $node = $edge->src()
- $node = $edge->dst()
- @props = $edge->props()
- $prop = $edge->props($name)
- @tags = $edge->tags()

## $prop object

- $prop->name()
- $prop->is\_required()
- $value\_type = $prop->type()
- @acceptable\_values = $prop->values()
- @tags = $prop->tags()
