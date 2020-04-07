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
    _type => undef,
    _value_set => undef, # prop has_value_set value_set
    _entities => [], # entity | entity has_property prop
    _tags => [],
    _propdef => {}
   }, $init );
  return $self;
}

1;
