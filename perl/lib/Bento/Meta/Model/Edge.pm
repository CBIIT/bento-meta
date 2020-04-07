package Bento::Meta::Model::Edge;
use base Bento::Meta::Model::Entity;
use Log::Log4perl qw/:easy/;
use strict;

# one edge per type:src:dst triplet
sub new {
  my $class = shift;
  my ($init) = @_;
  my $self =  $class->SUPER::new({
    _handle => undef,
    _model => undef,
    _multiplicity => undef,
    _src => undef,
    _dst => undef,
    _is_required => undef,
    _type => undef,
    _concept => undef,
    _tags => [],
    _props => {}, # prop | edge has_property prop (key: prop.handle)
  }, $init);

  return $self;
}

sub cardinality { shift->multiplicity(@_) }
1;
