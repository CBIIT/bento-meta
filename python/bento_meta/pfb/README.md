# "Portable Format for Bioinformatics"

* [The Point](#point)
  * [Sidebar: Schema vs Instance](#schemavinstance)
* [Implementation](#Implementation)
  * [Improvements](#improvements)
* [PFB Schema](#pfbschema)
  * [Entity](#Entity)
  * [Metadata](#Metadata)
  * [Node and Property](#node-and-property)
  * [Link](#Link)
  * [Relation](#Relation)
  * [User Data Type](#user-data-type)
* [Worked Example](#worked-example)

<a id="point"/>

## The Point: To Send/Store Data and its Description _Together_

[Avro](https://avro.apache.org/docs/current/spec.html) is a specification for defining data structures and "transporting" data according to those structures in a way that preserves both the data and the structure. A data object whose structure is defined by an Avro schema may be [serialized](https://en.wikipedia.org/wiki/Serialization), that is, saved or transmitted, using Avro-compliant clients. An Avro compliant client can restore the transmitted data to a structured data object that is equivalent to the original data object in both structure and content. This is possible, because the Avro protocol is designed to send messages containing not only the data, but the data's schema as well.

The "Portable Format for Bioinformatics" is essentially a simple set of Avro schemas. Together, these define a "wrapper of metadata" around custom data objects (nodes and their properties, along with links betwen nodes) whose schemas are created by the user.

The "Portable Format for Bioinformatics" essentially supposes a common data structure (a [property graph](https://en.wikipedia.org/wiki/Graph_database#Labeled-property_graph)) that is in use or understood among a network of users of the format. The PFB "wrapper schema" contains metadata that is necessary to enable a reciever to reconstruct the graph organization of a larger dataset, of which the custom data in the Avro message is a part.

Because Avro is strict about its naming conventions, and does not allow arbitrary characters in its identifiers (and in particular, in enumerations, which encode the acceptible value sets for properties), PFB also specifies an ad hoc means to encode alternative characters into Avro identifiers so that the original names for things can be reconstituted. This simple encoding is [described here](https://github.com/uc-cdis/pypfb/tree/master/doc#enum).

<a id="schemavinstance"/>

### Sidebar: Schema vs Instance

In understanding Avro, or any schema-based data language, it is important to maintain the distinction between the schema, or "form of the data", and the instance (of the schema), which is the data itself, cast in that form. This can become very "meta" and confusing on a first pass. Both the schema and the instance are themselves documents (text documents, information flowing over the Internet, or structured objects in a computer program), which can add to the confusion. Bad documentation that makes assumptions of the reader and does not unambiguously distinguish betwen schema and instance can also complexify matters.

One way for the less technical reader to think of the difference is to consider a empty, but fillable, PDF form. This is a document -- a PDF file that can be stored on a drive and sent to a colleague. But, it only contains information about what should go in the form entries; it doesn't yet contain specific data about any person.

This empty PDF form is the "schema" for the specific information about the form filler that is desired. When you fill out the form, then it contains both the schema (the instructions and form field labels) and the desired information . The filled-out form is a new document, now said to be an "instance" of the schema. The data can now be easily read from the form, with the _meaning_ of the data also understood from the schema information - labels, headers, and instructions.

So, the "Portable Format for Bioinformatics" is a set of forms for data, elaborated according to the Avro schema standard. The work of the user is to understand the structure and the meaning of these forms, then to transform her data into the same structure. The Avro tools will then be able to validate that data (i.e., insure that the right kinds of data are in the right form fields) and also package that data, along with the structure, to create an Avro message document that can be stored or sent, and reconstituted correctly by a recipient system.

## Implementation

The "Portable Format for Bioinformatics" was designed originally by the [Genomics Data Commons](https://gdc.cancer.gov) engineering team at the University of Chicago. It has been proposed as a format to enable interoperability among various large data repositories and services supported by the NIH.

The reference implementation of PFB can be found at [this GitHub repository](https://github.com/uc-cdis/pypfb).  This implementation is somewhat obscure and difficult for a new user to grasp. For example, the PFB Avro schema is [hard-coded into a Python file](https://github.com/uc-cdis/pypfb/blob/5652cb7abdd152c223d12e2990746d159f55237c/pfb/writer.py#L77), rather than broken out into a separate, more easily maintained JSON file. 

### Improvements

We have replicated this original schema, but in a modular way that takes advantage of the ability of Avro APIs such as [fastavro](https://fastavro.readthedocs.io/en/latest/schema.html) to assemble separate, simple schemas into a more complex one, using schema namespaces in [complex types](https://avro.apache.org/docs/current/spec.html#schema_complex) and [named schema references](https://avro.apache.org/docs/current/idl.html#schema_references) to resolve schemas within schemas.

<a id="pfbschema"/>

## "Portable Format for Bioinformatics" Schema

### Entity

The root of the PFB schema structure is the [``Entity``](./pfb.Entity.avsc). In the present modular format, it is easy to display here (as JSON):

    {
      "name": "Entity",
      "namespace": "pfb",
      "type": "record", 
      "fields": [
        {
          "name": "id",
          "type": [
    	    "null",
    	    "string"
          ],
          "default":null
        },
        {
          "name": "name",
          "type": "string"
        },
        {
          "name": "object",
          "type": [
    	    "pfb.Metadata",
	        <UserDataType>,...
          ]
        },
        {
          "name": "relations",
          "type": {
    	    "type": "array",
    	    "items": "pfb.Relation"
          },
          "default": []
        }
      ]
    }

The ``Entity`` is the basic unit of schema+data in PFB. It is an Avro "record", that is, a named set of keys and values. The components of the ``Entity`` are given by its keys: ``id``, ``name``, ``object``, and ``relations``. (These are defined in the ``fields`` array above.)

``Entity.object`` defines the container for data. It represents a _union_ or choice among possible schemas. One of these choices is always a ``Metadata`` subentity.  The others are custom objects defined by the user. User-defined custom objects are not present in the basic schema; these are built by users from their own data and models. These are described [below](#User Data Types). Tools to do this for the Bento system will appear in this repository.

### Metadata

The [``Metadata``](./pfb.Metadata.avsc) schema defines a fairly non-specific container for information about the user's custom data types. An instance of ``Metadata`` will contain aspects of the terminology in the custom data type, such as the terminology source, the source's identifier for the term, and other aspects. (Note that the specification refers to "ontologies", but any term source -- the [caDSR](https://cdebrowser.nci.nih.gov), for example -- may be the referent.)

    {
      "type": "record",
      "name": "Metadata",
      "namespace": "pfb",
      "fields": [
        {
          "name": "nodes",
          "type": {
    	"type": "array",
    	"items": "pfb.Node"
          }
        },
        {
          "name": "misc",
          "type": {
    	"type": "map",
    	"values": "string"
          }
        }
      ]
    }

``Metadata.nodes`` establishes an array of ``Node`` items. These store the terminological information for the user-defined graph nodes. Properties (that is, the named slots for actual data) are described by another schema within the ``Node`` schema.

``Metadata.misc`` is apparently a catch-all key/value list.

### Node and Property

The [``Node``](./pfb.Node.avsc) schema contains not only terminological metadata, but also key information for reconstituting the graph structure of the original data. In particular, the ``Node.links`` array describes how the node data being sent should be connected by "links" (a.k.a "edges", or "relationships") to other nodes of different types. See [below](#Link).

    {
      "name": "Node",
      "type": "record",
      "namespace": "pfb",
      "fields": [
        {
          "name": "name",
          "type": "string"
        },
        {
          "name": "ontology_reference",
          "type": "string"
        },
        {
          "name": "values",
          "type": {
            "type": "map",
            "values": "string"
          }
        },
        {
          "name": "links",
          "type": {
            "type":"array",
    	    "items": "pfb.Link"
          }
        },
        {
          "name": "properties",
          "type": {
            "type": "array",
            "items": "pfb.Property"
          }
        }
      ]
    }

    {
      "name": "Property",
      "type": "record",
      "namespace": "pfb",
      "fields": [
        {
          "name": "name",
          "type": "string"
        },
        {
          "name": "ontology_reference",
          "type": "string"
        },
        {
          "name": "values",
          "type": {
            "type": "map",
            "values": "string"
          }
        }
      ]
    }

According to the [spec documentation](https://github.com/uc-cdis/pypfb/tree/master/doc), ``Node.values`` is a key/value structure meant to contain addition terminological information such as term IDs, urls, and other such details in an ad hoc way.

``Node.properties`` is a structure for describing terminological metadata for the properties ("variables", "slots") associated with the given custom node. The [``Property``](./pfb.Property.avsc) schema is analogous to the ``Node`` schema in this regard.

### Link

The [``Link``](./pfb.Link.avsc) schema provides a way to describe how the accompanying data is connected to other data nodes within the property graph. 

Note that ``Link`` (in the version of PFB at [this release](https://github.com/uc-cdis/pypfb/releases/tag/0.4.3)) does not allow a complete description of the property graph:

* There is no facility for describing properties associated with the _link_ (as opposed to nodes)
* There is no schema analogous to ``Node`` and ``Property`` for describing the terminological information associated with the _link_, which may itself have externally defined semantics.

These omissions would be relatively straightforward to correct.

    {
      "name": "Link",
      "type": "record",
      "namespace": "pfb",
      "fields": [
        {
          "name": "name",
          "type": "string"
        }
        {
          "name": "dst",
          "type": "string"
        },
        {
          "name": "multiplicity",
          "type": {
            "name": "Multiplicity",
            "type": "enum",
            "symbols": [
              "ONE_TO_ONE",
              "ONE_TO_MANY",
              "MANY_TO_ONE",
              "MANY_TO_MANY"
            ]
          }
        }
      ]
    }

Similarly to the so-called ["Gen 3" schema system](https://github.com/NCI-GDC/gdcdictionary/tree/develop/gdcdictionary/schemas), links are essentially attributes of nodes, rather than first-class entities. 

The ``Link`` schema assumes that the "source" node is the ``Node`` that contains the ``Link``. The "destination" ``Node`` is named in ``Link.dst``.

The cardinality of the link is given by ``Link.multiplicity`` -- again, the "left-hand side" of the term (e.g. ``ONE`` in ``ONE_TO_MANY``) is assumed to refer to the containing  ``Node``.

The ``Link`` name is (surprise) ``Link.name``. Note again that no slots for terminological information are provided (but could be added here in an update to the specification). 

### Relation

The [``Relation``](./pfb.Relation.avsc) schema (apparently) exists to contain the identifiers of the precise _instances_ of graph nodes to which the accompanying data node(s) link.  ``Link`` generically defines the local graph structure, while ``Relation`` imparts the instance information. There are probably other ways to do it.

    {
      "name": "Relation",
      "type": "record",
      "namespace": "pfb",
      "fields": [
        {
          "name": "dst_id",
          "type": "string"
        },
        {
          "name": "dst_name",
          "type": "string"
        }
      ]
    }

### User Data Type

PFB assumes a (not entirely general) property graph structure, that is encoded in a particular way. Taking the components described above together, the PFB is essentially designed to describe a series of graph nodes. Each node is described with its 

* properties, 
* property value data types, and 
* outgoing edges or links. 

Users defining schemas to transmit their own data must consider their data and data types in terms of this structure.

## Worked Example

While the above details the schema, the [point](#point) of PFB is to encode _data_ with it, so that it can be stored and sent. A complete worked example using the ICDC data model, with further explanatory text and runnable code, is available in [this Jupyter notebook](./example/icdc-pfb-example.ipynb). 
