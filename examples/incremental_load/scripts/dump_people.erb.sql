\set ON_ERROR_STOP on

COPY (
  SELECT
    id,
    full_name,
    date_of_birth,
    updated_at
  FROM t_people
  WHERE updated_at >= CURRENT_DATE - interval '7 days'
)
TO STDOUT
CSV DELIMITER E'\001';
