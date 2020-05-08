package Bento::Meta::Model::Node;
use lib '../../../../lib';
use base Bento::Meta::Model::Entity;
use Log::Log4perl qw/:easy/;
use strict;

sub new {
  my $class = shift;
  my ($init) = (@_);
  my $self = $class->SUPER::new({
    _handle => undef,
    _model => undef,
    _concept => \undef, # node has_concept concept
    _category => undef,
    _tags => [],
    _props => {}, # prop | node has_property prop (key: prop.handle)
  },$init);
  return $self;
}

sub map_defn {
  return {
    label => 'node',
    simple => [
      [id => 'id'],
      [handle => 'handle'],
      [model => 'model'],
     ],
    object => [
      [concept => ':has_concept>',
       'Bento::Meta::Model::Concept' => 'concept']
     ],
    collection => [
      [props => ':has_property',
       'Bento::Meta::Model::Property' => 'property']
     ]
   };
}1;

=head1 NAME

Bento::Meta::Model::Node - object that models a data node for a model

=head1 SYNOPSIS

  $init = { handle => 'case',
            model => 'test_model' };
  $node = Bento::Meta::Model::Node->new($init);

=head1 DESCRIPTION

=head1 METHODS

=over

=item handle(), set_handle($name)

=item model(), set_model($model_name)

=item concept(), set_concept($concept_obj);

=item @props = $node->props, set_props( $prop_name => $prop_obj )

=back

=head1 SEE ALSO

L<Bento::Meta::Model::Entity>, L<Bento::Meta::Model>.

=head1 AUTHOR

 Mark A. Jensen < mark -dot- jensen -at- nih -dot- gov >
 FNL

=cut

1;
