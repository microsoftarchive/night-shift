#!/usr/bin/env ruby

require 'erb'
require 'json'


def parse_arguments(argv)
  state = :template
  templates = []
  common_context = {}
  varname = nil

  argv.each do |arg|
    case state
    when :template
      if arg =~ /^--(\w+)$/
        state = :variable
        varname = $1
      else
        templates << arg
      end
    when :variable
      common_context[varname] = arg
      state = :template
    end
  end

  raise "Bad final state: #{state}" if not state == :template
  raise "Need at least one template" if templates.empty?

  [templates, common_context]
end

def db_config_path(file)
  return File.absolute_path(File.dirname(__FILE__) + "/../config/" + file)
end

def redshift_aws_creds
  file = db_config_path("nightly_aws_credentials.json")
  json = JSON.load(File.read(file))
  access = json['aws_access_key_id']
  secret = json['aws_secret_access_key']

  "'aws_access_key_id=#{access};aws_secret_access_key=#{secret}'"
end

def extract_exports(credentials_file)
  contents = File.read(credentials_file)
  pairs = contents.scan(/export (\w+)="?(.+?)"?$/)
  Hash[pairs]
end

def run_query_with_cli(expanded_query, mode, db)
  if db =~ /mysql/
    warehouse_credentials = db_config_path("#{db}_credentials.sh")
  elsif db.to_s.start_with? "redshift"
    warehouse_credentials = db_config_path("#{db}_pg_credentials.sh")
  else
    raise "Don't know how to log in to database '#{db}'"
  end

  cli = if db =~ /mysql/
    env = extract_exports(warehouse_credentials)
    cli = IO.popen(". #{warehouse_credentials} && mysql --default-character-set=latin1 --batch --quick " +
      "-P #{env['MYSQL_PORT']} -u #{env['MYSQL_USER']} #{env['MYSQL_DATABASE']}", "r+")
  else
    # `source` is not available in vanilla /bin/sh but `.` is:
    cli = IO.popen(". #{warehouse_credentials} && psql -X -t", "r+")
  end

  prefix = "\\set ON_ERROR_STOP on\n\\set QUIET on\n"

  if mode == :intermediate
    if db =~ /mysql/
      cli.write(expanded_query + ";")
    else
      cli.write(prefix + expanded_query + ";")
    end

    cli.close_write

    result = cli.readlines
    cli.close

    if $?.to_i != 0
      STDERR.puts "Failed Query:\n#{expanded_query}\n\n"
      raise "cli exited with #{$?}"
    end

    return result
  else
    # This script supports an optional --FINALLY-- marker
    # to split an expanded template into two parts:
    # 1) A setup_query for setting up temporary views, etc.
    # 2) A final_query which will be the CSV result.
    if expanded_query =~ /^\s*-- *FINALLY *--\s*$/
      setup_query, final_query = expanded_query.split("-- FINALLY --", 2)
    else
      setup_query = ""
      final_query = expanded_query
    end

    # RedShift cannot copy CSV directly to STDOUT, so
    # we emulate it with some psql settings...
    if db.to_s.start_with? "redshift"
      # For explanations of these options, type \? in psql.
      redshift_copy = "\\a\n\\f ','\n\\t off\n\\pset footer off\n"
      cli.write("#{prefix}#{redshift_copy}#{setup_query}\n#{final_query};")
    elsif db =~ /mysql/
      cli.write("#{setup_query}\n#{final_query};")
    else
      cli.write("#{prefix}#{setup_query} COPY (#{final_query}) TO STDOUT
                 WITH CSV HEADER;")
    end

    cli.close_write
    cli.each do |line|
      puts line
    end
    cli.close

    if $?.to_i != 0
      STDERR.puts "Failed Query:\n#{expanded_query}\n\n"
      raise "cli exited with #{$?}"
    end

    return nil
  end
end

def expand_template_with_context(template, context)
  ostr = Object.new
  ostr.define_singleton_method(:post_process) do |&blk|
    @post_process_block = blk
  end
  ostr.define_singleton_method(:post_process_block) do
    @post_process_block
  end
  ostr.define_singleton_method(:aws_creds) do
    redshift_aws_creds
  end
  # ostr.define_singleton_method(:segment) do
  #   "(select distinct id as user_id from real.users)"
  # end

  # Define each key in context as a instance method for the context object
  context.each do |k, v|
    ostr.define_singleton_method(k.to_sym) do
      v
    end
  end

  bound = ostr.instance_eval { binding() }
  expanded_query = template.result(bound)
  expanded_query.gsub!(/\n+/m, "\n")

  [expanded_query, ostr]
end

def process_templates_with_context(templates, common_context)
  if common_context["db"].nil?
    db = :postgres
  else
    db = common_context["db"].to_sym
  end

  templates.each_with_index do |template_name, i|
    STDERR.puts "[+] Expanding #{template_name} for database #{db}"

    template_text = File.read(template_name).force_encoding("UTF-8")
    template = ERB.new(template_text)
    expanded, ostruct = expand_template_with_context(template, common_context)

    # STDERR.puts "\n[+] Expanded to\n#{expanded}"

    is_last_query = (i == (templates.size - 1))
    if is_last_query
      run_query_with_cli(expanded, :final, db)
    else
      intermediate = run_query_with_cli(expanded, :intermediate, db)
      STDERR.puts "\n[+] Got intermediate result #{intermediate.inspect}"

      # If the template defined a post_process_block, execute it here...
      unless ostruct.post_process_block.nil?
        # that modifies common_context for next script
        ostruct.post_process_block.call(intermediate, common_context)
      end
    end
  end
end


if $0 == __FILE__
  templates, common_context = parse_arguments(ARGV)
  process_templates_with_context(templates, common_context)
end
