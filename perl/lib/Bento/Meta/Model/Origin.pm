package Bento::Meta::Model::Origin;
use base Bento::Meta::Model::Entity;
use Log::Log4perl qw/:easy/;
use strict;

sub new {
  my $class = shift;
  my ($init) = @_;
  my $self = $class->SUPER::new( {
    _name => undef,
    _url => undef,
    _is_external => undef,
    _entities => [], # entity | entity has_origin origin
  }, $init );
  
  return $self;
}


1;
