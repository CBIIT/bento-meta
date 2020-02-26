use v5.10;
use Neo4j::Bolt;
use Neo4j::Cypher::Abstract qw/cypher ptn/;
use UUID::Tiny qw/:std/;
use strict;

my $NEO_URL = $ENV{NEO_URL} // 'bolt://neo4j:j4oen@localhost:7687';
my $uuid = sub { create_uuid_as_string(UUID_V4) };

my $dbh = Neo4j::Bolt->connect($NEO_URL);
my $con = $dbh->connected;
die "No connection to neo4j: ".$dbh->errmsg unless $con;

$_ = <>;
chomp;
my @hdr = split /\t/;
my %data;
while (<>) {
  chomp;
  my %dta;
  @dta{@hdr} = split /\t/;
  $dta{'NCIt Definition'} =~ s/^"//;
  $dta{'NCIt Definition'} =~ s/"$//;
  $data{$dta{'ICDC Preferred Term'}} = \%dta;
}

my @cyph;
# create Origin node for NCIt, is_external:true, url: https://ncit.nci.nih.gov/
push @cyph, cypher->merge( ptn->N('o:origin', {
  name => 'NCIT',
  is_external => 1,
  url => 'https://ncit.nci.nih.gov',
}) );

for my $value (keys %data) {
  my $dta = $data{$value};
  # find Concept linked to ICDC term
  my $sth = $dbh->run_query(
    cypher->match(
      ptn->N('c:concept')->R('<:represents')->N('t:term')
     )
      ->where( {'t.value' => $value } )
      ->return( 'c.id' )
     );
  my ($cid) = $sth->fetch_next; # expect this to be there, since model is already present in db
  unless ($cid) {
    warn "Concept matching '$value' term is not present in DB";
    next;
  }
  # create new NCIT term, link to Origin and Concept
  my $tid = $uuid->();
  push @cyph, cypher->match( ptn->C(
    ptn->N('o:origin'),
    ptn->N('c:concept')
   ))
    ->where( { 'o.name' => 'NCIT',
               'c.id' => $cid })
    ->merge(
      ptn->N('o')->R('<:has_origin')
        ->N('t:term',
            { id => $tid,
              value => $dta->{'NCIt Preferred Term'},
              origin_id => $dta->{'Concept Code'},
              origin_definition => $dta->{'NCIt Definition'},
            })
        ->R(':represents>')->N('c')
     );
}

say $_.";" for @cyph;
1;

