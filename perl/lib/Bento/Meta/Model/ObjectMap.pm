package Bento::Meta::Model::ObjectMap;
use lib '../lib';
use Scalar::Util qw/blessed/;
use Neo4j::Bolt;
use Neo4j::Cypher::Abstract qw/cypher ptn/;
use Log::Log4perl qw/:easy/;
use strict;
our %Cache;

sub new {
  my $class = shift;
  my ($obj_class, $label, $bolt_cxn) = @_;
  unless ($obj_class) {
    LOGDIE "${class}::new : require an object class (string) for arg1";
  }
  # ck obj_class
  unless (defined $label) {
    ($label) = $obj_class =~ /::([^:]+)$/;
    $label = lc $label;
  }
  my $self = bless {
    _class => $obj_class,
    _label => $label,
    _bolt_cxn => $bolt_cxn,
    _property_map => {},
    _relationship_map => {},
   }, $class;
  
  return $self;
}


sub class { shift->{_class} }
sub label { shift->{_label} }
sub bolt_cxn { @_ > 1 ? ($_[0]->{_bolt_cxn} = $_[1]) : $_[0]->{_bolt_cxn} }
sub pmap { shift->{_property_map} }
sub rmap { shift->{_relationship_map} }

sub property_attrs {
  return keys %{ shift->pmap }
}
sub relationship_attrs {
  return keys %{ shift->rmap }
}

sub map_simple_attr {
  my $self = shift;
  my ($attr, $property) = @_;
  # ck args
  return $self->{_property_map}{$attr} = $property;
}1;

# relationship - specify as in cypher::abstract format
# so "<:rlnship" means <-[:rlnship]-
# and  ":rlnship>" means -[:rlnship]->
# if just "rlnship", add colon and assume no dir

sub map_object_attr {
  my $self = shift;
  my ($attr, $relationship, $end_class, $end_label) = @_;
  # ck args
  $relationship = ":$relationship" unless ($relationship =~ /:/);
  return $self->{_relationship_map}{$attr} =
    { rel => $relationship,
      lbl => $end_label,
      cls => $end_class,
      many => 0 };
}1;

sub map_collection_attr {
  my $self = shift;
  my ($attr, $relationship, $end_class, $end_label) = @_;
  # ck args
  $relationship = ":$relationship" unless ($relationship =~ /:/);  
  return $self->{_relationship_map}{$attr} =
    { rel => $relationship,
      lbl => $end_label,
      cls => $end_class,
      many => 1};
}1;

# get - pull a node from db and populate obj
# : reads the node having the same neoid as is set on object
# : sets simple attrs with node properties
# : loads approp classed objects into object, collection attr
# :  - related objects are created and their simple attrs are set,
# :  - but their object- and collection-valued attrs are not loaded
# :  - this status is indicated by their dirty attr == -1
# get will pull from cache unless obj is partially loaded, or
# refresh is requested (arg == true)

sub get {
  my $self = shift;
  my ($obj, $refresh) = @_;
  unless ($self->bolt_cxn) {
    LOGWARN ref($self)."::get - ObjectMap has no db connection set";
    return;
  }
  my $c = $Cache{$obj->neoid};
  $refresh = 1 if $c && ($c->dirty < 0); # cached obj is only partially pulled
  if ($c && !$refresh) { # return (poss. shallow copy of) cached object
    return $obj if ($c == $obj);
    for (keys %{$obj}) {
      $obj->{$_} = $c->{$_};
    }
    return $obj;
  }
  # fully pull obj
  my $rows = $self->bolt_cxn->run_query(
    $self->get_q( $obj )
   );
  return _fail_query($rows) if ($rows->failure);
  my ($n,$n_id) = $rows->fetch_next;
  unless ($n) {
    LOGWARN ref($self)."::get - corresponding db node not found";
    return;
  }
  my $cls = $self->class;
  unless (eval "require $cls;1") {
    LOGDIE ref($self)."::get : unable to load class $cls: $@";
  }  
  $obj->set_with_node($n);
  # $obj->set_neoid($n_id);
  $Cache{$obj->neoid} = $obj;
  for my $attr ($self->relationship_attrs) {
    $rows = $self->bolt_cxn->run_query(
      $self->get_attr_q( $obj => $attr)
     );
    return _fail_query($rows) if ($rows->failure);
    my @values;
    $cls = $self->rmap->{$attr}{cls};
    if (!ref($cls)) {
      unless (eval "require $cls;1") {
        LOGDIE ref($self)."::get : unable to load class $cls: $@";
      }
    }
    else {
      for my $c (@$cls) {
        unless (eval "require $c;1") {
          LOGDIE ref($self)."::get : unable to load class $cls: $@";
        }
      }
    }
    while ( my ($a,$a_id) = $rows->fetch_next ) {
      my $o = $Cache{$a->{id}};
      my $c;
      if (!ref($cls)) {
        $c = $cls;
      }
      else {
        ($c) = grep { my $lbl = $_->map_defn->{label} ;
                      grep /^$lbl$/, @{$a->{labels}} } @$cls;
      }
      unless ($o) {
        $o = $c->new($a);
        $o->set_dirty(-1); # means this object has not got its object-valued attrs yet
        $Cache{$o->neoid} = $o;
      }
      push @values, $o;
    }
    my $set = "set_$attr";
    for ($obj->atype($attr)) {
      /^ARRAY$/ && do {
        $obj->$set(\@values);
        last;
      };
      /^HASH$/ && do {
        #this is a kludge - better would be a way to configure
        #a hash attribute to indicate which scalar attr of the value object
        #should be the hash key
        my @cur_k = keys %{$obj->$attr};
        my %cur_k;
        @cur_k{@cur_k} = @cur_k;
        for my $o (@values) {
          my ($k) = grep /^handle|value$/, $o->attrs;
          ($k) = grep (/^id$/, $o->attrs) unless length $k;
          LOGDIE "No hashkey found for object ".ref($o) unless length $k;
          delete $cur_k{$o->$k};
          LOGWARN("Hash attribute key not found on object") unless $k;
          $obj->$set( $o->$k => $o );
        }
        for (values %cur_k) { # keys on current obj with no value in db
          $obj->$set( $_ => undef ); 
        }
        last;
      };
      do { # scalar
        $obj->$set($values[0]);
      };
    }
  }
  $obj->set_dirty(0); # this object up to date with db
  return $obj;
}

# put - write an object and its attributes to the database
# - if object is mapped (has a Neo4j id), overwrite the db properties
# - with the attributes on the obj
# - if object is unmapped, create a new node in the db
# - for object-valued attributes, create relationships and nodes for the 
# - target objects in the database as necessary. Don't duplicate existing
# - relationships or target nodes.
# put only adds items to db, doesn't remove them. Explicitly remove items
# with rm()

sub put {
  # all this should be in one transaction.
  my $self = shift;
  my ($obj) = @_;
  unless ($self->bolt_cxn) {
    LOGWARN ref($self)."::put - ObjectMap has no db connection set";
    return;
  }
  my @stmts = $self->put_q($obj);
  my $rows;
  for my $q (@stmts) {
    $rows = $self->bolt_cxn->run_query($q);
    return _fail_query($rows) if ($rows->failure);
  }
  my ($n_id) = $rows->fetch_next;
  LOGWARN "No neo4j id retrieved" unless ($n_id);
  $obj->set_neoid($n_id);
  for my $attr ($self->relationship_attrs) {
    my @values = $obj->$attr;
    next unless @values;
    for my $v (@values) {
      next unless defined $v;
      unless ($v->neoid) { # create unmapped subordinate nodes
        @stmts = $v->put_q;
        for my $q (@stmts) {
          $rows = $self->bolt_cxn->run_query($q);
          return _fail_query($rows) if ($rows->failure);
        }
        my ($v_id) = $rows->fetch_next;
        LOGWARN "No neo4j id retrieved" unless ($v_id);
        $v->set_neoid($v_id);
        $Cache{$v->neoid} = $v; # cache it
        $v->set_dirty(1); # not fully put - indicates that put() should be called on the object $v later
      }
    }
    @stmts = $self->put_attr_q($obj, $attr => @values);
    for my $q (@stmts) {
      $rows = $self->bolt_cxn->run_query($q);
      return _fail_query($rows) if ($rows->failure);
    }
  }
  $Cache{$obj->neoid} = $obj; # cache it.
  $obj->set_dirty(0);
  return $obj;
}

sub rm {
  my $self = shift;
  my ($obj, $force) = @_;
  unless ($self->bolt_cxn) {
    LOGWARN ref($self)."::rm - ObjectMap has no db connection set";
    return;
  }
  unless ($obj->neoid) {
    LOGWARN ref($self)."::rm - Can't remove an unmapped object";
    return;
  }
  if ($force) {
    INFO "Force (detach) delete on obj ".$obj->neoid;
  }
  my $rows = $self->bolt_cxn->run_query(
    $self->rm_q( $obj, $force )
   );
  my ($n_id) = $rows->fetch_next; # this fetch doesn't fail when the node
  # still has relationships, but the node isn't deleted either
  # second fetch fails correctly
  $rows->fetch_next;
  return _fail_query($rows) if ($rows->failure == 1);
  unless ($n_id) {
    LOGWARN ref($self)."::rm - corresponding db node not found";
    return;
  }
  return $n_id;
}

sub add {
  my $self = shift;
  my ($obj, $attr, $tgt) = @_;
  unless ($self->bolt_cxn) {
    LOGWARN ref($self)."::add - ObjectMap has no db connection set";
    return;
  }
  my $rows = $self->bolt_cxn->run_query(
    $self->put_attr_q( $obj, $attr, $tgt )
   );
  return _fail_query($rows) if ($rows->failure);
  my ($tgt_id) = $rows->fetch_next;
  unless ($tgt_id) {
    LOGWARN ref($self)."::add - corresponding target db node not found";
    return;
  }
  return $tgt_id;
}

sub drop {
  my $self = shift;
  my ($obj, $attr, $tgt) = @_;
  unless ($self->bolt_cxn) {
    LOGWARN ref($self)."::drop - ObjectMap has no db connection set";
    return;
  }
  my $rows = $self->bolt_cxn->run_query(
    $self->rm_attr_q( $obj, $attr, $tgt )
   );
  return _fail_query($rows) if ($rows->failure);
  my ($tgt_id) = $rows->fetch_next;
  unless ($tgt_id) {
    LOGWARN ref($self)."::drop - corresponding target db node not found";
    return;
  }
  return $tgt_id;
}


sub _fail_query {
  my ($stream) = @_;
  my @c = caller(1);
  if ($stream->server_errmsg) {
    LOGCARP $c[3]." : server error: ".$stream->server_errmsg;
  }
  elsif ($stream->client_errmsg) {
    LOGCARP $c[3]."::get : client error: ".$stream->client_errmsg;
  }
  else {
    LOGWARN $c[3]."::get : unknown database-related error";
  }
  return
}

# cypher query to pull a node
sub get_q {
  my $self = shift;
  my ($obj) = @_;
  unless ( blessed $obj && $obj->isa($self->class) ) {
    LOGDIE ref($self)."::get_q : arg1 must be an object of class ".$self->class;
  }
  
  if ($obj->neoid) {
    return cypher->match('n:'.$self->label)
      ->where( { 'id(n)' => $obj->neoid })
      ->return('n','id(n)');
  }
  # else, find equivalent node
  my $wh = {};
  for ($self->property_attrs) {
    $wh->{"n.".$self->pmap->{$_}} = $obj->$_;
  }
  return cypher->match('n:'.$self->label)
    ->where($wh)
    ->return('n','id(n)');
}

# cypher query to pull nodes via relationship
sub get_attr_q {
  my $self = shift;
  my ($obj,$att) = @_;
  unless ( blessed $obj && $obj->isa($self->class) ) {
    LOGDIE ref($self)."::get_attr_q : arg1 must be an object of class ".$self->class;
  }
  unless ($att) {
    LOGDIE ref($self)."::get_attr_q : arg2 must be an attribute name for class ".$self->class;
  }
  # set up obj match:
  my $q = $self->get_q($obj);
  # hack Cypher::Abstract - drop the return and add a with: 
  pop @{$q->{stack}};
  $q->with('n');
  if ( grep /^$att$/, $self->property_attrs ) {
    $q->return( 'n.'.$self->pmap->{$att} );
  }
  elsif (grep /^$att$/, $self->relationship_attrs ) {
    my ($reln, $end_label, $many) = @{$self->rmap->{$att}}{qw/rel lbl many/};
    $q->match(ptn->N('n')->R($reln)->N('a:'.$end_label))->
      return('a', 'id(a)');
    $q->limit(1) unless $many;
    return $q;
  }
  else {
    LOGDIE ref($self)."::get_attr_q : '$att' is not a registered attribute for class ".$self->class;
  }
}

# put_q
# if obj has a neoid (is 'mapped'), then overwrite the props on that node
# in the DB with the props in the obj
# if obj does not have a neoid, create a new node with the props on the object
# both stmts return the node id
sub put_q {
  my $self = shift;
  my ($obj) = @_;
  unless ( blessed $obj && $obj->isa($self->class) ) {
    LOGDIE ref($self)."::put_q : arg1 must be an object of class ".$self->class;
  }
  my $props = {};
  my @null_props;
  for ($self->property_attrs) {
    if (defined $obj->$_) {
      $props->{$self->pmap->{$_}} = $obj->$_;
    }
    else {
      push @null_props, $self->pmap->{$_};
    }
  }
  
  if ($obj->neoid) {
  # rewrite props on existing node
  # need to set props that have defined values,
  # and remove props that undefined values -
    # so 2 statements are returned
    my $nprops;
    $nprops->{"n.$_"} = $props->{$_} for keys %{$props};
    my @stmts;
    push @stmts, cypher->match('n:'.$self->label)
      ->where({ 'id(n)' => $obj->neoid })
      ->set($nprops)
      ->return('id(n)');
    for (@null_props) {
      push @stmts, cypher->match('n:'.$self->label)
        ->where({ 'id(n)' => $obj->neoid })
        ->remove('n.'.$_)
        ->return('id(n)');
    }
    return @stmts;
  }
  # else, create new node with props that have defined values
  return cypher->create(ptn->N('n:'.$self->label => $props))
    ->return('id(n)');
}

# put_attr_q($obj, $attr => @values)
# - query to create relationships and end nodes corresponding
# to object- or collection-valued attributes
# returns a list, one statement per $value
# can only do this on node that already is mapped in the db (must have non-empty
# neoid() attr)
# for each obj in @values - require these all be present in db as well? Or create de novo?
# - require that they be mapped: do put_q($_) for (@values), then put_attr_q,
# if necessary
sub put_attr_q {
  my $self = shift;
  my ($obj,$att, @values) = @_;
  unless ( blessed $obj && $obj->isa($self->class) ) {
    LOGDIE ref($self)."::put_attr_q : arg1 must be an object of class ".$self->class;
  }
  unless (defined $obj->neoid) {
    LOGDIE ref($self)."::put_attr_q : arg1 must be a mapped object (attr 'neoid' must be set)";  }
  unless (@values) {
    LOGDIE ref($self)."::put_attr_q : arg2,... must be a list of endpoint objects";
  }
  if ( grep /^$att$/, $self->property_attrs ) {
    return ( cypher->match('n:'.$self->label)
      ->where({'id(n)' => $obj->neoid })
      ->set( {'n.'.$self->pmap->{$att} => $values[0]} )
      ->return('id(n)') );
  }
  elsif (grep /^$att$/, $self->relationship_attrs ) {
    my ($reln, $end_label, $many) = @{$self->rmap->{$att}}{qw/rel lbl many/};
    my @stmts;
    for my $val (@values) {
      next unless defined $val;
      unless (blessed $val && $val->isa('Bento::Meta::Model::Entity')) {
        LOGDIE ref($self)."::put_attr_q : arg 3,... must all be Entity objects";
      }
      unless ($val->neoid) {
        LOGDIE ref($self)."::put_attr_q : arg 3,... must all be mapped objects (all must have 'neoid' set)";
      }
      my $q = cypher->match(
        ptn->C(ptn->N('n:'.$self->label), ptn->N('a:'.$end_label))
       )
        ->where({'id(n)' => $obj->neoid,
                 'id(a)' => $val->neoid})
        ->merge(ptn->N('n')->R($reln)->N('a'))
        ->return('id(a)');
      push @stmts, $q;
      last unless $many;
    }
    return @stmts;
  }
  else {
    LOGDIE ref($self)."::put_attr_q : '$att' is not a registered attribute for class ".$self->class;
  }
}

# rm_q - remove a mapped object. if $detach is TRUE then force removal
# (i.e., use DETACH DELETE), which will also remove the relationships
# in the db.
sub rm_q {
  my $self = shift;
  my ($obj,$detach) = @_;
  unless ( blessed $obj && $obj->isa($self->class) ) {
    LOGDIE ref($self)."::rm_q : arg1 must be an object of class ".$self->class;
  }
  unless (defined $obj->neoid) {
    LOGDIE ref($self)."::rm_q : arg1 must be a mapped object (attr 'neoid' must be set)";  }
  my $q = cypher->match('n:'.$self->label)
    ->where({'id(n)' => $obj->neoid });
  if ($detach) {
    $q->detach_delete('n');
  }
  else {
    $q->delete('n');
  }
  return $q->return('id(n)');
}

# rm object, collection attributes - delete relationships only, leave end nodes
# intact
# use rm_q to remove end nodes explicitly in database
sub rm_attr_q {
  my $self = shift;
  my ($obj,$att, @values) = @_;
  unless ( blessed $obj && $obj->isa($self->class) ) {
    LOGDIE ref($self)."::rm_attr_q : arg1 must be an object of class ".$self->class;
  }
  unless (defined $obj->neoid) {
    LOGDIE ref($self)."::rm_attr_q : arg1 must be a mapped object (attr 'neoid' must be set)";  }
  if ( grep /^$att$/, $self->property_attrs ) {
    return ( cypher->match('n:'.$self->label)
               ->where({'id(n)' => $obj->neoid })
               ->remove( 'n.'.$self->pmap->{$att} )
               ->return('id(n)') );
  }
  elsif (grep /^$att$/, $self->relationship_attrs ) {
    my ($reln, $end_label, $many) = @{$self->rmap->{$att}}{qw/rel lbl many/};
    my $r_reln = $reln;
    $r_reln =~ s/:/r:/;
    my @stmts;
    if ($values[0] eq ':all') { # detach all ends
      return cypher->match(ptn->N('n:'.$self->label)
                      ->R($r_reln)->N("v:$end_label"))
        ->where({ 'id(n)' => $obj->neoid })
        ->delete('r')# delete relationship only
        ->return('id(v)');
    }
    for my $val (@values) {
      next unless defined $val;
      unless (blessed $val && $val->isa('Bento::Meta::Model::Entity')) {
        LOGDIE ref($self)."::put_attr_q : arg 3,... must all be Entity objects";
      }
      unless ($val->neoid) {
        LOGDIE ref($self)."::rm_attr_q : arg 3,... must all be mapped objects (all must have 'neoid' set)";
      }
      my $q = cypher->match(ptn->N('n:'.$self->label)
                              ->R($r_reln)->N("v:$end_label"))
        ->where({
          'id(n)' => $obj->neoid,
          'id(v)' => $val->neoid
         })
        ->delete('r') # delete relationship only
        ->return('id(v)');
      push @stmts, $q;
      last unless $many;
    }
    return @stmts;
  }
  else {
    LOGDIE ref($self)."::rm_attr_q : '$att' is not a registered attribute for class ".$self->class;
  }
}


=head1 NAME

Bento::Meta::Model::ObjectMap - interface Perl objects with Neo4j database

=head1 SYNOPSIS

  # create object map for class
  $map = Bento::Meta::Model::ObjectMap->new('Bento::Meta::Model::Node')
  # map object attributes to Neo4j model 
  #  simple attrs = properties
  for my $p (qw/handle model category/) {
    $map->map_simple_attr($p => $p);
  }
  #  object- or collection-valued attrs = relationships to other nodes
  $map->map_object_attr('concept' => '<:has_concept', 
                        'concept' => 'Bento::Meta::Model::Concept');
  $map->map_collection_attr('props' => '<:has_property', 
                            'property' => 'Bento::Meta::Model::Property');

  # use the map to generate canned cypher queries

=head1 DESCRIPTION

=head1 METHODS

=over 

=item new($obj_class [ => $neo4j_node_label ][, $bolt_url])

Create new ObjectMap object for class C($obj_class). Arg is a string.
If $label is not provided, the Neo4j label that is mapped to the
object is set as the last token  in the class namespace, lower-cased.
E.g., for an object of class C<Bento::Meta::Model::Node>, the label is
'node'.

$bolt_cxn is a L<Neo4j::Bolt::Cxn> object. Each map needs one to communicate
with a database. It can be the same connection across maps.

=item class()

Get class mapped by this map.

=item label()

Get label for this map.

=item bolt_cxn()

Get or set bolt_cxn for this map ($map->bolt_cxn($cxn) to set).

=item map_simple_attr($object_attribute => $neo4j_node_property)

=item map_object_attr($object_attribute => $neo4j_node_property, $fully_qualified_end_object_class => $end_neo4j_node_label)

=item map_collection_attr($object_attribute => $neo4j_node_property, $fully_qualified_end_object_class => $end_neo4j_node_label)

=item get($obj)

=item put($obj)

=item rm($obj)

=back

=head2 Cypher generation methods

=over

=item get_q($object)

If $object is mapped, query for the node having the object's Neo4j id.
If not mapped, query for (all) nodes having properties that match the object's
simple properties. The query returns the node (possibly multiple nodes, in the
unmapped case).

=item get_attr_q($object, $object_attribute)

For an object (matched in the same way as L</get_q>):
If the attribute named ($object_attribute) is a simple type, query the value 
of the corresponding node property. The query returns the value, if it exists.

If the attribute is object- or collection-valued, query for the set of nodes
linked by the mapped Neo4j relationship (as specified to L</map_object_attr> or
L</map_collection_attr>). The query returns one node per response row.

=item put_q($object)

If $object is mapped, overwrite the mapped node's properties with the current
value of the object's simple attributes. The query returns the mapped node's
Neo4j id.

If not mapped, create a new node according to the object's simple-valued
attributes ( => Neo4j node properties), setting the corresponding properties.
The query returns the created node's Neo4j id.

=item put_attr_q($object, $object_attribute => @values)

The $object must be mapped (have a Neo4j id) for L</put_attr_q>. 
$object_attribute is the string name of the attribute (not the Neo4j property).
If the attribute is simple-valued, the third argument should be the string or 
numeric value to set. The query will set the property of the mapped node, and 
return the node id.

If the attribute is object- or collection-valued, the @values should be a list
of objects appropriate for the attribute definitions. The query will match the
object node-attribute relationship-attribute node links, and merge the attribute nodes. That is, the attribute nodes will be created if the relationship and 
matching node do not already exist. For a collection-valued attribute, one query
will be created per attribute node. Each query will return the attribute node's
Neo4j id.

=item rm_q($object, [$force])

The $object must be mapped (have a Neo4j id). The query will attempt to delete 
the mapped node from the database. If $force is false or missing, the query will
be formulated with "DELETE"; it will succeed only if the node is not participating in any relationship. 

If $force is true, the query will be formulated with "DETACH DELETE", and the executed query will remove the mapped node and all relationships in which it
participates.

=item rm_attr_q($object, $object_attribute => @values)

The $object must be mapped (have a Neo4j id). If $object_attribute is a
simple-valued (property-mapped) attribute, the query will remove that 
property from the mapped node. If $object_attribute is an object-valued
(relationship-mapped) attribute, then the query will remove the _relationship
only_ between the node corresponding to $object and the nodes corresponding to 
@values. This query does not remove nodes themselves from the database; 
use C<rm_q()> to get queries for that purpose.

=back

=head1 AUTHOR

 Mark A. Jensen < mark -dot- jensen -at- nih -dot- gov >
 FNL

=cut

1;
