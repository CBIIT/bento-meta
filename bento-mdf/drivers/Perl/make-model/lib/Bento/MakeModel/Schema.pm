package Bento::MakeModel::Schema;
use v5.10;
use feature qw/state/;
use lib '../../../lib';
use Carp qw/croak/;
use Log::Log4perl qw/:easy/;
use Bento::MakeModel::Config;
use JSON::PP;
use YAML::PP;
use YAML::PP::Dumper;
use YAML::PP::Emitter;
use Try::Tiny;
use Tie::IxHash;
use Lingua::EN::Inflexion;
use Clone qw/clone/;
use strict;
use warnings;

# object to represent a single node's schema
my $ys = YAML::PP->default_schema( boolean => 'JSON::PP' );
$ys->add_representer(
  tied_equals => 'Tie::IxHash',
  code => sub {
    my ($rep, $node) = @_;
    $node->{items} = [ %{ $node->{data} } ];
    return 1;
  },
 );
  
our $yaml_dumper = YAML::PP::Dumper->new( schema => $ys,);
sub new {
  my $class = shift;
  my ($name, @args) = @_;
  unless (defined $name) {
    FATAL "name required as arg 1";
    die "Caller error";
  }
  my $self = bless {
    _name => $name,
    _root => {},
    _key_order => {},
    _required_props => [],
    _link_props => [], 
    _unique_keys => [],
    _dirty => 1,
  }, $class;
  $self->_append_key_order('/',\@TOP_LEVEL_KEY_ORDER);
  $self->_build_header(@args)->_add_standard_properties;
  return $self;
}

sub new_from_native_yaml {
  my $class = shift;
  my ($filename) = @_;
  unless (defined $filename && -e $filename) {
    FATAL "existing yaml filename required as arg1";
    die "Caller error";
  }
  my $self = bless {
     _root => {},
    _key_order => {},
  }, $class;    
  my $ypp = YAML::PP->new(boolean => 'JSON::PP');
  try {
    $self->{_root} = $ypp->load_file($filename);
  } catch {
    ERROR "Problem in native yaml file '$filename':\n$_";
    return;
  };
  unless ($self->{_name} = $self->{_root}{id}) {
    ERROR "Native Gen3 yaml file '$filename' has no 'id' field, skipping";
    return;
  }
  return $self;
}

sub root { shift->{_root} }
sub name { shift->{_name} }

sub as_yaml {
  # job is to create a Perl structure with
  # ordered hashes (Tie::IxHash) wherever
  # there is a need, as indicated by 
  # $self->{_key_order}.
  # Then send structure off to YAML::Dump.
  my $self = shift;
  if ($self->{_dirty}) {
    ERROR "Beware of the output: schema for '$$self{name}' not _finalized";
  }
  return $yaml_dumper->dump_string($self->as_ordered_object);
}



sub as_ordered_object {
  my $self = shift;
  my $walk;
  $walk = sub {
    my ($self, $adr, $ptr) = @_;
    my $order = $self->{_key_order}{$adr};
    if ((ref $ptr eq '') || (ref($ptr) =~ /^JSON::PP/)) {
      return $ptr; # scalar value
    }
    elsif (ref $ptr eq 'HASH') {
      tie my %h, 'Tie::IxHash';
      $order //= [keys %$ptr];
      for my $k (@$order) {
	$h{$k} = $walk->($self, $adr."$k/",$ptr->{$k});
      }
      return \%h;
    }
    elsif (ref $ptr eq 'ARRAY') {
      my ($i,$a);
      $a = [];
      for ($i=0;$i<@$ptr;$i++) {
	$a->[$i] = $walk->($self, $adr."[$i]/",$ptr->[$i]);
      }
      return $a;
    }
    else {
      FATAL "Can't handle ref type ".ref($ptr);
      die "YAML production error";
    }
  };
  return $walk->($self,'/',$self->root);
}

sub _build_header {
  my $self = shift;
  my %args = @_;
  $self->{_dirty} = 1;
  ## HARDCODING HEADER
  $self->root->{'$schema'} = "http://json-schema.org/draft-04/schema#";
  $self->root->{id} = $self->name;
  $self->root->{title} = $self->name; $self->root->{title} =~ s/^(.)/\U$1\E/;
  $self->root->{type} = 'object';
  $self->root->{namespace} = $GEN3_NS;
  $self->root->{category} = $args{Category} // $DEFAULT_NODE_CATEGORY;
  $self->root->{program} = '*';
  $self->root->{project} = '*';
  $self->root->{description} = "";
  $self->root->{uniqueKeys} = [ ['id'] ];
  if ($args{UniqueKeys}) {
    push @{$self->root->{uniqueKeys}}, @{clone($args{UniqueKeys})};
  }
  $self->root->{additionalProperties} = JSON::PP::false;
  $self->root->{submittable} = JSON::PP::true;
  $self->root->{validators} = undef;
  $self->root->{systemProperties} = $STANDARD_SYSTEM_PROPERTIES;
  return $self;
}

sub _add_standard_properties {
  my $self = shift;
  $self->{_dirty} = 1;
  $self->_append_key_order('/properties/',[qw/type id state/]);
  $self->root->{properties}{submitter_id} = {type=>['string','"null"']};
  $self->root->{properties}{type}{enum} = [$self->name];

  $self->root->{properties}{$_} = $STANDARD_SYSTEM_PROPDEFS->{$_} for @$STANDARD_SYSTEM_PROPERTIES;

  return $self;
}

# arrays to store output order of object keys
sub _append_key_order {
  my $self = shift;
  my ($address, $keyary) = @_;
  push @{$self->{_key_order}{$address}}, @$keyary;
  return $self;
}

# _add_links( {<relname> => [ {Src=><this_node_name>,Dst=>...,
#                              Mul=><many_to_one|one_to_one|one_to_many>,
#                              Req=><bool_true|bool_false>}, {...}]}
sub _add_links {
  my $self = shift;
  my ($relns) = @_;
  $self->{_dirty} = 1;
  my $i=0;
  $self->root->{links} = [];
  for my $rtype (keys %$relns) {
    for my $rinfo (@{$relns->{$rtype}}) {
      $self->_append_key_order("/links/[$i]/",
			       [qw/ name backref label target_type multiplicity required /]);
      $i++;
      if ($rinfo->{Mul} and $rinfo->{Mul} !~ /(?:many|one)_to_(?:many|one)/) {
	WARN "Don't understand multiplicity '$$rinfo{Mul}', using default '$MULT_DEFAULT'";
	$rinfo->{Mul} = $MULT_DEFAULT;
      }
      my $link = 
	{
	  name => noun($rinfo->{Dst})->plural,
	  backref => noun($rinfo->{Src})->plural,
	  label => $rtype,
	  target_type => $rinfo->{Dst},
	  multiplicity => $rinfo->{Mul} // $MULT_DEFAULT,
	  required => defined $rinfo->{Req} ? ( $rinfo->{Req} ? JSON::PP::true : JSON::PP::false ) :
	    $PROP_REQ_DEFAULT,
	};
      push @{$self->root->{links}}, $link;
      my $multype = ( $link->{multiplicity} =~ /to_one$/ ? 'to_one' : 'to_many');
      push @{$self->{_link_props}}, { $link->{name} => { '$ref' => "_definitions.yaml#/$multype" } };
      if ($link->{required}) {
	push @{$self->{_required_props}}, $link->{name};
      }

    }
  }

  return $self;
}

# interpret the input property definition here
# add all properties to the {properties} structure,
# push prop name onto {systemProperties} if 'sys' is
# the indicated proptype
sub _add_property {
  my $self = shift;
  my $proptype = shift;
  my ($prop, $pdef) = @_;
  unless ($proptype =~ /^sys|std$/) {
    FATAL "arg 1 must be property type: 'sys' or 'std'";
    croak "Caller error";
  }
  $self->{_dirty} = 1;
  my $schema_prop_struct = {};
  $self->_append_key_order("/properties/",[$prop]);
  if (defined $pdef) {
    if ($pdef->{Enum}) { # Enum specified, ignore Type
      unless (ref $pdef->{Enum} eq 'ARRAY') {
	FATAL "Enum for property '$prop' must be specified as a list";
	die "Input yaml error";
      }
      $schema_prop_struct->{enum} = $pdef->{Enum};
    }
    elsif ($pdef->{Type}) {
      $schema_prop_struct->{type} = ($pdef->{Nul} ? [ $pdef->{Type}, "null" ] : $pdef->{Type});
    }
    else {
      WARN "Definition of property '$prop' for node '$$self{_name}' does not specify type; using default $PROP_TYPE_DEFAULT";
      $schema_prop_struct->{type} = $PROP_TYPE_DEFAULT;
    }
    if ($pdef->{Term}) {
      $schema_prop_struct->{term} = {'$ref' => "_terms.yaml#/$$pdef{Term}"};
    }
    else {
      if ($ADD_TERM_REF_BY_DEFAULT) {
	$schema_prop_struct->{term} = {'$ref' => "_terms.yaml#/$prop"};
      }
    }
    if ($pdef->{Req}) {
      push @{$self->{_required_props}}, $prop;
    }
  }
  else { # default property config
    $schema_prop_struct->{type} = $PROP_NULLABLE_DEFAULT ? [$PROP_TYPE_DEFAULT, "null"] : $PROP_TYPE_DEFAULT;
  }
  $self->root->{properties}{$prop} = $schema_prop_struct;
  if ($proptype eq 'sys') {
    push(@{$self->root->{systemProperties}}, $prop) unless grep /^$prop$/,@{$self->root->{systemProperties}};
  }
  return $self;
}

sub _add_std_property { shift->_add_property('std', @_) }
sub _add_sys_property { shift->_add_property('sys', @_) }

sub _finalize_schema {
  my $self = shift;
  # task here: create required properties object from $self->{_required_props}, after
  # _add_property and _add_links runs have recorded the requirements there
  $self->root->{required} = $self->{_required_props};
  # unique keys
  push @{$self->root->{uniqueKeys}}, @{$self->{_unique_keys}};
  # links as properties
  if (@{$self->{_link_props}}) {
    for my $p (@{$self->{_link_props}}) {
      for (keys %$p) {
	$self->_append_key_order('/properties/', [$_]);
	$self->root->{properties}{$_} = $p->{$_};
      }
    }
  }
  # system properties
  # TODO
  
  $self->{_dirty} = 0;
  return $self;
}

=head1 NAME

Bento::MakeModel::Schema - Representation of a "Gen3" dictionary document

=head1 SYNOPSIS

 $n = Bento::MakeModel::Schema->new('nodename');
 # boilerplate header and properties already in $n
 $n->_add_links({ has_goob => [{ Src => 'nodename', Dst => 'other_node',
                                 Mul => 'many_to_one', Req => 1 },
			       { Src => 'nodename', Dst => 'different_node',
			         Mul => 'one_to_one', Req => 0 }] } );
 $n->_add_std_property('prop1' => { Type => 'string', Req => 0,
                                Term => 'prop1', ... });
 $n->_finalize_schema;
 print $n->as_yaml;

=head1 DESCRIPTION

L<Bento::MakeModel::Schema> objects represent and output the actual
data structures needed to configure the "Gen3" data model.

=head1 AUTHOR

 Mark A. Jensen < mark -dot- jensen -at- nih -dot- gov >
 FNLCR

=cut

1;
