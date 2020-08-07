# Object API for Data Models in Bento MDF : Specification

[Reference driver and application](../drivers/Perl/make-model)

## Background

The [ICDC](https://caninecommons.cancer.gov) and other CRDC nodes created by FNL/BIDS depend on graph data models described in [Model Description Files](https://github.com/CBIIT/bento-mdf#model-description-files-mdf) (MDF). These are plain text files formatted in YAML that follow a defined syntax, and provide a computable and human-readable way to record elements of the [property graph](https://en.wikipedia.org/wiki/Graph_database) persistently.

The MDFs form a single point of definition for a CRDC node's data model. Downstream applications and utilities depend on them to maintain a consistent database, validate incoming data, render the data model graphically for communications, and other key functions.

## Rationale

Although the MDF are expressed in a controlled syntax, they are inconvenient for developers to parse "manually". That is, the underlying syntax must be understood, the MDF must be read into language objects using a YAML parser, and those objects must be traversed directly within a user's code based on a detailed knowledge of the syntax. When this syntax is updated, which is likely, the changes can break existing code.

Additionally, multiple versions of MDFs may exist at any given time, in different code branches, different operational environments, or locally on a developer's machine. Code that reads MDFs directly from a hard-coded location will miss updates that may occur to standard locations.

To avoid these issues and to increase the usability of the MDF as a general framework for expressing the property graph, we are defining a general API that provides access to the structure of the MDF in a general way. This API is a specification that can inform language specific modules that read MDF and expose it as (an) object(s) with common methods and attributes.

## Specification

In the following:

* the term _module_ means a module or set of modules in the target programming language that supports the API as described;

* the term _model_ means the language object resulting from parsing the input MDF YAML files.

Qualifiers in the specification have the following meanings:

* "must" - the module does not conform to the API unless functionality noted is present.

* "should" - the functionality indicated is highly desirable.

* "may" - the functionality indicated would increase the utility of the module, but implementation is optional

### Usage

* The functionality described must be fully incorporated into the module, and not dependent on additional coding by the user.

* Configuration (e.g., defaults) should be enabled via documented environment variables or documented auxiliary files that accompany the module in distribution.

### Setup

* The module must accept one or more local files or URLs adhering to MDF format.

* The module must be configurable to use a default, possibly remote, location of MDF files if MDF file location is not specified by user.

* A module supporting this API should generate objects that expose the API, each of which may be initialized by different sets of MDFs. That is, a [Factory](https://en.wikipedia.org/wiki/Factory_method_pattern) pattern is encouraged.

### Input File Merge Functionality

* The module must enable the input of multiple MDF files. 

* The final representation of the model, a single object resulting from a merge of the individual objects represented by the input files, must be constructed according to the rules illustrated at [Multiple input YAML files and "overlays"](https://github.com/CBIIT/icdc-model-tool#multiple-input-yaml-files-and-overlays).

### Entities

The model description file structure is formally defined in [JSONSchema](https://json-schema.org/understanding-json-schema/). The definition artifact (a YAML file) is available [here](https://github.com/CBIIT/bento-mdf/blob/master/schema/mdf-schema.yaml).

The module must support the following entities and their attributes. 

* Node

A node describes an organized set of data. A node is referred to by its _label_, a string. A node with a given label is associated with given _properties_ (see below).

The module should represent edges in a structure (e.g., as an object of type "Node") that enables their individual attributes and properties to be queried.

* Edge

An edge describes a relationship between two nodes. Edges have a string _type_, a _source_ (a node label string), and a _destination_ (a node label string). The _direction_ of an edge is said to be _outgoing_ from its source node, and _incoming_ to its destination node.

In the model, an edge is uniquely described by the tuple (_type_, _source_, _destination_).

A given edge (_type_,_source_,_destination_) can be associated with given _properties_ (see below).

The module should represent edges in a structure (e.g., as an object of type "Edge") that enables their individual attributes and properties to be queried.

* Edge Type

Every edge has an _edge type_, which describes the relationship between the source node and destination node. To be completely specified, an edge must have an edge type.

* Property

A property is a unit of data, organized as a key/value pair. The key is the property name string. The value depends on the _property definition_, which can specify what data type a given property value may have.

  * Property Definition

A property definition structure defines a number of attributes that describe the value of a property with a given key. Possible attributes for a property are described [in this documentation](https://github.com/CBIIT/bento-mdf#property-definitions) and are formally defined in [JSONSchema](https://github.com/CBIIT/bento-mdf/blob/master/schema/mdf-schema.yaml).

### Methods

The module must implement the following methods at minimum.

* source() 

This method must provide the original object created by parsing the input files.

* nodes()
* properties()
* edge\_types()
* edges() 

These methods must provide a list containing the names of all the respective entities defined in the model.

edge_types() must return a deduplicated list of edge types that are present in the model.

* node(_name_)
* property(_name_)
* edge\_type(_name_)

These methods must provide the means to query the attributes of the named entity, or fail quietly.

The value of node(_name_) must provide access to the list of properties associated with the named node.

The value of property(_name_) must provide access to the property definition attributes associated with the named property. In particular, it should enable the following queries:

  * is\_required  - Boolean indicating whether the model requires a value for this property
  * type - indication of the valid value type - e.g., "integer", "enum")
  * values - if property value type is enumerated, a list of valid string values for the named property
    
* edge\_by\_src( _nodename_ )
* edge\_by\_dst( _nodename_ )
* edge\_by\_type(_type_)

These methods must provide lists of edge tuples or objects whose source name, destination name, or edge type string, respectively, equal the argument.

* Node.properties
* Edge.properties

Node and edge entities must expose accessors or methods that provide lists of associated properties or property names.

### Outputs

The following outputs must be available fram any standalone,  production quality MDF processing tool.

#### Validation 

The tool must read input YAML files and indicate whether the resulting object is valid with respect to the [MDF JSONSchema](../schema/mdf-schema.yaml).

#### Graphical representation of the input model

The tool must have the capability to render the model in a suitable graphics format.

### Table of nodes and associated properties

The tool must have the capability to produce a simple tab-separated or CSV table of the model's node names and property names.



