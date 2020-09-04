# "Portable Format for Bioinformatics"

## The Point: To Send/Store Data and its Description _Together_

[Avro](https://avro.apache.org/docs/current/spec.html) is a specification for defining data structures and "transporting" data according to those structures in a way that preserve both the data and the structure. A data object whose structure is defined by an Avro schema may be "serialized", that is, saved or transmitted, using Avro-compliant clients. An Avro compliant client can restore the transmitted data to a structured data object that is equivalent to the original data object in both structure and content. This is possible, because the Avro protocol is designed to send messages containing not only the data, but the data's schema as well.

The "Portable Format for Bioinformatics" is essentially a simple set of Avro schemas. Together, these define a "wrapper of metadata" around custom data objects (nodes and their properties, along with links betwen nodes) whose schemas are created by the user.

The "Portable Format for Bioinformatics" essentially supposes a common data structure (a [property graph](https://en.wikipedia.org/wiki/Graph_database#Labeled-property_graph)) that is in use or understood among a network of users of the format. The PFB "wrapper schema" contains metadata that is necessary to enable a reciever to reconstruct the graph organization of a larger dataset, of which the custom data in the Avro message is a part.

Because Avro is strict about its naming conventions, and does not allow arbitrary characters in its identifiers (and in particular, in enumerations, which encode the acceptible value sets for properties), PFB also specifies an ad hoc means to encode alternative characters into Avro identifiers so that the original names for things can be reconstituted. This simple encoding is [described here](https://github.com/uc-cdis/pypfb/tree/master/doc#enum).

## A Key Distinction: Schema vs Instance

In understanding Avro, or any schema-based data language, it is important to maintain the distinction between the schema, or "form of the data", and the instance (of the schema), which is the data itself, cast in that form. This can become very "meta" and confusing on a first pass. Both the schema and the instance are themselves documents (text documents, information flowing over the Internet, or structured objects in a computer program), which can add to the confusion. Bad documentation that makes assumptions of the reader and does not unambiguously distinguish betwen schema and instance can also complexify matters.

One way for the less technical reader to think of the difference is to consider a empty, but fillable, PDF form. This is a document -- a PDF file that can be stored on a drive and sent to a colleague. But, it only contains information about what should go in the form entries; it doesn't yet contain specific data about any person.

This empty PDF form is the "schema" for the specific information about the form filler that is desired. When you fill out the form, then it contains both the schema (the instructions and form field labels) and the desired information . The filled-out form is a document, now said to be an "instance" of the schema. The data can now be easily read from the form, with the _meaning_ of the data also understood from the schema information - labels, headers, instructions.

The "Portable Format for Bioinformatics" then is a set of forms for data, elaborated according to the Avro schema standard. The work of the user is then to understand the structure and the meaning of these forms, then to transform her data the same structure. The Avro tools will then be able to validate that data (i.e., insure that the right kinds of data are in the right form fields) and also package that data, along with the structure, to create an instance that can be stored or sent, and reconstituted correctly by a recipient system.

One final point: an Avro document, whether it represents a schema or an instance, is just [JSON](https://en.wikipedia.org/wiki/JSON), albeit highly constrained JSON. This makes these documents very easy to work with in programs.

# Implementation

The "Portable Format for Bioinformatics" was designed originally by the [Genomics Data Commons](https://gdc.cancer.gov) engineering team at the University of Chicago. It has been proposed as a format to enable interoperability among various large data repositories and services supported by the NIH.

The reference implementation of PFB can be found at [this GitHub repository](https://github.com/uc-cdis/pypfb).  This implementation is somewhat obscure and difficult for a new technical user to grasp. For example, the PFB Avro schema is [hard-coded into a Python file](https://github.com/uc-cdis/pypfb/blob/5652cb7abdd152c223d12e2990746d159f55237c/pfb/writer.py#L77), rather than broken out into a separate, more easily maintained JSON file. 

We have replicated this original schema, but in a modular way that takes advantage of the ability of Avro APIs such as [fastavro](https://fastavro.readthedocs.io/en/latest/schema.html) to assemble separate, simple schemas into a more complex one, using schema namespaces in [complex types](https://avro.apache.org/docs/current/spec.html#schema_complex) and [named schema references](https://avro.apache.org/docs/current/idl.html#schema_references) to resolve schemas within schemas. The Python [bento_meta](https://cbiit.github.io/bento-meta/) package will employ this implementation of PFB for its serializer (coming soon?).

# "Portable Format for Bioinformatics" Schema

## Entity

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

``Entity.object`` defines the container for data. It represents a _union_ or choice among possible schemas. One of these choices is always a ``Metadata`` subentity.  The others are custom objects defined by the user. User-defined custom objects are not present in the basic schema; these are built by users from their own data and models. These are described [below](./User Data Types). Tools to do this for the Bento system will appear in this repository.

## Metadata

The [``Metadata``](./pfb.Metadata.avsc) schema defines a fairly non-specific container for information about the user's custom data types. An instance of ``Metadata`` will contain aspects of the terminology in the custom data type, such as the terminology source, the source's identifier for the term, and other aspects. (Note that the specification refers to 'ontologies', but any term source -- the [caDSR](https://cdebrowser.nci.nih.gov), for example -- may be the referent.)

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

## Node and Property

The [``Node``](./pfb.Node.avsc) schema contains not only terminological metadata, but also key information for reconstituting the graph structure of the original data. In particular, the ``Node.links`` array describes how the node data being sent should be connected by "edges", "links", or "relationships" to other nodes of different types. See [below](#Link).

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

``Node.properties`` is a structure for describing terminological metadata for the properties ("variables", "slots") associated with the given custom node. The [``Property``](./pfb.Property.avsc) schema is similar to the ``Node`` schema in this regard.

## Link

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

## Relation

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

## User Data Type

PFB assumes a (not entirely general) property graph structure, that is encoded in a particular way. Taking the components described above together, the PFB is essentially designed to describe a series of graph nodes. Each node is described with its 

* properties, 
* property value data types, and 
* outgoing edges or links. 

Users defining schemas to transmit their own data must consider their data and data types in terms of this structure.

### Worked Example

Consider the following example. In the [Integrated Canine Data Commons (ICDC) model](https://cbiit.github.io/icdc-model-tool/), a subject of a study is called a _case_, and a case has the following properties (variable, slots for data) associated with it:

    case:
        Props:
          - case_id
          - patient_id
          - patient_first_name

(This and the following snippets of YAML are taken from the [model description files](https://github.com/CBIIT/bento-mdf) found at https://cbiit.github.io/icdc-model-tool/model-desc/.) The properties are defined in the model as follows (omitting human readable descriptions):

    case_id:
        Type: string
        Req: true
      patient_id:
        Type: string
        Req: true
      patient_first_name:
        Type: string

(Patient first name is OK, because we're talking about dogs.)

A case may have a number of other sets of related data. These are separate nodes in the graph,  associated with a specific case via relationships (links, edges). There are 14 such nodes, but only three of these are linked by outgoing (i.e. from case to node) relationships. The _cohort_ node is a simple example:

    cohort:
        Props:
          - cohort_description
          - cohort_dose

Both properties have type ``string``. The relationship ``member_of`` indicates the association:

    Relationships:
      member_of:
        Mul: many_to_one
        Ends:
          - Src: case
            Dst: cohort

Every node, regardless of type, also entails an internal _id_ field.

Avro schemas that will encode the nodes _case_ and _cohort_ are straightforward enough. These are the User Data Types.

    icdc_case_schema =
		{ 
          "name": "case",
          "type": "record",
		  "fields": [
			{ "name": "id",
			  "type": "string" },
			{ "name": "case_id",
			  "type": "string" },
			{ "name": "patient_id",
			  "type" ; "string" },
			{ "name": "patient_first_name",
			  "type": "string" }
		  ]
		}

    icdc_cohort_schema =
		{
          "name": "cohort",
          "type": "record",
		  "fields": [
			{ "name": "id",
			  "type": "string" },
			{ "name": "cohort_description",
			  "type": "string" },
			{ "name": "cohort_dose",
			  "type": "string" }
		  ]
		}

These schemas need to be included in the ``Entity`` schema at the time the PFB message is created.

### Metadata schemas and links

To encode these data nodes in PFB, we also must construct corresponding ``Node`` and ``Property`` metadata schemas, according to [the spec above](#node_and_property). An example using the ``cohort`` node is as follows. Note this is an _instance_ of the ``Node`` _schema_ above. The instance is an Avro record (a JSON object), and it has acceptable keys ``name``, ``ontology_reference``, ``values``, ``links``, and ``properties``.  

The ``cohort`` as a node type does not have an external terminology reference as yet, so ``ontology_reference`` and ``values`` are not used. It does not have any outgoing links in the model, so ``links`` is not used. ICDC properties are associated with NCI Thesaurus codes, so these are provided in the ``properties`` schemas.

    icdc_cohort_meta =
	  { 
		"name": "cohort",
		"properties": [
		  { 
			"name": "cohort_description",
			"ontology_reference": "NCIT",
			"values": {
			  "concept_code": "C166209"
			}
          },
		  { 
			"name": "cohort_dose",
			"ontology_reference": "NCIT",
			"values": {
			  "concept_code": "C166210"
			}
		  }
		]
	  }


For the ``case`` node, we also need to describe the outgoing link to the ``cohort``. Here, the ``properties`` schemas are constructed similarly to the above example, so we'll leave these out.

    icdc_case_meta =
		{
		  "name": "case",
		  "properties": [
			...
		  ],
		  "links": [
			{
			  "name": "member_of",
			  "dst": "cohort",
			  "multiplicity": "MANY_TO_ONE"
			}
		  ]
		}

## A Complete PFB Message of Two Entity Instances

Now consider some data to encode for transmission: a case and its cohort.

    {
      "id": "n101",
      "case_id": "UBC01-007",
      "patient_id": "007"
    }
    
    {
      "id": "n201",
      "cohort_description": "arm1",
      "cohort_dose": "10mg/kg"
    }


Two ``Entity`` instances must be sent in the PFB, one for each node, along with the metadata for each node type. The final component of the ``Entity``, an array of a single ``Relation`` instance, must accompany the case ``Entity``, to ensure that is connected to the cohort on the other side of the wire.

The PFB payload would look like:

    [
      { 
        "name": "Metadata",
        "object": icdc_cohort_meta
      },
      {
        "name": "Metadata", 
        "object": icdc_case_meta
      },
      {
        "name": "cohort",
        "id": "n201",
		"object":     {
          "case_id": "UBC01-007",
          "patient_id": "007"
        }
      },
      {
        "name": "case",
        "id": "n101",
        "object":      {
          "cohort_description": "arm1",
          "cohort_dose": "10mg/kg"
        },
        "relations": [
          "dst_name": "cohort",
          "dst_id": "n201"
        ]
      }
    ]

