# docker run -P -d maj1/test-db-bento-meta
FROM neo4j:3.5.3
MAINTAINER Mark A. Jensen <mark -dot- jensen -at- nih -dot com>
EXPOSE 7474 7473 7687
ADD --chown=neo4j:neo4j data /var/lib/neo4j/data
COPY --chown=neo4j:neo4j neo4j.conf /var/lib/neo4j/conf/neo4j.conf
CMD ["neo4j"]



