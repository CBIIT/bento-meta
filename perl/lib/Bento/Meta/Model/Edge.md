# NAME

Bento::Meta::Model::Edge - object that models an edge or relationship

# SYNOPSIS

# DESCRIPTION

# METHODS

- multiplicity(), cardinality()

    Whether the edge from src to dst is one\_to\_one, one\_to\_many, many\_to\_one, or
    many\_to\_many.

- triplet()

    This is a string giving the edge type, source node label, and destination 
    node label, separated by colons. 

        print $edge->triplet; # of_case:diagnosis:case

    Helpful for finding a particular edge.

        $diag_to_case = grep { $_->triplet eq 'of_case:diagnosis:case' } $model->edges;

# AUTHOR

    Mark A. Jensen < mark -dot- jensen -at- nih -dot- gov >
    FNL
