# Import the night-shift's boilerplate
include night-shift/lib/boilerplate.mk

scaffold:: intermediate/$(TODAY)
intermediate/$(TODAY):
	mkdir -p $@

imports: scaffold \
         intermediate/$(TODAY)/public.people

intermediate/$(TODAY)/public.people.csv: intermediate/$(TODAY)
	night-shift/lib/run_sql_template.rb --dialect postgres --config config/source_postgres.sh \
		scripts/dump_people.erb.sql > $@

people_path:=/tmp/people.csv
intermediate/$(TODAY)/public.people.moved: intermediate/$(TODAY)/public.people.csv
	cp "$<" "$(people_path)" && echo $(people_path) > $@

intermediate/$(TODAY)/public.people: | intermediate/$(TODAY)/public.people.moved
	night-shift/lib/run_sql_template.rb --dialect postgres --config config/target_postgres.sh --file "`cat $(firstword $|)`" --table people \
		scripts/schema_people.erb.sql \
		scripts/update_table.erb.sql
