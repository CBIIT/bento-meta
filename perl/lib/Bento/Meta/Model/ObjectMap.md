# NAME

Bento::Meta::Model::ObjectMap - interface Perl objects with Neo4j database

# SYNOPSIS

    # create object map for class
    $map = Bento::Meta::Model::ObjectMap->new('Bento::Meta::Model::Node')
    # map object attributes to Neo4j model 
    #  simple attrs = properties
    for my $p (qw/handle model category/) {
      $map->map_simple_attr($p => $p);
    }
    #  object- or collection-valued attrs = relationships to other nodes
    $map->map_object_attr('concept' => '<:has_concept', 
                          'concept' => 'Bento::Meta::Model::Concept');
    $map->map_collection_attr('props' => '<:has_property', 
                              'property' => 'Bento::Meta::Model::Property');

    # use the map to generate canned cypher queries

# DESCRIPTION

# METHODS

- new($obj\_class \[ => $neo4j\_node\_label \]\[, $bolt\_url\])

    Create new ObjectMap object for class C($obj\_class). Arg is a string.
    If $label is not provided, the Neo4j label that is mapped to the
    object is set as the last token  in the class namespace, lower-cased.
    E.g., for an object of class `Bento::Meta::Model::Node`, the label is
    'node'.

    $bolt\_cxn is a [Neo4j::Bolt::Cxn](https://metacpan.org/pod/Neo4j::Bolt::Cxn) object. Each map needs one to communicate
    with a database. It can be the same connection across maps.

- class()

    Get class mapped by this map.

- label()

    Get label for this map.

- bolt\_cxn()

    Get or set bolt\_cxn for this map ($map->bolt\_cxn($cxn) to set).

- map\_simple\_attr($object\_attribute => $neo4j\_node\_property)
- map\_object\_attr($object\_attribute => $neo4j\_node\_property, $fully\_qualified\_end\_object\_class => $end\_neo4j\_node\_label)
- map\_collection\_attr($object\_attribute => $neo4j\_node\_property, $fully\_qualified\_end\_object\_class => $end\_neo4j\_node\_label)
- get($obj)
- put($obj)
- rm($obj)

## Cypher generation methods

- get\_q($object)

    If $object is mapped, query for the node having the object's Neo4j id.
    If not mapped, query for (all) nodes having properties that match the object's
    simple properties. The query returns the node (possibly multiple nodes, in the
    unmapped case).

- get\_attr\_q($object, $object\_attribute)

    For an object (matched in the same way as ["get\_q"](#get_q)):
    If the attribute named ($object\_attribute) is a simple type, query the value 
    of the corresponding node property. The query returns the value, if it exists.

    If the attribute is object- or collection-valued, query for the set of nodes
    linked by the mapped Neo4j relationship (as specified to ["map\_object\_attr"](#map_object_attr) or
    ["map\_collection\_attr"](#map_collection_attr)). The query returns one node per response row.

- put\_q($object)

    If $object is mapped, overwrite the mapped node's properties with the current
    value of the object's simple attributes. The query returns the mapped node's
    Neo4j id.

    If not mapped, create a new node according to the object's simple-valued
    attributes ( => Neo4j node properties), setting the corresponding properties.
    The query returns the created node's Neo4j id.

- put\_attr\_q($object, $object\_attribute => @values)

    The $object must be mapped (have a Neo4j id) for ["put\_attr\_q"](#put_attr_q). 
    $object\_attribute is the string name of the attribute (not the Neo4j property).
    If the attribute is simple-valued, the third argument should be the string or 
    numeric value to set. The query will set the property of the mapped node, and 
    return the node id.

    If the attribute is object- or collection-valued, the @values should be a list
    of objects appropriate for the attribute definitions. The query will match the
    object node-attribute relationship-attribute node links, and merge the attribute nodes. That is, the attribute nodes will be created if the relationship and 
    matching node do not already exist. For a collection-valued attribute, one query
    will be created per attribute node. Each query will return the attribute node's
    Neo4j id.

- rm\_q($object, \[$force\])

    The $object must be mapped (have a Neo4j id). The query will attempt to delete 
    the mapped node from the database. If $force is false or missing, the query will
    be formulated with "DELETE"; it will succeed only if the node is not participating in any relationship. 

    If $force is true, the query will be formulated with "DETACH DELETE", and the executed query will remove the mapped node and all relationships in which it
    participates.

- rm\_attr\_q($object, $object\_attribute => @values)

    The $object must be mapped (have a Neo4j id). If $object\_attribute is a
    simple-valued (property-mapped) attribute, the query will remove that 
    property from the mapped node. If $object\_attribute is an object-valued
    (relationship-mapped) attribute, then the query will remove the \_relationship
    only\_ between the node corresponding to $object and the nodes corresponding to 
    @values. This query does not remove nodes themselves from the database; 
    use `rm_q()` to get queries for that purpose.

# AUTHOR

    Mark A. Jensen < mark -dot- jensen -at- nih -dot- gov >
    FNL
