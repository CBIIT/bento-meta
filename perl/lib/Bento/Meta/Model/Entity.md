# NAME

Bento::Meta::Model::Entity - base class for model objects

# SYNOPSIS

    package Bento::Meta::Model::Object;
    use base Bento::Meta::Model::Entity;
    use strict;
    
    sub new {
      my $class = shift;
      my ($init_hash) = @_;
      my $self = $class->SUPER::new( {
        _my_scalar_attr => undef,
        _my_object_attr => \undef,
        _my_array_attr => [],
        _my_hash_attr => {},
        }, $init );
    }

    use Bento::Meta::Model::Object;
    $o = Bento::Meta::Model::Object->new({
     my_scalar_attr => 1,
     my_array_attr => [qw/ a b c /],
     my_object_attr => $Object,
     my_hash_attr => { yet => 0, another => 1, hashref => 2},
    });

    # getters
    $value = $o->my_scalar_attr;  # get scalar value
    @values = $o->my_array_attr;  # get array (not ref)
    $hash_value = $o->my_hash_attr; # get hashref, but prefer this:
    $value_for_key = $o->my_hash_attr( $key ); # get hash value for key, or
    @hash_values = $o->my_hash_attr; # in array context, returns hash values as array

    # setters
    $new_value = $o->set_my_scalar_attr("new value!"); # set scalar
    $o->set_my_array_attr( [ qw/ arrayref with some values / ] ); # replace arrayref
    $o->set_my_hash_attr( key => $value ); # set a value for a key in hash attr
    $o->set_my_hash_attr( { brand => 1, new => 2, hashref => 3 }); # replace hashref 

# DESCRIPTION

Bento::Meta::Model::Entity is a base class that allows quick and dirty setup
of model objects and provides a consistent interface to simple attributes.
See ["SYNOPSIS"](#synopsis).

It also provides a place for common actions that must occur for OGM bookkeeping.

You can override anything in the subclasses and make them as complicated as 
you want. 

Private (undeclared) common attributes do not appear in the $obj->attrs. 
The base class Entity has the following private attributes

    neoid - the Neo4j internal id integer for the node mapped to the object 
            (if any)
    dirty - a flag that is set when the object has been changed but not yet pushed
            to the database

# METHODS

## Class Methods

- new($attr\_hash, $init\_hash)

    $attr\_hash configures the object's declared attributes. $init\_hash
    initializes the attributes' values. $init\_hash can be a plain hashref
    or a [Neo4j::Bolt::Node](https://metacpan.org/pod/Neo4j::Bolt::Node).

- object\_map($map\_definition\_hashref, $bolt\_cxn), object\_map() - getter

    Create and attach an [Bento::Meta::Model::ObjectMap](/perl/lib/Bento/Meta/Model/ObjectMap.md) to the `Entity` subclass.
    The ObjectMap defines the associations from the object class and 
    attributes to the Neo4j graph model, as well as the connection to the graph
    database. When the ObjectMap is defined, instances receive the ["get()"](#get),
    ["put()"](#put), [add\_&lt;attr>](https://metacpan.org/pod/add_<attr>), and [drop\_&lt;attr>](https://metacpan.org/pod/drop_<attr>) methods for
    maintaining consistency between objects and nodes in the graph.

    For a given subclass of `Entity`, the map definition hash provides the 
    corresponding label for its mapped Neo4j node, the mappings of simple scalar
    attributes to mapped node properties, object-valued attributes to the mapped 
    Neo4j relationship and target node, and collection-valued attributes to their
    mapped relationship and target nodes. Example:

        my $omap = "Bento::Meta::Model::Node"->object_map(
           {
             label => 'node',
             simple => [
               [model => 'model'],
               [handle => 'handle']
              ],
             object => [
               [ 'concept' => ':has_concept>',
                 'Bento::Meta::Model::Concept' => 'concept' ],
              ],
             collection => [
               [ 'props' => ':has_property>',
                 'Bento::Meta::Model::Property' => 'property' ],
              ]
            },
            $bolt_cxn
          );

    Note that each individual attribute map is an arrayref with a single element,
    and that these are wrapped in another arrayref which is assigned to the 
    relevant hash key.

    The simple-valued attribute maps have this form:

        [ <attribute_name> => <neo4j_property_name> ]

    The object-valued attribute maps have this form:

        [ <attribute_name> => <neo4j_relationship_type>,
          <target_attribute_classname> => <neo4j_target_node_label> ]

        Note: <target_attribute_classname> can be a class name string, or an 
        array of class names, so an attribute can contain objects of more
        than one class.

    The directionality of the relationship is given using an angle bracket, 
    as in [Neo4j::Cypher::Abstract](https://metacpan.org/pod/Neo4j::Cypher::Abstract). The direction is given relative to the the 
    subclass.

    The database connection of the map can set in the setter or on the map object:

        $cxn = Neo4j::Bolt->connect("bolt://localhost:7687");
        $omap->bolt_cxn($cxn);

## Instance Methods

- make\_uuid()

    Create a new uuid (with [Data::UUID](https://metacpan.org/pod/Data::UUID)).
    Doesn't put it anywhere, just returns it.

- attrs()

    Returns list of attributes declared for this object. 

- atype($attr)

    Return type of the attribute $attr.
      undef => scalar
     'SCALAR' or ref($obj) => object
     'ARRAY' => array, 
     'HASH' => hash

- set\_with\_node($neo4j\_bolt\_node)

    Set all simple scalar attributes according to values in 
    $neo4j\_bolt\_node->{properties}, and assign object's neoid attribute
    to $neo4j\_bolt\_node->{id}.

- map\_defn()

    This should be defined in the subclasses. It should return a map definition 
    hashref for the subclass as described above in ["object\_map"](#object_map). See 
    [Bento::Meta::Model::Node](/perl/lib/Bento/Meta/Model/Node.md), for example.

## Database interaction methods

When the subclass has been instrumented with an [Bento::Meta::Model::ObjectMap](/perl/lib/Bento/Meta/Model/ObjectMap.md),
the following methods are available on any instance.

- get(), get($refresh)
- put()
- rm()
- add\_&lt;attr>()
- drop\_&lt;attr>()

# AUTHOR

    Mark A. Jensen (mark -dot- jensen -at- nih -dot- gov)
    FNL
