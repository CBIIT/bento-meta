package Bento::Meta::Model::Property;
use base Bento::Meta::Model::Entity;
use Log::Log4perl qw/:easy/;
use strict;

sub new {
  my $class = shift;
  my ($init) = @_;
  my $self = $class->SUPER::new( {
    _handle => undef,
    _model => undef,
    _value_domain => undef,
    _units => undef,
    _pattern => undef,
    _is_required => undef,
    _concept => \undef, # prop has_concept concept
    _value_set => \undef, # prop has_value_set value_set
    _entities => {}, # entity | entity has_property prop
    _tags => [],
    _propdef => {}
   }, $init );
  return $self;
}

sub map_defn {
  return {
    label => 'property',
    simple => [
      [id => 'id'],
      [handle => 'handle'],
      [model => 'model'],
      [value_domain => 'value_domain'],
      [is_required => 'is_required'],
      [units => 'units'],
      [pattern => 'pattern'],
     ],
    object => [
      [ 'value_set' => ':has_value_set>',
        'Bento::Meta::Model::ValueSet' => 'value_set' ],
      [ 'concept' => ':has_concept>',
        'Bento::Meta::Model::Concept' => 'concept'],
     ],
    collection => [
      [ 'entities' => '<:has_property',
        ['Bento::Meta::Model::Node',
         'Bento::Meta::Model::Edge'] => ''],
      ]
   };
}

sub type { shift->{_value_domain} } # alias
sub values {
  my $self = shift;
  return unless $self->value_set;
  my @ret;
  for ($self->value_set->terms) {
    push @ret, $_->value;
  }
  return @ret;
}

sub terms {
  my $self = shift;
  return unless $self->value_set;
  return $self->value_set->terms(@_);
}

sub set_terms {
  my $self = shift;
  return unless $self->value_set;
  return $self->value_set->set_terms(@_);
}

=head1 NAME

Bento::Meta::Model::Property - object that models a node or relationship property

=head1 SYNOPSIS

  $prop = Bento::Meta::Model::Property->new({ handle => 'sample_weight', 
                                              value_domain => 'number',
                                              units => 'mg',
                                              is_required => 1 });           
  $node = Bento::Meta::Model::Node->new({handle=>'sample'});
  $node->set_props( sample_weight => $prop ); # add this property to node


=head1 DESCRIPTION

=head1 METHODS

=over

=item handle(), set_handle($name)

=item model(), set_model($model_name)

=item concept(), set_concept($concept_obj)

=item is_required(), set_is_required($bool)

=item value_domain(), set_value_domain($type_name)

=item value_set, set_value_set($value_set_obj)

=item units(), set_units($units_string)

=item pattern(), set_pattern($regex_string)

=item @entities = $prop->entities()

Objects (nodes or edges) that have this property.

=item @terms = $prop->terms(), set_terms()

This is a convenience accessor to the terms attribute of the property's
L<value set|Bento::Meta::Model::ValueSet>, if any.

=back

=head1 SEE ALSO

L<Bento::Meta::Model::Entity>, L<Bento::Meta::Model::ValueSet>, 
L<Bento::Meta::Model>.

=head1 AUTHOR

 Mark A. Jensen < mark -dot- jensen -at- nih -dot- gov >
 FNL

=cut

1;
