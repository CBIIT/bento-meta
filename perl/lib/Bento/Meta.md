# NAME

Bento::Meta - Tools for manipulating a Bento Metamodel Database

# SYNOPSIS

# DESCRIPTION

[Bento::Meta](/lib/Bento/Meta.md) is a full object-relational mapping (although for a graph
database, [Neo4j](https://neo4j.com)) of the Bento metamodel for storing
property graph representations of data models and terminology.

It can be also be used without a database connection to read, manipulate, 
and store data models in the 
[Model Description Format](https://github.com/CBIIT/bento-mdf) (MDF). 

This class is just a [Bento::Meta::Model](/lib/Bento/Meta/Model.md) factory and container. 

# METHODS

- load\_model($handle, @files), load\_model($handle, $bolt\_url)

    Load a model from MDF files, or from a Neo4j database. `$bolt_url` must
    use the `bolt://` scheme.

- model($handle)

    The [Bento::Meta::Model](/lib/Bento/Meta/Model.md) object corresponding to the handle.

- models()

    A list of [Bento::Meta::Model](/lib/Bento/Meta/Model.md) objects contained in the object.

- handles()

    A sorted list of model handles contained in the object.

# SEE ALSO

[Bento::Meta::Model](/lib/Bento/Meta/Model.md), [Neo4j::Bolt](https://metacpan.org/pod/Neo4j::Bolt).

# AUTHOR

    Mark A. Jensen < mark -dot- jensen -at nih -dot- gov>
    FNL
