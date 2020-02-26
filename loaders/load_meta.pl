use v5.10;
use Neo4j::Bolt;
use Bento::MakeModel;
use Neo4j::Cypher::Abstract qw/cypher ptn/;
use UUID::Tiny qw/:std/;
use strict;

my $NEO_URL = $ENV{NEO_URL} // 'bolt://neo4j:j4oen@localhost:7687';
my $uuid = sub { create_uuid_as_string(UUID_V4) };

my @mdf = grep /\.ya?ml$/, @ARGV;
my ($mod_handle) = grep !/\.ya?ml$/, @ARGV;

die "Need model handle" unless $mod_handle;

# qw{/Users/jensenma/Code/icdc-model-tool/model-desc/icdc-model.yml /Users/jensenma/Code/icdc-model-tool/model-desc/icdc-model-props.yml};

my $mm = Bento::MakeModel->new()->read_input(@mdf);
my $mod = $mm->model;
my $dbh = Neo4j::Bolt->connect($NEO_URL);
my $con = $dbh->connected;
die "No connection to neo4j: ".$dbh->errmsg unless $con;

my %edges;
my %done_props;

my @cyph;
push @cyph, cypher->merge(ptn->N('o:origin', {name => $mod_handle}));

# match (q:node)-[:has_concept]->(c:concept) where q.handle = $name
# merge (n:node { handle:$name, model:$mod_handle })-[:has_concept]->(c:concept)
# on create set c.id = $cid


for my $n ($mod->nodes) {
  my ($cid, $cyph) = merge_concept_id('node',$n->name);
  # create Node and Concept
  push @cyph, $cyph;
  push @cyph, cypher->match(
    ptn->N("c:concept")
   )
    ->where( { 'c.id' => $cid } ) 
    ->merge(
      ptn->N("n:node", { handle => $n->name, model => $mod_handle })
        ->R(":has_concept>")->N('c')
       );
  # create Term, link to Origin and Concept
  push @cyph, @{term_origin_concept($n->name, $mod_handle, $cid)->[1]};
}

for my $rt ($mod->edge_types) {
  my ($cid,$cyph) = merge_concept_id('relationship',$rt->name);
  # create the Term and link to Concept and Origin
  push @cyph, $cyph;
  push @cyph, @{term_origin_concept($rt->name,$mod_handle,$cid)->[1]};
  for my $e ($mod->edge_by_type($rt)) {
    my $tmp_id = $uuid->();
    push @{$edges{$e->name}}, $tmp_id;
    # create a Relationship node instance for this Src/Dst pair, and link to Concept
    push @cyph, cypher->match(
      ptn->N("c:concept")
     )
      ->where ({'c.id' => $cid})
      ->create(
        ptn->N("r:relationship", { handle => $rt->name, model => $mod_handle, tmp_id => $tmp_id })
        ->R(":has_concept>")->N('c')
       );
    # create the links has_src and has_dst from this Relationship to the Node nodes
    # also, create a relationship between Node nodes corresponding to this Relationship
    push @cyph, cypher->match(ptn->C(
      ptn->N('s:node'),
      ptn->N('r:relationship'),
      ptn->N('d:node')
     ))
      ->where(
        { 's.handle' => $e->src->name,
          's.model' => $mod_handle,
          'd.handle' => $e->dst->name,
          'd.model' => $mod_handle,
          'r.tmp_id' => $tmp_id,
        }
       )
      ->merge(
        ptn->N('s')->R('<:has_src')->N('r')->R(':has_dst>')->N('d')
          ->R('<rr:_'.$e->name)->N('s')
       )
      ->on_create->set({ 'rr.model' => $mod_handle })
  }
}

# create property nodes , concepts and terms
for my $ent ($mod->nodes, $mod->edge_types) {
  for my $p ($ent->props) {
    if (!$done_props{$p->name}) {
      # create a Concept for the property
      my ($cid,$cyph) = merge_concept_id('property',$p->name);
      # create the Term and link to Concept and Origin
      push @cyph, $cyph;
      push @cyph, @{term_origin_concept($p->name, $mod_handle, $cid)->[1]};
      # create a Property node instance and link to Concept
      push @cyph, cypher->match(
        ptn->N("c:concept")
       )
        ->where({'c.id' => $cid})
        ->create(
         ptn->N("p:property", {
           handle => $p->name,
           model => $mod_handle,
           ($p->is_required ? (is_required => $p->is_required) : ()),
           value_domain => encode_prop_type($p) // 'None'
         })
           ->R(":has_concept>")->N('c')
          );
      # add metaproperties to Property nodes, Value_sets of Terms
      
      $done_props{$p->name}++;
    }
  }
}

# link properties to nodes
for my $n ($mod->nodes) {
  for my $p ($n->props) {
  # link Node to Property
 
    push @cyph, cypher->match(ptn->C(
      ptn->N('n:node'),ptn->N('p:property')
     ))
      ->where(
        { 'n.handle' => $n->name,
          'n.model' => $mod_handle,
          'p.handle' => $p->name,
          'p.model' => $mod_handle
         }
       )
      ->merge(
        ptn->N('n')->R(':has_property>')->N('p')
       );
  }
}

#link properties to edges

for my $rt ($mod->edge_types) {
  my @rids = @{$edges{$rt->name}};
  for my $p ($rt->props) {
    push @cyph, cypher->match(ptn->C(
      ptn->N('r:relationship'),
      ptn->N('p:property')
     ))
      ->where(
        { 'r.tmp_id' => {-in => \@rids},
          'p.handle' => $p->name,
          'p.model' => $mod_handle
        }
       )
      ->merge(
        ptn->N('r')->R(':has_property')->N('p')
       );
  }
}

# create value_sets and their terms and related concepts
for my $pname (keys %done_props) {
  my $p = $mod->prop($pname);
  next unless (ref($p->type) eq 'ARRAY');
  my $vid = $uuid->();
  push @cyph, cypher->match( ptn->N('p:property'))
    ->where( { 'p.handle' => $pname, 'p.model' => $mod_handle} )
    ->create( ptn->N('p')->R(":has_value_set>")->N('v:value_set',{id => $vid}) );
  for my $val ($p->values) {
    next unless defined $val;
    if ($val =~ /^https?:\/\//) { # url points to value set
      push @cyph, cypher->match( ptn->N('v:value_set') )
        ->where({'v.id' => $vid})
        ->set( { 'v.url' => $val });
      last;
    }
    else { # a new term
      if (! $val) { $DB::single=1; }
      my ($cid,$cyph) = merge_concept_id('term', $val);
      push @cyph, $cyph;
      my $t = term_origin_concept($val,$mod_handle,$cid);
      push @cyph, @{$t->[1]};
      # attach to value_set
      push @cyph, cypher->match(ptn->C(
        ptn->N('t:term'),
        ptn->N('v:value_set')
       ))
        ->where( { 't.id' => $t->[0],
                   'v.id' => $vid } )
        ->create( ptn->N('t')->R('<:has_term')->N('v') );
    }
  }
}

# clean up tmp_id on Relationships
push @cyph, cypher->match('r:relationship')
  ->remove('r.tmp_id');

say $_.";" for @cyph;

sub merge_concept_id {
  my ($label, $value) = @_;
  my $sth = $dbh->run_query(
    cypher->match( ptn->N("n:$label")->R(':has_concept>')->N("c:concept") )
      ->where( { $label eq 'term' ? 'n.value' : 'n.handle' => $value } )
      ->return( 'c.id' ) );
  my ($r) = $sth->fetch_next;
  my $cid = $r || $uuid->() ;
  return $cid, cypher->merge(
    ptn->N('c:concept', { id => $cid })
   );

}

sub term_origin_concept {
  my ($value, $origin, $cid) = @_;
  my $tid = $uuid->();
  return [
    $tid,
    [ cypher->merge(
      ptn->N('c:concept', { id => $cid })
     ),
      cypher->match(ptn->C(
        ptn->N('c:concept'),
        ptn->N('o:origin')
       ))
        ->where( {'c.id' => $cid, 'o.name' => $mod_handle } )
        ->merge(
          ptn->N('o')->R("<:has_origin")->N("t:term", { value => $value, id => $tid })->R(":represents>")->N('c')
         )]
   ]; 
}

sub encode_prop_type {
  my $p = shift;
  for ($p->type) {
    ref eq 'ARRAY' && return 'enum';
    ref eq 'HASH' && return join("+",keys %$_);
    return $p->type;
  }
}

=head1 NAME

load_meta.pl - load bento model into metamodel graph

=head1 SYNPOSIS

  perl load_meta.pl bento_model.yaml bento_model_props.yaml <short_model_name> > meta.cypher
  cypher-shell -u <user> -p <pass> < meta.cypher

=head1 DESCRIPTION

Script reads Bento model description files, and creates a file of Cypher statements to be loaded
into Neo4j with metamodel graph currently up.

Note that the DB needs to be queried during script run. Currently looks for neo on localhost:7687.

=head1 DEPENDENCIES

Script needs L<Neo4j::Bolt>, L<Neo4j::Cypher::Abstract>, L<Bento::MakeModel>, L<UUID::Tiny> 
installed.

=head1 AUTHOR

  mark -dot- jensen -at- nih -dot- com
  (c) 2020 FNLCR

=cut

1;
