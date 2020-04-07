package Bento::Meta::Model::EdgeType;
use base Bento::Meta::Model::Entity;
use Log::Log4perl qw/:easy/;
use strict;

sub new {
  my $class = shift;
  my ($init) = @_;
  my $self = $class->SUPER::new( {
    _handle => undef,
    _model => undef,
    _tags => [],
    _props => {},
    _multiplicity => undef,
    _ends => [],
    _edgedef => {},
  }, $init);
  return $self;
}

sub cardinality { shift->multiplicity }

1;
