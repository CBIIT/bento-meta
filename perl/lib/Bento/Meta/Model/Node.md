# NAME

Bento::Meta::Model::Node - object that models a data node for a model

# SYNOPSIS

    $init = { handle => 'case',
              model => 'test_model' };
    $node = Bento::Meta::Model::Node->new($init);

# DESCRIPTION

# METHODS

- handle(), set\_handle($name)
- model(), set\_model($model\_name)
- concept(), set\_concept($concept\_obj);
- @props = $node->props, set\_props( $prop\_name => $prop\_obj )

# SEE ALSO

[Bento::Meta::Model::Entity](/perl/lib/Bento/Meta/Model/Entity.md), [Bento::Meta::Model](/perl/lib/Bento/Meta/Model.md).

# AUTHOR

    Mark A. Jensen < mark -dot- jensen -at- nih -dot- gov >
    FNL
