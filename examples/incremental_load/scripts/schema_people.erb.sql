-- CREATE TABLE "people" (
--   id int,
--   full_name varchar(255) NULL,
--   date_of_birth date NULL,
--   updated_at date NULL
-- );

<%

context["specs"] = [
  ["id", "int"],
  ["full_name", "varchar(255) NULL"],
  ["date_of_birth", "date NULL"],
  ["updated_at", "date NULL"],
]

context["columns"] = context["specs"].map {|col, type| col}
context["updates"] = context["columns"].select {|c| c != "id"}.map {|c| "#{c} = tmp.#{c}"}

%>