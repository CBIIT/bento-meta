package Bento::Meta::Model::Concept;
use base Bento::Meta::Model::Entity; 
use Log::Log4perl qw/:easy/;
use strict;

sub new {
  my $class = shift;
  my ($init) = @_;
  my $self = $class->SUPER::new({
    _id => undef,
    _terms => {}, # term | term has_concept concept (key: term.value)
  }, $init);
  return $self;
}


1;
