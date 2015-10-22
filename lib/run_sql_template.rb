#!/usr/bin/env ruby

require 'erb'
require 'json'
require 'optparse'
require 'shellwords'

def extract_exports(config_file)
  contents = File.read(config_file)
  pairs = contents.scan(/export (\w+)="?(.+?)"?$/)
  Hash[pairs]
end

def get_final_query(expanded_query, mode, options)
  psql_prefix = "\\set ON_ERROR_STOP on\n\\set QUIET on\n"
  if mode == :intermediate or not options[:csv]
    return "#{expanded_query.chomp(';')};" if options[:dialect] == :mysql
    return "#{expanded_query}" if options[:dialect] == :mssql
    return "#{psql_prefix}#{expanded_query.chomp(';')};" if [:postgres, :redshift].include?(options[:dialect])
  else
    if options[:dialect] == :mssql
      # Note: have to add few extra parameters into `sqlcmd`.
      return "#{expanded_query}"
    elsif options[:dialect] == :redshift
      # RedShift cannot copy CSV directly to STDOUT, so
      # we emulate it with some psql settings...
      # For explanations of these options, type \? in psql.
      redshift_copy = "\\a\n\\f ','\n\\t off\n\\pset footer off\n"
      return "#{psql_prefix}#{redshift_copy}\n#{expanded_query.chomp(';')};"
    elsif options[:dialect] == :mysql
      return "#{expanded_query.chomp(';')};"
    elsif options[:dialect] == :postgres
      return "#{psql_prefix} COPY (#{expanded_query.chomp(';')}) TO STDOUT WITH CSV HEADER;"
    end
  end
end

def run_query_with_cli(expanded_query, mode, options)
  if options[:dryrunfirst] or options[:dryrunlast]
    STDERR.puts("Query to execute:\n#{expanded_query}")
    raise "quit because of --dry-run" if options[:dryrunfirst]
    raise "quit because of --dry-run" if options[:dryrunlast] and mode == :final
  end

  if options[:dialect] == :mysql
    env = extract_exports(options[:config])
    cli = IO.popen(". #{options[:config].shellescape} && mysql --default-character-set=latin1 --batch --quick " +
      "-P #{env['MYSQL_PORT']} -u #{env['MYSQL_USER']} #{env['MYSQL_DATABASE']}", "r+")
  elsif options[:dialect] == :mssql
    env = extract_exports(options[:config])
    cmd = ". #{options[:config].shellescape} && sqlcmd -S '#{env['MSSQL_HOST']},#{env['MSSQL_PORT']}' " +
      "-U '#{env['MSSQL_USER']}' -P '#{env['MSSQL_PASSWORD']}' -d '#{env['MSSQL_DATABASE']}' -I "
    if mode == :final and options[:csv]
      cmd += "-h-1 -s',' -W "
    end
    cli = IO.popen(cmd, "r+")
  elsif [:postgres, :redshift].include?(options[:dialect])
    cli = IO.popen(". #{options[:config].shellescape} && psql -X -t", "r+")
  end

  query = get_final_query(expanded_query, mode, options)
  cli.write(query)
  cli.close_write

  # Get the result
  if mode == :intermediate
    result = cli.readlines
  else
    cli.each do |line|
      puts line
    end
    result = nil
  end
  cli.close

  # Write error to STDERR
  if $?.to_i != 0
    STDERR.puts "Failed Query:\n#{expanded_query}\n\n"
    raise "cli exited with #{$?}"
  end

  return result
end

def expand_template_with_context(template, context)
  ostr = Object.new
  ostr.define_singleton_method(:post_process) do |&blk|
    @post_process_block = blk
  end
  ostr.define_singleton_method(:post_process_block) do
    @post_process_block
  end

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

def process_templates(options)
  options[:templates].each_with_index do |template_name, i|
    STDERR.puts "[+] Expanding #{template_name} for database #{options[:dialect]}"

    template_text = File.read(template_name).force_encoding("UTF-8")
    template = ERB.new(template_text)
    expanded_query, ostruct = expand_template_with_context(template, options[:context])

    is_last_query = (i == (options[:templates].size - 1))
    if is_last_query
      run_query_with_cli(expanded_query, :final, options)
    else
      intermediate = run_query_with_cli(expanded_query, :intermediate, options)
      STDERR.puts "\n[+] Got intermediate result #{intermediate.inspect}"

      # If the template defined a post_process_block, execute it here...
      unless ostruct.post_process_block.nil?
        # that modifies common_context for next script
        ostruct.post_process_block.call(intermediate, options[:context])
      end
    end
  end
end

if $0 == __FILE__
  options = {:config => nil, :dialect => nil, :csv => false, :dryrunfirst => false, :dryrunlast => false, :context => {}}
  OptionParser.new do |opt|
    opt.on('-d', '--dialect DIALECT', [:postgres, :mysql, :redshift, :mssql], 'Database dialect (postgres, mysql, redshift, mssql)') { |o| options[:dialect] = o }
    opt.on('-c', '--config CONFIG_FILE', 'Configuration file.') { |o| options[:config] = File.absolute_path(o) }
    opt.on('--csv', "Convert the query's result into CSV") { |o| options[:csv] = true }
    opt.on('-nf', 'Do not execute the first SQL, only print it. Terminate after the first one.') { |o| options[:dryrunfirst] = true }
    opt.on('-nl', 'Do not execute the last SQL, only print it.') { |o| options[:dryrunlast] = true }
    ARGV.select { |attr| attr =~ /^--(\w+)$/ and not ['--config','--dialect','--csv'].include?(attr) } \
        .each { |attr| opt.on("#{attr} VALUE") { |o| options[:context][/^--(\w+)$/.match(attr)[1]] = o } }
  end.parse!
  options[:templates] = ARGV.map { |f| File.absolute_path(f) }

  raise "Need at least one template." if options[:templates].empty?
  raise "Configuration file is required." if options[:context].nil?
  raise "Dialect attribute is required." if options[:dialect].nil?
  raise "Not existing configuration file." if not File.exist?(options[:config])
  raise "Template is not exists." if not options[:templates].map { |f| File.exist?(f) } .all?

  process_templates(options)
end
