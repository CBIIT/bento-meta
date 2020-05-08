# NAME

Bento::Meta::Model::Edge - object that models an edge or relationship

# SYNOPSIS

    $case = Bento::Meta::Model::Node->new({handle=>'case'});
    $sample = Bento::Meta::Model::Node->new({handle=>'sample'});
    $edge = Bento::Meta::Model::Edge->new({ handle=>'of_case',
                                            src => $sample,
                                            dst => $case });

# DESCRIPTION

# METHODS

- handle(), set\_handle($name)
- model(), set\_model($model\_name)
- concept(), set\_concept($concept\_obj)
- is\_required(), set\_is\_required($bool)
- @props = $edge->props, set\_props( $prop\_name => $prop\_obj )
- multiplicity(), cardinality()

    Whether the edge from src to dst is one\_to\_one, one\_to\_many, many\_to\_one, or
    many\_to\_many.

- triplet()

    This is a string giving the edge type, source node label, and destination 
    node label, separated by colons. 

        print $edge->triplet; # of_case:diagnosis:case

    Helpful for finding a particular edge.

        $diag_to_case = grep { $_->triplet eq 'of_case:diagnosis:case' } $model->edges;

# SEE ALSO

[Bento::Meta::Model::Entity](/perl/lib/Bento/Meta/Model/Entity.md), [Bento::Meta::Model](/perl/lib/Bento/Meta/Model.md).

# AUTHOR

    Mark A. Jensen < mark -dot- jensen -at- nih -dot- gov >
    FNL
