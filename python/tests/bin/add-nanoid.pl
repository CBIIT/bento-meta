#!/usr/bin/perl
use strict;
use warnings;

use Neo4j::Bolt;
use UUID::Tiny qw/:std/;
use Hashids;
use Nanoid;
use Data::Dumper;
use DateTime;
use FindBin qw( $Bin $Script $RealBin $RealScript);


#-----------------------------------------------------------------------------
# GLOBALS
#-----------------------------------------------------------------------------
my $VERBOSE = 1;
my $CXN;
my $PID = $$;
my $START_TIME = DateTime->now(time_zone=>'local');
   # server_ip = ( 'LOCAL'   => '127.0.0.1',
   #               'DEV'     => '54.91.213.206',
   #               'STAGE'   => '3.210.7.218',
   #               'PROD'    => '34.233.99.234',
   #               'TEST'    => '3.225.53.249');
my $SERVER_IP = '127.0.0.1';


#-----------------------------------------------------------------------------
# make a correctly formed url for connecting to neo4j using bolt 
#-----------------------------------------------------------------------------
sub construct_bolt_url {
    my ($ip) = @_;

    ## these should be in your environment, not the code silly goose
    my $neo4j_user = 'neo4j'; # $ENV{'NEO4J_MDB_USER'};
    my $neo4j_pass = 'test'; # $ENV{'NEO4J_MDB_PASS'};
    my $port = 7687;

    print "port is $port - u: $neo4j_user - p: $neo4j_pass\n" if $VERBOSE > 20;

    my $url = 'bolt://' . $neo4j_user . ':' . $neo4j_pass . '@' . $ip . ':' . $port;

    return $url;
}

#-----------------------------------------------------------------------------
# sub: print_settings     -- prints global settings --
#-----------------------------------------------------------------------------
sub print_settings {
    print "\n","-"x80,"\n";
    print "SETTINGS\n";
    print "  VERBOSE   : $VERBOSE\n";
    print "  SERVER_IP : $SERVER_IP\n";
}

#-----------------------------------------------------------------------------
# sub: print_header     -- prints script header --
#-----------------------------------------------------------------------------
sub print_header {
    print "- "x40,"\n";
    print "COMMAND     : ", `ps -o 'command=' -p $PID`;
    print "START TIME  : $START_TIME\n";
    print "="x80,"\n";
}


#-----------------------------------------------------------------------------
# sub: print_footer    -- prints a simple script footer --
#-----------------------------------------------------------------------------
sub print_footer {
    print "="x80,"\n";
    print "SCRIPT PATH : $RealBin\n";
    print "SCRIPT      : $RealScript\n";
    print "COMMAND     : ", `ps -o 'command=' -p $PID`;
    print "PERL VER    : $]\n";
    print "HOSTNAME    : ", `hostname -s`;
    print "USER        : ", `ps -o 'user=' -p $PID`;
    print "START TIME  : $START_TIME\n";
    print "END TIME    : ", DateTime->now(time_zone=>'local'), "\n";
    print "- "x40,"\n";
    print `ps -o user,pmem,pcpu,lstart,etime,cputime,command -p $PID`;
    print "-"x80,"\n\n";
}


sub remove_added_ids {

    print "Start: remove_added_ids()\n" if $VERBOSE; 

    my @types = ( 
                    'nanoid',
                    );

    foreach my $type (@types) {
        remove_id_type($type);
    }

    print "End: remove_added_ids()\n" if $VERBOSE; 
}

sub remove_id_type {
    my ($type) = @_;
    my $count;

    my $stream = $CXN->run_query(
      "MATCH (a) REMOVE a.$type RETURN count(a.$type);",
      {} # parameter hash required
    );
    my @names = $stream->field_names;
    while ( my @row = $stream->fetch_next ) {
      print "\tnumber of a.$type: $row[0]\n" if $VERBOSE > 2;
      $count = $row[0];
    };

    print "... done removing all $type ids\n" if $VERBOSE;
    return $count;
}





sub get_query {
    my ($type, $tempid) =@_;

    my $query = "MATCH (a) 
                 WHERE  a.$type = '$tempid'
                 RETURN '$type', a.$type";

    return $query;
}


sub get_a_thing_query {
    my ($type) =@_;

    my $query = "MATCH (a) 
                 WHERE  a.$type IS NULL 
                 RETURN id(a)
                 LIMIT 1";

    return $query;
}


sub set_id_query {
    my ($type, $id, $neo4jid) = @_;

    unless (defined ($type))    { die "type     is not defined!" };
    unless (defined ($id))      { die "new id   is not defined!" };
    unless (defined ($neo4jid)) { die "neo4j id is not defined!" };

    my $query = "MATCH (a) 
                 WHERE  id(a) = $neo4jid
                 SET a.$type = '$id'
                 RETURN id(a), a.$type";

    return $query;
}

sub get_a_thing_neo4jid {
    my $type = shift // 'nanoid'; 
    
    my $neo4jid = undef;

    my $query = get_a_thing_query($type);

    my $stream = $CXN->run_query( $query,
      {} # parameter hash required
    );
    my @names = $stream->field_names;
    while ( my @row = $stream->fetch_next ) {
        $neo4jid = $row[0];
        print "\t> neo4j id: $row[0]\n" if $VERBOSE > 1;
    };

   return $neo4jid; 
}


sub set_a_newid_for_thing {
    my ($type, $id, $neo4jid) = @_; 
    
    my $result = undef;
    my $counter = 0;
    
    my $query = set_id_query($type, $id, $neo4jid);
    print "\tupdate query is : $query\n" if $VERBOSE > 3;

    my $stream = $CXN->run_query( $query,
      {} # parameter hash required
    );
    my @names = $stream->field_names;
    while ( my @row = $stream->fetch_next ) {
        $counter++;
        if (( $neo4jid eq $row[0]) && ( $id eq $row[1])){
            $result = 1;
        }
        print "\t>neo4j.id:$row[0]\ttype:$type\tnewid:$row[1] \n" if $VERBOSE;
    };

   if ($counter == 1 && $result == 1) {
       print "\tupdate good\n" if $VERBOSE > 2;
   }
    
   return $result; 
}


sub check_for_existing_ids {
    my ($id_href) =@_;

    my $total_found_ids = 0;

    foreach my $type ( keys %{$id_href} ) {

        print "\tChecking if type $type exists ...\n" if $VERBOSE > 4;
        
        # see if it is in the database
        my $tempid = $id_href->{$type};
        print "\t\tchecking existance of $type - $tempid\n" if $VERBOSE > 1;

        my $query = get_query($type, $tempid);

        my $count = count_ids($query);
        $total_found_ids += $count;
    }
    
    if ($total_found_ids > 0) {
        print "regenerate keys, not unique\n" if $VERBOSE > 1;
    }
    else{
        print "\tkeys are unique\n" if $VERBOSE > 2;
    }

    return $total_found_ids;
}


sub count_ids {
    my ($query) = @_; 
    
    my $result = 0; 

    my $stream = $CXN->run_query( $query,
      {} # parameter hash required
    );
    my @names = $stream->field_names;
    while ( my @row = $stream->fetch_next ) {
      $result++; 
      print "\t> type: $row[0]\tid: $row[1] \n" if $VERBOSE > 2;
    };

   return $result; 
}

sub count_nanoid {

    print "... starting counting a.nanoid" if $VERBOSE > 4;

    my $count;

    my $stream = $CXN->run_query(
      "MATCH (a) WHERE a.nanoid IS NOT NULL RETURN count(a);",
      {} # parameter hash required
    );
    my @names = $stream->field_names;
    while ( my @row = $stream->fetch_next ) {
      print "\tnumber of a.nanoid: $row[0]\n" if $VERBOSE > 2;
      $count = $row[0];
    };

    print "... done counting a.nanoid \n" if $VERBOSE > 4;
    return $count;
}



sub copy_id_to_originalid {

    print "Start: copy_id_to_original()\n" if $VERBOSE;
    my $count_at_start = count_originalid();
    print "\ta.original_id at start: $count_at_start\n" if $VERBOSE;

    my $stream = $CXN->run_query(
      "MATCH (a) WHERE a.id IS NOT NULL SET a.original_id = a.id RETURN a.original_id;",
      {} # parameter hash required
    );
    my @names = $stream->field_names;
    while ( my @row = $stream->fetch_next ) {
      print "\t$row[0]\n" if $VERBOSE > 6;
    };
    print "\tDone: copied a.id to a.original_id\n" if $VERBOSE;

    my $count_at_end = count_originalid();
    print "\ta.original_id at end: $count_at_end\n" if $VERBOSE;
    print "End: copy_id_to_originalid()\n" if $VERBOSE;
}


sub count_originalid {

    print "Start: count_originalid()" if $VERBOSE > 4;
    my $count;

    my $stream = $CXN->run_query(
      "MATCH (a) WHERE a.original_id IS NOT NULL RETURN count(a.original_id);",
      {} # parameter hash required
    );
    my @names = $stream->field_names;
    while ( my @row = $stream->fetch_next ) {
      $count = $row[0];
      print "\tnumber of a.original_id: $row[0]\n" if $VERBOSE > 2;
    };

    print "End: count_originalid()\n" if $VERBOSE > 4;
    return $count;

}


sub add_id_to_file {

    my @files = qw/ term_.csv /;

    for my $f (@files) {
        open(my $fh, "<", $f) or die "oops, cannot open $f";

        my $new_f = substr($f,0, -4);
        $new_f .= "_nano.csv";
        open(my $new_fh, ">", $new_f) or die "oops, cannot open $new_f";

        while (my $line = <$fh>) {
           chomp $line;
            my $nanoid = Nanoid::generate('size'=>10, 'alphabet'=>'abcdefghjkmnopqrstuvwxyzACDFGHJKMNPQRTUVWXY0234679');
            print $new_fh "$line,$nanoid\n";
        }
    }
}


# maintains padding
sub hex2bin {
    my ($num_hex) = @_;

    ## padded
    my $num = hex($num_hex);
    my $num_bin = sprintf('%0*b', length($num_hex)*4, $num);
   
    return $num_bin;
}


# maintains my desired padding
sub bin2hex {
    my ($num_bin) = @_;
    my $num_dec = bin2dec($num_bin);
    my $num_hex = sprintf('%08x', $num_dec);
    return $num_hex;
}


# maintains padding
# limited to operating on 8 hexidecimal numbers, 32 binary numbers
sub bin2dec {
    my $d = unpack("N", pack("B32", substr("0" x 32 . shift, -32)));
    my $d_padded = sprintf('%010d', $d);
    return $d_padded;
}

sub make_halfuuid {
    my ($uuid) = @_;

    $uuid =~ s/-//g;
    print "\tuuid is now $uuid\n" if $VERBOSE > 2;
    print "\t            0        1         2         3  \n" if $VERBOSE > 2;
    print "\t            12345678901234567890123456789012\n" if $VERBOSE > 2;

    my $input_1 = substr($uuid, 0, 8);
    my $input_2 = substr($uuid, 8, 8);
    my $input_3 = substr($uuid, 16, 8);
    my $input_4 = substr($uuid, 24, 8);

    print "\thex parts are \n" if $VERBOSE > 2;
    print "\t\t$input_1\n" if $VERBOSE > 2; 
    print "\t\t$input_2\n" if $VERBOSE > 2; 
    print "\t\t$input_3\n" if $VERBOSE > 2; 
    print "\t\t$input_4\n" if $VERBOSE > 2;

    my $b_1 = hex2bin($input_1);
    my $b_2 = hex2bin($input_2);
    my $b_3 = hex2bin($input_3);
    my $b_4 = hex2bin($input_4);

    print "\tbin parts are \n" if $VERBOSE > 2;
    print "\t\t$b_1\n" if $VERBOSE > 2;
    print "\t\t$b_2\n" if $VERBOSE > 2;
    print "\t\t$b_3\n" if $VERBOSE > 2;
    print "\t\t$b_4\n" if $VERBOSE > 2;
    print "\t\t0        1         2         3  \n" if $VERBOSE > 2;
    print "\t\t12345678901234567890123456789012\n" if $VERBOSE > 2;

    my $n = ($b_1 ^ $b_3) | ("\x30" x 32);
    print "==================\n" if $VERBOSE > 4;
    print "I got \n\t\t$n\n" if $VERBOSE > 4;

    my $xor_13 = ($b_1 ^ $b_3) | ("\x30" x 32);
    my $xor_24 = ($b_2 ^ $b_4) | ("\x30" x 32);

    print "\txors are\n\t\t$xor_13\n\t\t$xor_24\n" if $VERBOSE > 4;

    my $hexxor_13 = sprintf("%08x", oct( "0b$xor_13" ) ); 
    my $hexxor_24 = sprintf("%08x", oct( "0b$xor_24" ) ); 
    my $halfuuid = "$hexxor_13" . "$hexxor_24";

    print "\tfirsthalf  = $hexxor_13\n"   if $VERBOSE > 2;
    print "\tsecondhalf = $hexxor_24\n"   if $VERBOSE > 2;
    print "\thalfuuid \t = $halfuuid\n" if $VERBOSE > 1;
    
    return $halfuuid;
}


# ---------------------------------------------------------------------------
sub convert_number_to_hashid {
    my ($number) = @_;

    my $hashid_salt = "mdb and sts 3";
    my $hashids = Hashids->new($hashid_salt);

    my $hashid = $hashids->encode($number);
    
    print "\thashids \t = $hashid\n"   if $VERBOSE > 1;

    return $hashid;
}


# ---------------------------------------------------------------------------
sub make_hashid {
    my ($halfuuid) = @_;  # output from above

    my $hexhalf_1 = substr($halfuuid, 0, 8);
    my $hexhalf_2 = substr($halfuuid, 8, 8);
    
    my $dechalf_1 = sprintf ("%08d", hex($hexhalf_1));
    my $dechalf_2 = sprintf ("%08d", hex($hexhalf_2));

    my $dec = $dechalf_1 . $dechalf_2;
    
    my $hashid = convert_number_to_hashid($dec);

    return $hashid;
}



# ---------------------------------------------------------------------------
sub make_nanoid {
    my $size = shift // 8;
    my $alphabet = shift // 'abcdefghijkmnopqrstuvwxyzACEFGHJKMNPQRTUVWXY34679'; 

    my $nanoid = Nanoid::generate('size'=> $size, 'alphabet'=> $alphabet);
    
    print "\tnanoid $size \t = $nanoid\n"   if $VERBOSE > 1;
    
    return $nanoid;
}


# ---------------------------------------------------------------------------
sub make_uuid {
    #my $uuid_input = '9009b2d690f9465eb2aa5ff61682c13f';
    my $uuid = create_uuid_as_string(UUID_V4);

    print "\tuuid \t\t = $uuid\n"   if $VERBOSE > 1;

    return $uuid;
}


# ---------------------------------------------------------------------------
sub generate_ids {

    my $nanoid = make_nanoid(8);

    my $example_ids_href = { 'nanoid6' => 'UKRyTM',
                    'nanoid8' => 'ka3hdjTV',
                    'nanoud10' => 'bqemY96wTF',
                    'uuid' => '28842094-83c7-4cfa-bfb3-8673b1a22513',
                    'halfuuid' => '9737a6e7326569e9',
                    'hashid' => '0vk1Pn5xRVkrW'};

    my $ids_href = { 
                     'nanoid'  => $nanoid
                    };
    
    return $ids_href;
}

sub update_one_thing {

    my $ids_href = generate_ids();
    my $existing_id_count = check_for_existing_ids($ids_href);
   
    if ($existing_id_count == 0){
        my $counter = 0;
        my $neo4jid = get_a_thing_neo4jid('nanoid'); 
        
        foreach my $type ( keys %{$ids_href} ) {
            my $id = $ids_href->{$type};
            print "checking type: $type id: $id neo4jid: $neo4jid \n" if $VERBOSE;
            my $answer = set_a_newid_for_thing($type, $id, $neo4jid); 
            print "... $answer\n";
        }
    }
}


sub update_all_things {

    print "\nStart: update_all_things\n" if $VERBOSE;
    my $counter = 0;
    count_nanoid();
    my $neo4j_id_to_update = get_a_thing_neo4jid('nanoid'); 
    while ($neo4j_id_to_update) {

        print "\n"," *"x35,"\n";
        print "...looking at neo4j: $neo4j_id_to_update\n" if $VERBOSE;
        
        my $ids_href = undef;
        my $ids_are_not_ready_to_assign = 1;
       
        # repeat in this loop till I get a set of ids that 
        # where none of them are in the database
        while ( $ids_are_not_ready_to_assign) {
            $ids_href = generate_ids();  
            my $existing_id_count = check_for_existing_ids($ids_href);
            if ($existing_id_count == 0){
                $ids_are_not_ready_to_assign = 0;
            }
           
            print "\t... new ids\n" if $VERBOSE > 2;
            print Dumper ($ids_href) if $VERBOSE > 2;
        } 
       
        # now do update for all keys
        print "\t... attempting update\n" if $VERBOSE;
        foreach my $type ( keys %{$ids_href} ) {
                
            my $id = $ids_href->{$type};
                print "\t...checking type: $type id: $id neo4jid: $neo4j_id_to_update\n" if $VERBOSE > 1;
                my $answer = set_a_newid_for_thing($type, $id, $neo4j_id_to_update); 
                print "\t... update status: $answer\n" if $VERBOSE > 2;
        }
        
        # now that one neo4j instance is updated 
        $counter++;
        $neo4j_id_to_update = get_a_thing_neo4jid('nanoid');
        print "\t...getting next neo4j thing $neo4j_id_to_update to update\n" if $VERBOSE > 2;
    }
    print "\tSummary: updated $counter things\n" if $VERBOSE;
    count_nanoid();
    print "End: update_all_things\n" if $VERBOSE;
}


sub main {

    # for timings
    print_settings() if $VERBOSE;
    print_header() if $VERBOSE;

    my $bolt_url = construct_bolt_url($SERVER_IP);
    $CXN = Neo4j::Bolt->connect($bolt_url);

    ## my Poka-yoke: don't run this unless you mean it silly goose;
    if (1) {
        #copy_id_to_originalid();
        update_all_things();
        print "This is part of a maze of twisty little passages, all alike.\n";
    }
    elsif (0){
        remove_added_ids();
        print "A hollow voice says 'Fool.'\n";
    }
    else{
        # Um, yeah. You don't know what you are doing. Do ya?
        print "It is pitch black. You are likely to be eaten by a Grue.\n";
    }

    # for timings, ref
    print_footer() if $VERBOSE;
}

main() if not caller();
