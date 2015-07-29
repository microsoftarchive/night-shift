ifndef TODAY
  TODAY:=$(shell date +%Y-%m-%d)
endif

TMP_TOKEN:=$(shell date +%H%M%S)

# `date` behaves different on Mac and Linux, so we need to check the platform here:
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

#
# Lists all available targets from the makefile
#

list-all-targets:
	@egrep -h '^[a-zA-Z][^# :=]+:([^=]|$$)' Makefile *.mk | cut -d: -f1 | sed -e 's/$$(TODAY)/'$(TODAY)'/g'
