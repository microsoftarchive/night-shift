

# A framework for nightly batch data processing using GNU Make

History
=

In 2013 [@torsten](https://github.com/torsten) wanted to set up a batch job manager for the Wunderlist data pipeline. Evaluating Amazon Data Flow, Oozie and Luigi all seemed to be overkill. Inspired by [Mike Bostock](http://bost.ocks.org/mike/make/) he started out rolling one `Makefile` started by a `cronjob`. In two years this tool has been grown to accomodate the needs and in 2015 we open sourced the skeleton of the add-ons that make your life easier going old skool and seventies or KISS, you may say.

This repo is currently in production reaching out to dozens of sources and running hundreds of SQLs. If you are interested in our setup, check out [this presentation](http://www.slideshare.net/soobrosa/6w-bp-datashow).

Features
=
- has a Makefile wrapper that gets triggered by cron, tries to run it at most MAX_ATTEMPTS times and logs to output so cron can send an email,
- runs all `make` targets in a tracking shell, so timing information, output and errors could be logged,
- produces log files that can be synchronized to a file store (we use S3),
- has a timer script `run_at` for `cron` like target timing,
- has a script to inject conditionals, variableas and Ruby logic into SQL.

What's in `lib`
=
You should run `run_workflow.sh` that will wrap `Makefile`.

What's in `tests`
=
Running `./tests/run.sh` will

- test for makefile target for production,
- collect unused or wrong makefile targets,
- check unused files in the script folder,
- check unused template variables.

There's also a test for checking whether log size is below or above threshold.

## License

Copyright © 2013-2015 6Wunderkinder GmbH.

Distributed under the MIT License.
