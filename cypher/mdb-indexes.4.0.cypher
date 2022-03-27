create index if not exists for (n:node) on (n.nanoid);
create index if not exists for (n:relationship) on (n.nanoid);
create index if not exists for (n:property) on (n.nanoid);
create index if not exists for (n:value_set) on (n.nanoid);
create index if not exists for (n:term) on (n.nanoid);
create index if not exists for (n:origin) on (n.nanoid);
create index if not exists for (n:tag) on (n.key, n.value);

call db.index.fulltext.createNodeIndex('termDefn', ['term'], ['origin_definition'],
  {`fulltext.eventually_consistent`:'true',`fulltext.analyzer`:'standard-no-stop-words'});
call db.index.fulltext.createNodeIndex('termValue', ['term'], ['value'],
  {`fulltext.eventually_consistent`:'true',`fulltext.analyzer`:'standard-no-stop-words'});
call db.index.fulltext.createNodeIndex('termValueDefn', ['term'], ['origin_definition','value'],
  {`fulltext.eventually_consistent`:'true',`fulltext.analyzer`:'standard-no-stop-words'});
call db.index.fulltext.createNodeIndex('tagKeyValue', ['tag'], ['key','value'],
  {`fulltext.eventually_consistent`:'true',`fulltext.analyzer`:'standard-no-stop-words'});

call db.index.fulltext.createNodeIndex('nodeHandle', ['node'], ['handle'],
  {`fulltext.eventually_consistent`:'true',`fulltext.analyzer`:'standard-no-stop-words'});
call db.index.fulltext.createNodeIndex('edgeHandle', ['relationship'], ['handle'],
  {`fulltext.eventually_consistent`:'true',`fulltext.analyzer`:'standard-no-stop-words'});
call db.index.fulltext.createNodeIndex('nodeHandle', ['property'], ['handle'],
  {`fulltext.eventually_consistent`:'true',`fulltext.analyzer`:'standard-no-stop-words'});
call db.index.fulltext.createNodeIndex('entityHandle', ['node','property','relationship'], ['handle'],
  {`fulltext.eventually_consistent`:'true',`fulltext.analyzer`:'standard-no-stop-words'});


