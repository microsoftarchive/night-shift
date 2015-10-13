\set QUIET off
\timing

BEGIN;

CREATE TEMPORARY TABLE "tmp_<%= table %>" (
  <%= specs.map {|col, type| "#{col} #{type}"}.join(", ") %>
);

COPY "tmp_<%= table %>" (
  <%= columns.join ", " %>
)
FROM '<%= file %>'
DELIMITER E'\001' NULL '';

UPDATE "<%= table %>" SET
  <%= updates.join ", " %>
FROM "tmp_<%= table %>" AS tmp
WHERE tmp.updated_at > "<%= table %>".updated_at
  AND "<%= table %>".id = tmp.id;

INSERT INTO "<%= table %>" ( <%= columns.join "," %> )
(
  SELECT
    <%= columns.join "," %>
  FROM "tmp_<%= table %>" AS tmp
  WHERE tmp.id NOT IN (SELECT id FROM "<%= table %>")
);

END;