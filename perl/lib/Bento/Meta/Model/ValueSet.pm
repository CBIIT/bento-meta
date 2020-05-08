package Bento::Meta::Model::ValueSet;
use base Bento::Meta::Model::Entity;
use Log::Log4perl qw/:easy/;
use strict;

sub new {
  my $class = shift;
  my ($init) = @_;
  my $self = $class->SUPER::new( {
    _handle => undef,
    _id => undef,
    _url => undef,
    _terms => {}, # term | value_set has_term term (key: term.value)
    _prop => \undef, # prop | prop has_value_set value_set
    _origin => \undef, # value_set has_origin origin
  },$init);
  return $self;
}

sub set_terms {
  my $self = shift;
  my @args = @_;
  $self->set_dirty(1);
  $self->prop->set_dirty(1) if ($self->prop); # smudge the connected property
  if (ref $args[0] eq 'HASH') {
    return $self->{_terms} = $args[0];
  } elsif (!ref($args[0]) && @args > 1) {
    if (defined $args[1]) {
      return $self->{_terms}{$args[0]} = $args[1];
    } else {                # 2nd arg is explicit undef - means delete
      return delete $self->{_terms}{$args[0]}
    }
  } else {
    LOGDIE "set_terms requires hashref as arg1, or key => term_obj as arg1 and arg2";
  }
}
sub map_defn {
  return {
    label => 'value_set',
    simple => [
      [handle => 'handle'],
      [id => 'id'],
      [url => 'url'],
     ],
    object => [
      [ prop => '<:has_value_set',
        'Bento::Meta::Model::Property' => 'property' ],
      [ origin => ':has_origin>',
        'Bento::Meta::Model::Origin' => 'origin' ]
     ],
    collection => [
      [ terms => ':has_term>',
        'Bento::Meta::Model::Term' => 'term' ]
     ]
   };
}

=head1 NAME

Bento::Meta::Model::ValueSet - object that models an enumerated set of property values

=head1 SYNOPSIS

=head1 DESCRIPTION

=head1 METHODS

=over

=item id(), set_id($id_string)

=item url(), set_id($url)

Informative URL ideally pointing to a description of the set of values.

=item terms(), set_terms( $term_value => $term_obj)

The terms aggregated by the value set.

=item prop()

The property (object) whose value set this is.

=item origin, set_origin($origin_obj)

Origin object represnting the source authority of the term set, if any.

=back

=head1 AUTHOR

 Mark A. Jensen < mark -dot- jensen -at- nih -dot- gov >
 FNL

=cut

  1;
