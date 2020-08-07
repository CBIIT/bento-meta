[![Build Status](https://travis-ci.org/CBIIT/bento-mdf.svg?branch=master)](https://travis-ci.org/CBIIT/bento-mdf)

# Bento Graph Model Description Framework

## Overview

The Bento graph model description framework allows a user to provide a very simple, human-readable description of an overall [property graph](https://en.wikipedia.org/wiki/Graph_(abstract_data_type)) model. The layout of nodes, relationships, node properties, and relationship properties are specified in data structures expressed in YAML-formatted _model description files_ (MDFs).

The Bento framework is currently used in the following projects;

* The [Integrated Canine Data Commons](https://caninecommons.cancer.gov)
* The [Clinical Trials Data Commons](https://github.com/CBIIT/ctdc-model)

## Drivers and Tools

Language drivers and other tools that want to comply with the Bento
framework should observe the latest [specification](./spec).

[make-model](./drivers/Perl/make-model/README.md) is a reference
driver and tool written in [Perl](https://www.perl.org/).

### Validator

A simple command line validator is included in the repo at
[mdf-validate](./validators/mdf-validate). See that page for install
and usage information.

## Model Description Files (MDF)

The layout of nodes, relationships, node properties, and relationship properties are specified in data structures expressed in YAML-formatted _model description files_ (MDFs).

The input format follows these general conventions, which are enforced by a [JSONSchema](https://json-schema.org/understanding-json-schema/) [schema](./schema/mdf-schema.yaml):

* Special key names are capitalized; these are essentially MDF directives.

* Custom names, such as names of nodes and properties, are all lower case, with underscores replacing any spaces ("snakecase");

A graph model can be expressed in a single YAML file, or multiple YAML files. [Compliant](./spec) drivers will merge the data structures are merged, so that, for example, nodes and relationships can be described in one file, and property definitions can be provided in a separate file.

### Nodes

The `Nodes` top-level key points to an object containing descriptions of each node type in the model. Node descriptions look like:

    <nodename> :
        Category: <categoryname>
        UniqueKeys:
            - [ 'propnameA', 'propnameB', ... ]
            - [ ... ]
            - ...
        Props:
           - <propname1>
           - <propname2>
           - ...

A node type can have a defined category, or a default (which can be configured) will be used in the final output.

The `UniqueKeys` key points to an array of arrays. Each bottom-level array is a list (which can be of length 1) of node property names. This specifies that nodes of this type that are created in the system must be unique with respect to the set of values for the properties indicated. For example, `['id']` here indicates that the value for the property `id` must be unique for all nodes of the type. `['project_id', 'submitter_id']` indicates that the submitter id must be unique among all nodes having a given project_id value.

The `Props` key points to a simple array of property names given as strings. The detailed definition of each property (e.g., value type or enumeration, required status) are provided once, in a separate top-level section, `PropDefinitions` ([see below](#Property Definitions)).

### Relationships

The `Relationships` top-level key points to an object of descriptions of each relationship type. Relationship descriptions look like:

    <relname>:
         Props:
             - <propname>
         Req: [ true | false ]
         Mul: [ one_to_one | many_to_one | many_to_many | one_to_many ]
         Ends:
            - Src: <nodename1>
               Dst: <nodename2>
            - Src: <nodename...>
               ...

A named relationship can have properties defined, analogous to nodes.

A named relationship can be specified as required with the `Req` key, and its multiplicity (from source node type to destination node type) with the `Mul` key.

A given named relationship can be formed between different source and destination node type pairs. The `Ends` key points to an array of `{ Src, Dst }` objects that describe the allowed pairs.

### Property Definitions

The `PropDefinitions` top-level key points to an object of descriptions of each property. Property descriptions look like:

    <propname1>:
        Term: <term reference token>
        # e.g., for $ref: "_terms.yaml#/ajcc_clinical_m", 
        # use 'ajcc_clinical_m'
        Desc: "a description of the property"
        Type: <string|number> # or the following:
        Enum:
            - acceptable
            - values
            - for
            - property
            - go
            - here
        Nul: <true|false> # is property nullable?
        Req: <true|false> # is property required?
        Src: <a string describing where the property came from - e.g.
                 a CRF.>


Either the `Type` or the `Enum` key should be present. If Enum key is present, the `Type` key will be ignored.

`Src` is a note regarding the data source of the property. The value is not used in any output; it is essentially a comment.

Where properties need to be applied to Nodes and Relationships, use a list of propnames from those defined in PropDefinitions.

### Universal Properties

In some use cases, it is desirable for every node (or relationship) to possess a certain property or set of properties. For example, every node may be expected to have a unique ID, regardless of its type.

The `UniversalNodeProperties` and `UniversalRelationshipProperties` top-level keys provide a means to specify these properties. The subkey `mustHave` should contain an array of property names for required universal properties. The subkey `mayHave` can contain an array of property names that are univerally allowable for all nodes or relationships.

    UniversalNodeProperties:
      mustHave:
        - id
      mayHave:
        - transaction_id

### Multiple input YAML files and "overlays"

The [specification](./spec) allows graphs to be defined over multiple input YAML files. The structured information in the files are merged together to produce one input structure internally. This allows a user to, for example, keep Node definitions in one file, Relationships in another, and Property definitions in yet another. Each of these objects has a separate top-level key, and will be merged into the single internal object without any "collisions".

[Compliant](./spec) drivers and tools enable merging YAML files into a single object according to specific rules. These allow the user to "overlay" desired changes onto a base model file, without having to resort to multiple versions of a base model. The first pair of files is merged, the next file is merged into that result, and so on to the end of the input files.  For example, using [./drivers/Perl/make-model](model-tool):

    model-tool -g graph.svg icdc-model.yml temp-changes.yml

would create a graphic of nodes and edges defined in `icdc-model.yml`, as modified by changes specified in `temp-changes.yml`.

#### Adding elements

As indicated above, if independent sets of keys at a given level of the YAML structure are present in the input files, the merged structure will possess all the keys and their contents:

File 1:

    Nodes:
      original_node:
        Props:
	      - old_prop

File 2:

    Nodes:
      original_node:
        Props:
          - new_prop
      addtional_node:
        Props:
          - new_prop

yields

    Nodes:
      original_node:
        Props:
          - old_prop
          - new_prop
      additional_node:
        Props:
          - new_prop

Note that by default, the overlay keys and values are added; original array elements are not replaced. Array elements remain unique: if both files have an element named `foo`, only one `foo` element will be present in the merged array.

#### Deleting/replacing elements

To indicate that an overlay should remove a key and its contents, or an array element, that are present in an earlier file, prefix the key/element with a forward slash `/`

File 1:

    Nodes:
      original_node:
        Props:
          - unwanted_prop
          - a_prop
      unwanted_node:
        Props:
          - a_prop

File 2:

    Nodes:
      original_node:
        Props:
          - /unwanted_prop
          - new_prop
      /unwanted_node:
        Props:
          - whatever_prop

yields

    Nodes:
      original_node:
        Props:
          - a_prop
      - new_prop

#### Tagging Entities

A `Tags` entry can be added to any object (thing that accepts key:value pairs) in the MDF. This is a way to associate metainformation with an entity that can be read later by a custom parser. A `Tags` entry value is an array of strings, the tags.

For example, one may markup a set of nodes to be rendered in a certain color:

    dog:
      Props:
        - breed
      Tags:
        - "color: red;"
    cat:
      Props:
        - breed
      Tags:
        - "color: blue;"
