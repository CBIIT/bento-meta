create index if not exists for (n:node) on (n.nanoid);
create index if not exists for (n:relationship) on (n.nanoid);
create index if not exists for (n:property) on (n.nanoid);
create index if not exists for (n:value_set) on (n.nanoid);
create index if not exists for (n:term) on (n.nanoid);
create index if not exists for (n:origin) on (n.nanoid);
create index if not exists for (n:tag) on (n.key, n.value);

create fulltext index termDefn for (t:term) on each [t.origin_definition];
create fulltext index termValue for (t:term) on each [t.value];
create fulltext index termValueDefn for (t:term) on each [t.value, t.origin_defintion];

create fulltext index tagKeyValue for (g:tag) on each [g.key, g.value];

create fulltext index nodeHandle on (n:node) on each [n.handle];
create fulltext index edgeHandle on (n:relationship) on each [n.handle];
create fulltext index propHandle on (n:property) on each [n.handle];


