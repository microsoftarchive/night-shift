ifndef TODAY
  TODAY:=$(shell date +%Y-%m-%d)
endif

TMP_TOKEN:=$(shell date +%H%M%S)

# `date` behaves different on Mac and Linux, so we need to check the platform here.
ifeq ($(shell uname -s),Darwin)
  YESTERDAY:=$(shell date -v-1d +%Y-%m-%d)
  YESTERDAY_SLASHED:=$(shell date -v-1d +%Y/%m/%d)
else
  YESTERDAY:=$(shell date --date="1 day ago" +%Y-%m-%d)
  YESTERDAY_SLASHED:=$(shell date --date="1 day ago" +%Y/%m/%d)
endif

# Generate a unique suffix to the target name so that parallel running
# make processes do not overwrite other temp files.
TMP_OUT=$@.$(TMP_TOKEN).tmp

# Define the tracking shell (you can redefine it in your Makefile).
SHELL=./night-shift/lib/tracking_shell.py --target $@ --date $(TODAY)

.PHONY: all nuke scaffold backup clean-test cleanup

# All target is disabled.
all:
	@echo Specify target

# Scaffolding directory structure (please redefine).
scaffold:: logs/$(TODAY)/

# Folder for logs.
logs/$(TODAY)/:
	mkdir -p $@

# Clean-up targets. WARNING: Use nuke only during development!
nuke::

# Cleanup terminates any pending resources (please redefine).
cleanup::

# Clean-up test folders.
clean-test::
	@rm -rf logs/_test_
	@mkdir -p logs/_test_

# Lists all available targets from the makefile.
list-all-targets:
	@egrep -h '^[a-zA-Z][^# :=]+:([^=]|$$)' Makefile *.mk | cut -d: -f1 | sed -e 's/$$(TODAY)/'$(TODAY)'/g'

# Backup after the target execution is finished (please redefine)
# WARNING: Order is important. This has to be the last target in this dependency list!
# It should be the same ones as you can find in the `config/night_shift.sh`.
backup::
