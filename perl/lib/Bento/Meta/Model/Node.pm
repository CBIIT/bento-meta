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
    _concept => undef, # node has_concept concept
    _category => undef,
    _tags => [],
    _props => {}, # prop | node has_property prop (key: prop.handle)
  },$init);
  return $self;
}
             
1;
