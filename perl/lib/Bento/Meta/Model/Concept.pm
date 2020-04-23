package Bento::Meta::Model::Concept;
use base Bento::Meta::Model::Entity; 
use Log::Log4perl qw/:easy/;
use strict;

sub new {
  my $class = shift;
  my ($init) = @_;
  my $self = $class->SUPER::new({
    _id => undef,
    _terms => {}, # term | term represents concept (key: term.value)
    _entities => {}, # entity | entity has_concept concept (key: entity.handle)
  }, $init);
  return $self;
}

sub map_defn {
  return {
    label => 'concept',
    simple => [
      [ id => 'id' ],
     ],
    object => [
     ],
    collection => [
      [ terms => '<:represents',
        'Bento::Meta::Model::Term' => 'term' ],
      [ entities => '<:has_concept',
        ['Bento::Meta::Model::Node',
         'Bento::Meta::Model::Edge',
         'Bento::Meta::Model::Property'] => '' ]
     ]
   };
}

1;
