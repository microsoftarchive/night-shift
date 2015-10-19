

# A framework for nightly batch data processing using GNU Make

In 2013 [@torsten](https://github.com/torsten) wanted to set up a batch job manager for the Wunderlist data pipeline. Evaluating Amazon Data Flow, [Oozie](http://oozie.apache.org) and [Luigi](http://luigi.readthedocs.org/en/stable/) all seemed to be overkill. Inspired by [Mike Bostock](http://bost.ocks.org/mike/make/) he started out rolling one `Makefile` started by a `cronjob`. In two years this tool has been grown to accomodate the needs and in 2015 we open sourced the **skeleton** of the add-ons that make your life easier going old skool and seventies or KISS, you may say.

This repo is currently in production reaching out to dozens of sources and running hundreds of SQLs. If you are interested in our setup, check out [this presentation](http://www.slideshare.net/soobrosa/6w-bp-datashow).

## Features

- `Makefile` wrapper that gets triggered by `cron`. It tries to run it at most `MAX_ATTEMPTS` times.
- Runs all make targets in a [trackingshell](https://github.com/wunderlist/trackingshell), so timing information, output and errors could be logged. You can add extra steps too (e.g.: upload results into S3).
- Has a timer script for `cron` like target timing.
- Has a script to inject conditionals, variables and `Ruby` logic into `SQL`.
- Converts `SQL` results into `CSV` from **mysql**, **postgresql** and **redshift**.
- Tests to keep your makefile clean.
- Has a `Flask` application to monitor your logs.

## Principles

Our mantra is "_Keep it simple_" and "_Don't re-invent the wheel_". According to this we have a few solid principles:

- Use `cron` for scheduling.
- Use `make` for dependencies, partial results, and retries.
- Glue everything together with a hand full of bash script.
	1. Most process handling and output redirection should be handled by `bash` and `make`. Because they are good at it and it is more work to do right in `Ruby` or `Python`.
	2. All complex logic (and math) should be in `Ruby` or `Python`.
- Use `Python` or `Ruby` for the actual workers.
- Inject variables and logic into SQL with Ruby's `ERB`.


## How you can use it?

1. Create a directory for your data-flow.
2. Add night-shift as submodule.

   ```
   $ git submodule add git@github.com:wunderlist/night-shift.git
   ```

3. Install dependencies.

   ```bash
   $ pip install -r requirements.txt
   $ pip install -r web/requirements.txt # for web interface
   ```

4. Create a folder for config files and scripts.

   ```
   $ mkdir config scripts
   ```
 
5. Set your configurations. You can find samples in the `night-shift/config` directory. 

   ```bash
   $ cp night-shift/config/dialect_postgres.sh.sample config/dbname_postgres.sh
   $ nano config/dbname_postgres.sh
   ```
    
   Change the informations in the file.
    
   ```sh
   export PGHOST="localhost"
   export PGPORT=5432
   export PGDATABASE="dbname" 
   export PGUSER="username" 
   export PGPASSWORD="password"
   ```

6. Create a `makefile`.

   ```bash
   $ echo "include night-shift/lib/boilerplate.mk" > makefile
   ```

7. Write your own make targets. You can extend the build in targets like:
   - **scaffold**: Create necessary  directory structure.
   - **nuke**: Removes every files. Gives you a clean slate during development.
   - **cleanup**: Terminate pending resources.
   - **backup**: Backup files after the nightly.

   Extending is easy (use `::` after the target's name):
   
   ```makefile
   scaffold:: intermediate/$(TODAY)
   intermediate/$(TODAY):
     mkdir -p $@
   ```

8. Set up your night-shift configuration file.

   ```bash
   $ cp night-shift/config/night_shift.sh.sample config/night_shift.sh
   $ nano config/night_shift.sh
   ```
   
   Add your up level targets after `scaffold` what you want to execute.
   
   ```sh
   export NIGHT_SHIFT_TARGETS="scaffold"
   ```
   
   Set data-flow directory's path.

   ```sh
   export NIGHT_SHIFT_PROJECT_DIR=""
   ```

9. **(On production)** Extend your `cron` settings. with

   ```bash
   source config/night_shift.sh && night-shift/lib/run_workflow.sh 
   ```

## Examples

You can check out the `examples` folder for working examples.


## License

Copyright © 2013-2015 6Wunderkinder GmbH.

Distributed under the MIT License.

