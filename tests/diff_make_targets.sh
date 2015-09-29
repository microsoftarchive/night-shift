#!/bin/bash

set -e

source config/night_shift.sh
export TODAY=_test_

make clean-test SHELL=/bin/bash > /dev/null
python night-shift/tests/diff_make_targets.py \
  <(make scaffold | grep -v '^make:' | sed -e 's/^mkdir -p //g' && make -tk $NIGHT_SHIFT_TARGETS backup  | grep -v '^make:' | sed -e 's/^touch //g' && echo "$NIGHT_SHIFT_TARGETS backup" | tr ' ' '\n' ) \
  <(make list-all-targets SHELL=/bin/bash | grep -vE $NIGHT_SHIFT_EXCEPTIONS)
make clean-test SHELL=/bin/bash > /dev/null