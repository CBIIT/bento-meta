# NAME

Bento::Meta::Model::Property - object that models a node or relationship property

# SYNOPSIS

    $prop = Bento::Meta::Model::Property->new({ handle => 'sample_weight', 
                                                value_domain => 'number',
                                                units => 'mg',
                                                is_required => 1 });           
    $node = Bento::Meta::Model::Node->new({handle=>'sample'});
    $node->set_props( sample_weight => $prop ); # add this property to node

# DESCRIPTION

# METHODS

- handle(), set\_handle($name)
- model(), set\_model($model\_name)
- concept(), set\_concept($concept\_obj)
- is\_required(), set\_is\_required($bool)
- value\_domain(), set\_value\_domain($type\_name)
- value\_set, set\_value\_set($value\_set\_obj)
- units(), set\_units($units\_string)
- pattern(), set\_pattern($regex\_string)
- @entities = $prop->entities()

    Objects (nodes or edges) that have this property.

- @terms = $prop->terms(), set\_terms()

    This is a convenience accessor to the terms attribute of the property's
    [value set](/perl/lib/Bento/Meta/Model/ValueSet.md), if any.

# SEE ALSO

[Bento::Meta::Model::Entity](/perl/lib/Bento/Meta/Model/Entity.md), [Bento::Meta::Model::ValueSet](/perl/lib/Bento/Meta/Model/ValueSet.md), 
[Bento::Meta::Model](/perl/lib/Bento/Meta/Model.md).

# AUTHOR

    Mark A. Jensen < mark -dot- jensen -at- nih -dot- gov >
    FNL
