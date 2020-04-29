package TestObject;
use base Bento::Meta::Model::Entity;
use strict;

sub new {
  my $class = shift;
  my ($init) = @_;
  my $self = $class->SUPER::new( {
    _my_scalar_attr => undef,
    _my_object_attr => \undef,
    _my_array_attr => [],
    _my_hash_attr => {},
    }, $init );
}
1;
