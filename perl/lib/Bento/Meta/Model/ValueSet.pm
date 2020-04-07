package Bento::Meta::Model::ValueSet;
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
    _prop => undef, # prop | prop has_value_set value_set
    
  },$init);
  return $self;
}


1;
