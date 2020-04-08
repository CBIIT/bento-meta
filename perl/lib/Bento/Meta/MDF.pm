package Bento::Meta::MDF;
use lib '../../lib';
use Bento::Meta::Model;
use JSON::ize;
use Log::Log4perl qw/:easy/;
use Clone qw/clone/;
use YAML::PP qw/LoadFile/;
use Hash::Merge;

our $MERGER = Hash::Merge->new();
$MERGER->add_behavior_spec( OVERLAY_MERGE_BEH, 'R_OVERLAY' );
$MERGER->set_behavior('R_OVERLAY');

our $DEFAULT_MULT = 'one_to_one';
our @DEFAULT_TYPE = (value_domain => 'TBD');

our $re_url = qr{^(?:https?|bolt)://};

sub create_model {
  my $class = shift;
  my ($handle, @files) = @_;
  my $self = bless {
    _yaml => undef,
    _handle => $handle,
   }, $class;
  unless ($handle) {
    LOGDIE "$class::create_model : req model handle as arg1, followed by yaml files";
  }
  if (-e $handle and $handle =~ /ya?ml/) {
    LOGWARN "$class::create_model : arg1 looks like a filename (expecting model handle";
  }
  unless (@files) {
    LOGDIE "$class::create_model: req list of files as args";
  }
  $self->read_yaml(@files);
  my $ynodes = $self->yaml->{Nodes};
  my $yedges = $self->yaml->{Relationships};
  my $ypropdefs = $self->yaml->{PropDefinitions};
  
  my $model = Bento::Meta::Model->new($handle);

  #create nodes and properties
  for my $h ( keys %$ynodes ) {
    my $yn = $ynodes->{$h};
    my $n = $model->add_node({
      handle => $h,
      model => $handle,
      ($yn->{Tags} ?
         tags => clone($yn->{Tags}) :
         ()),
      ($yn->{Category} ?
         category => $yn->{Category} :
         ())
      ($yn->{Desc} ?
         desc => $yn->{Desc} :
         ())        
     });
  }

  #create edges and properties
  for my $t ( keys %$yedges ) {
    my $ye = $yedges->{$t};
    for my $ends (@{$ye->{Ends}}) {
      $model->add_edge({
        handle => $t,
        model => $self->handle,
        src => $model->node($ends->{Src}),
        dst => $model->node($ends->{Dst}),
        multiplicity => $ends->{Mul} // $ye->{Mul} // $DEFAULT_MULT,
        is_required => $ends->{Req} // $ye->{Req},
        ( $ends->{Tags} // $ye->{Tags} ?
            tags => clone($ends->{Tags} // $ye->{Tags}) :
            () ),
        ( $ends->{Desc} // $ye->{Desc} ?
            desc => clone($ends->{Desc} // $ye->{Desc}) :
            () )        
      });
    }
  }

  # create node properties
  for my $w ($model->nodes, $model->edges) {
    my @ph;
    if (ref $w =~ /Node$/) {
      @ph = @{$ynodes->{$w->handle}{Props}};
    }
    elsif (ref $w =~ /Edge$/) {
      # Props elt appearing in Ends hash
      # takes precedence over Props elt
      # in the handle's hash
      my ($hdl,$src,$dst) = split /:/,$w->triplet;
      my ($ends_props) = grep
        { ($_->{Src} eq $src) &&
          ($_->{Dst} eq $dst) } @{$yedges->{$hdl}{Ends}};
      @ph = @{$ends_props // $yedges->{$hdl}{Props}};
    }
    for my $ph (@ph) {
      my $ypdef = $ypropdefs->{$ph};
      my %init = (
        handle => $ph,
        model => $self->handle,
        ($ypdef->{Tags} ?
           tags => clone($ypdef->{Tags}) :
           ()),
        ($ypdef->{Type} ?
           ($self->_value_domain($ypdef->{Type})) :
           @DEFAULT_TYPE),
       );
      my $p = Bento::Meta::Model::Property->new(\%init);
      $model->add_prop($w, $p);
    }
  }
  
  #create edge properties

}

sub yaml { shift->{_yaml} }
sub handle { shift->{_handle} }

sub read_yaml {
  my ($self, @files) = @_;
  $self->{_yaml} = {};
  INFO "Input files: ".join(',',@files);
  for my $pth (@files) {
    my $pth_o = LoadFile($pth);
    my @dels = _delete_paths($pth_o);
    $self->{_yaml} = $MERGER->merge( $self->{_yaml}, $pth_o);
    if (@dels) {
      _do_deletes($self->{_input_yaml}, \@dels);
    }
  }

  unless ($self->{_yaml}{Nodes}) {
    LOGDIE "No nodes defined";
  }
  unless ($self->{_yaml}{Relationships}) {
    LOGDIE "No relationships defined";
  }
  unless ($self->{_yaml}{PropDefinitions}) {
    LOGWARN "No property definitions included";
  }
  return $self;
}

# _value_domain( $p->{Type} ) : returns plain even-sized array
sub _value_domain {
  my $self = shift;
  my ($type) = @_;
  for (ref $type) {
    /^HASH$/ && do {
      if ($type->{pattern}) {
        return ( value_domain => 'regexp',
                 pattern => $type->{pattern} );
      }
      elsif ($type->{units}) {
        return ( value_domain => $type->{value_type},
                 units => join(';',@{$type->{units}}) );
      }
      else {
        # punt: return JSON string of the hash
        LOGWARN "MDF type descriptor unrecognized: ".J($type);
        return ( value_domain => J($type) );
      }
      last;
    };
    /^ARRAY$/ && do {
      my $vs = Bento::Meta::Model::ValueSet->new();
      $vs->set_id( $vs->make_uuid );
      $vs->set_handle( $self->handle.substr($vs->id,0,7) );
      if ($type->[0] =~ /$re_url/) { #looks like url
        $vs->set_url($type->[0]);
      }
      else { # enum
        my %t;
        for my $val (@$type) {
          $t{$val} = Bento::Meta::Model::Term->new({
            value => $val,
            # don't create id here
           });
        }
        $vs->set_terms(\%t);
      }
      return ( value_domain => 'value_set',
               value_set => $vs );
      last;
    };
    do { # scalar
      return ( value_domain => $type ); # type string
    };
  }
}

sub _delete_paths {
  my ($pth_o) = @_;
  my $walk;
  my @dpths;
  $walk = sub {
    my ($adr, $ptr) = @_;
    unless (defined $ptr) {
      return;
    }
    if (ref $ptr eq '' or ref($ptr) =~ /^JSON::PP/) { # scalar
      if ($ptr =~ m|^/(.*)|) { # delete char present on value
	push @dpths, [$adr,$1];
      }
      else {
	1; # done at leaf
      }
    }
    elsif (ref $ptr eq 'HASH') {
      for my $k (keys %{$ptr}){
	if ( $k =~ m|^/(.*)| ) { # delete char present on key
	  push @dpths, [$adr."\{$1\}", $1]; # prune from here
	}
	else {
	  $walk->($adr."\{$k\}", $ptr->{$k});
	}
      }
    }
    elsif (ref $ptr eq 'ARRAY') {
      for my $i (0..$#$ptr) {
	$walk->($adr."\[$i\]",$ptr->[$i]);
      }
    }
    else {
      FATAL "Can't handle ref type ".ref($ptr);
      die "YAML read error";
    }
  };
  $walk->('',$pth_o);
  return @dpths;
}

sub _do_deletes {
  my ($y, $dels) = @_;
  for my $d (@$dels) {
    next unless (@$d == 2);
    if ($$d[0] =~ /}$/) {
      if (eval "exists \$y->$$d[0];") {
	eval "delete \$y->$$d[0];";
      }
      else {
	ERROR "Delete of non-existent key requested: '$$d[0]'";
      }
      $$d[0] =~ s|($$d[1])\}$|'/$1'}|;
      eval "delete \$y->$$d[0];";
    }
    elsif ($$d[0] =~ /\]$/) {
      # get address of the array itself
      $$d[0] =~ s/\[[0-9]+\]$//;
      my $ary = eval "\$y->$$d[0]";
      @{$ary} = grep !/^\/?$$d[1]$/,@$ary; # remove element and delete indicator
      1;
    }
    else {
      FATAL "Don't understand delete path '$$d[0]'";
    }
  }
}
# custom behavior for Hash::Merge: act like Left Precedence, except allow
# hash key conflicts to be resolved from the right ("overlay")
sub OVERLAY_MERGE_BEH () {
  return {
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
   }
}
;

=head1 NAME

Bento::Meta::MDF - Create model objects from model description files

=head1 SYNOPSIS

 $model = Bento::Meta::MDF->create_model(@mdf_files);
 # $model isa Bento::Meta::Model

=head1 DESCRIPTION

L<Bento::Meta::MDF> defines a L<Bento::Meta::Model> factory, C<create_model()>,
that accepts model description files as specified at L<bento-mdf|https://github.com/CBIIT/bento-mdf>.

In particular, it follows the merging protocol describes at
L<https://github.com/CBIIT/bento-mdf#multiple-input-yaml-files-and-overlays>.

=head1 AUTHOR

 Mark A. Jensen <mark -dot- jensen -at- nih -dot- gov>
 FNL

=cut

1;
  
