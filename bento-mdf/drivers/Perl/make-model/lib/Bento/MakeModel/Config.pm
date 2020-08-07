package Bento::MakeModel::Config;
use base Exporter;
use Log::Log4perl::Level;
use JSON::PP;
use strict;
use warnings;

our @EXPORT = qw/ @TOP_LEVEL_KEY_ORDER $GEN3_NS $DEFAULT_NODE_CATEGORY $MULT_DEFAULT
		  $STANDARD_SYSTEM_PROPERTIES $STANDARD_SYSTEM_PROPDEFS
		  $PROP_REQ_DEFAULT $PROP_TYPE_DEFAULT $PROP_NULLABLE_DEFAULT
		  $ADD_TERM_REF_BY_DEFAULT $LOG_LEVEL
		  $OVERLAY_MERGE_BEH $files
/;
our $LOG_LEVEL = $INFO;

our @TOP_LEVEL_KEY_ORDER = qw/
  $schema
  id
  title
  type
  namespace
  category
  program
  project
  description
  additionalProperties
  submittable
  validators
  systemProperties
  links
  required
  uniqueKeys
  properties
			     /;

our $MULT_DEFAULT = 'many_to_one';
our $STANDARD_SYSTEM_PROPERTIES = [qw/id state created_datetime updated_datetime/];
our $STANDARD_SYSTEM_PROPDEFS = {
  id => { '$ref' => '_definitions.yaml#/UUID',
	  systemAlias => 'node_id' },
  state => { '$ref' => '_definitions.yaml#/state' },
  created_datetime => { '$ref' => '_definitions.yaml#/datetime' },
  updated_datetime => { '$ref' => '_definitions.yaml#/datetime' },  
};
our $PROP_REQ_DEFAULT = 0;
our $PROP_TYPE_DEFAULT = 'string';
our $PROP_NULLABLE_DEFAULT = 0;
our $GEN3_NS = 'https://icdc.nci.nih.gov';
our $DEFAULT_NODE_CATEGORY = 'administrative';
our $ADD_TERM_REF_BY_DEFAULT = 0;
our $files = [];
# custom behavior for Hash::Merge: act like Left Precedence, except allow
# hash key conflicts to be resolved from the right ("overlay")
our $OVERLAY_MERGE_BEH = {
  'SCALAR' => {
    'SCALAR' => sub { $_[1] },
    'ARRAY'  => sub { $_[1] },
    'HASH'   => sub { $_[1] },
  },
  'ARRAY' => {
    'SCALAR' => sub { [grep(/^$_[1]$/,@{$_[0]}) ? @{$_[0]} : (@{$_[0]}, $_[1]) ] },
    'ARRAY'  => sub{my $a = [@{$_[0]}] ; map { my $c = $_ ; push(@$a, $c) unless grep { $c eq $_ } @{$_[0]} } @{$_[1]}; $a},
    'HASH'   => sub { $_[1] },
  },
  'HASH' => {
    'SCALAR' => sub {  warn "Input merge: overwriting hash with scalar value"; $_[1] },
    'ARRAY'  => sub { warn "Input merge: overwriting hash with an array"; $_[1] },
    'HASH'   => sub { Hash::Merge::_merge_hashes($_[0], $_[1]) },
  }
};


1;
