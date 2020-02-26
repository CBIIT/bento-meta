use v5.10;
use Spreadsheet::XLSX;
use HTML::Entities;
use JSON;
use UUID::Tiny qw/:std/;
use Neo4j::Cypher::Abstract qw/cypher ptn/;
use Neo4j::Bolt;
use strict;
use warnings;

# $SIG{__WARN__} = sub { die $_[0] };

my $bridg2neo_url = 'bolt://localhost:32795';
my $dbh = Neo4j::Bolt->connect($bridg2neo_url);
my $con = $dbh->connected;
unless ($con) {
  die "Can't connect to BRIDG graph at '$bridg2neo_url'";
}

my @cyph;
my $bxls = '/Users/jensenma/Code/icdc-model-tool/bridg/ICDC Cross-Mapping of Data Sources and Standards - 20200110.xlsx';
my $mod_handle = 'ICDC';

my $uuid = sub { create_uuid_as_string(UUID_V4) };
my $xls = Spreadsheet::XLSX->new($bxls);
my ($s) = $xls->worksheets;

my @cols = (0,1,col('AY')..col('BG'));
my @rows = (3..($s->row_range)[1]);
my (@data,@hdrs);

for my $c (@cols) {
  push @hdrs, decode_entities($s->get_cell(2,$c)->value);
}
s/^Comments.*/Comments/ for @hdrs;

for my $r (@rows) {
  my (%dta,@dta);
  for my $c (@cols) {
    my $val;
    eval {
      $val = $s->get_cell($r, $c)->value;
      $val =~ s/^\s+//;
      $val =~ s/\s+$//;
    };
    $val = $@ ? undef : decode_entities($val) ;
    if ($val) { $val =~ s/[']/&#39;/g;}
    push @dta, $val;
  }
  @dta{@hdrs} = @dta;
  push @data, \%dta;
}

push @cyph, cypher->merge(
  ptn->N('o:origin',{ name => 'BRIDG',
                      version => '5.3.1',
                      is_external => "1",
                      url => "https://bridgmodel.nci.nih.gov/"
                     })
 );

for (@data) {
  next unless $_->{Class};
  my $d = $_->{Description} // '';
  my ($id,$value);
  my %resp;
  if ($_->{'Element Type'} =~ /Assoc/) {
    my ($dst_role,$dst_class) = $_->{'Element'} =~ /^([^(]+)\(([^)]+)\)/;
    my $str = $dbh->run_query(<<Q);
MATCH ()-[r {dst_role:"$dst_role"}]->(), (s)<-[:has_src]-(a:Association)-[:has_dst]->(d) WHERE a.id = r.assoc_id 
RETURN a.name, a.id, s.name, r.src_role, d.name, r.dst_role
Q
    @resp{qw/name id src_name src_role dst_name dst_role/} =
      $str->fetch_next;
    $resp{type} = 'Association';
    if ($resp{name}) {
      $id = $resp{id};
      $value = sprintf("(%s as %s)<-[:%s]-(%s as %s)",@resp{qw/src_name src_role name dst_name dst_role/});
    }
    else {
      warn "No association found for $$_{Element} in BRIDG graph;";
      $id=undef;
      $value=sprintf("(%s)<--(%s as %s)", $_->{Class}, $dst_class, $dst_role);
    }

  }
  elsif ($_->{'Element Type'} =~ /Attrib/) {
    my $str = $dbh->run_query(<<Q);
MATCH (c:Class {name:"$$_{Class}"})-[:has_property]->(p:Property {name:"$$_{Element}"})
RETURN p.name, p.id, c.name, p.data_type
Q
    @resp{qw/name id class_name data_type/} = $str->fetch_next;
    $resp{type} = 'Property';
    if ($resp{name}) {
      $id = $resp{id};
      $value = sprintf("%s.%s",@resp{qw/class_name name/});
    }
    else {
      warn "No property found in BRIDG graph for $$_{Element}";
      $id=undef;
      $value = sprintf("%s.%s",$_->{Class}, $_->{Element});
    }
  }
  else { # 'Class'
    my $str = $dbh->run_query(<<Q);
MATCH (c:Class {name:"$$_{Class}"}) RETURN c.name, c.id
Q
    @resp{qw/name id/} = $str->fetch_next;
    $resp{type} = 'Class';
    if ($resp{name}) {
      $id = $resp{id};
      $value = $resp{name};
    }
    else {
      warn "No class found for $$_{Class} in BRIDG graph";
      $id = undef;
      $value = $_->{Class};
    }
  }

  my ($origin_definition,
      $examples, $other_names, $notes) =
        $d =~ m|^\s*(?:DEFINITION:\s*)(.*?)\W*
                (?:EXAMPLE.*?:\s*)(.*?)\W*
                (?:OTHER\sNAME.*?:\s*)(.*?)\W*
                (?:NOTE.*?:\s*)(.*?)\W*$|sx;
  $origin_definition and $origin_definition =~ s/\n/ &#10; /sg;
  $examples and $examples =~ s/\n/ &#10; /sg;
  $other_names and $other_names =~ s/\n+/ &#10; /sg;
  $notes and $notes =~ s/\n/ &#10; /sg;
  my $cid = $uuid->(); # every bridg term will have its own concept

  my $term_spec = {
            value => $value,
            origin_id => $id // 'none',
            origin_definition => $origin_definition//'none',
            ($examples ? (examples => $examples) : ()),
            ($other_names ? (other_names => $other_names) : ()),
            ($notes ? (notes => $notes) : ()),
            ($_->{Class} ? (class => $_->{Class}) : ()),
            ($_->{Cardinality} ? (cardinality => $_->{Cardinality}) : ()),
            ($_->{'Mapping Path'} ? (mapping_path => $_->{'Mapping Path'}) : ()),
            ($_->{Element} ? (element => $_->{Element}) : ()),
            ($_->{'Element Type'} ? (element_type => $_->{'Element Type'}) : ()),
            ($_->{'Data Type'} ? (hl7_data_type => $_->{'Data Type'}) : ()),
            ($_->{'Comments'} ? (comments => $_->{'Comments'}) : ()),
          };
  if (my $p_b = $_->{Property}) {
    if ($p_b =~ />/) { # relationship in ICDC model
      my $src = $_->{Node};
      my ($rel,$dst) = split(/\s+>\s+/,$p_b);
      $rel =~ s/^\s+//;
      $dst =~ s/\s+$//;
      push @cyph, cypher->match( ptn->C(
        ptn->N('s:node')->R('<:has_src')
          ->N('r:relationship')->R(':has_dst>')->N('d:node'),
        ptn->N('o:origin')
       ))
        ->where({'r.handle' => $rel,
                 's.handle' => $src,
                 'd.handle' => $dst,
                 'r.model' => $mod_handle,
                 'o.name' => 'BRIDG',
                 'o.version' => '5.3.1'})
        ->merge(
          ptn->N('o')->R('<:has_origin')
            ->N('t:term', $term_spec)
            ->R(':represents>')
            ->N('c:concept', {id => $cid})
            ->R('<:has_concept')->N('r')
           );
    }
    else { # property
      eval {
      push @cyph, cypher->match(ptn->C(
        ptn->N('p:property'),
        ptn->N('o:origin')
       ))
        ->where({'p.handle' => $p_b,
                 'p.model' => $mod_handle,
                 'o.name' => 'BRIDG',
                 'o.version' => '5.3.1'})
        ->merge(
          ptn->N('o')->R('<:has_origin')
            ->N('t:term', $term_spec)
            ->R(':represents>')
            ->N('c:concept', {id => $cid})
            ->R('<:has_concept')
            ->N('p')
           );
    };
      if ($@) {
        $DB::single=1;
        1;
      }
    }
  }
  elsif (my $n = $_->{Node}) { # node
    push @cyph, cypher->match( ptn->C(
      ptn->N('n:node'),
      ptn->N('o:origin')
     ))
      ->where( {'n.handle' => $n,
                'n.model' => $mod_handle,
                'o.name' => 'BRIDG',
                'o.version' => '5.3.1'})
      ->merge(
        ptn->N('o')->R('<:has_origin')
          ->N('t:term', $term_spec)
          ->R(':represents>')
          ->N('c:concept', {id => $cid})
          ->R('<:has_concept')
          ->N('n')
         );
  }
  else {
    warn "can't process ".encode_json($_).": no Node or Property values";
  }
}

say $_.";" for @cyph;
1;

sub col {
  my $m = 1;
  my $a = 0;
  for (reverse split('',$_[0])) {
    $a += $m*( ord($_)-ord('A') + 1);
    $m *= ord('Z')-ord('A')+1;
  }
  return $a-1;
}

