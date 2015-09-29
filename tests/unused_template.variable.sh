#!/bin/bash

set -e

source config/night_shift.sh
export TODAY=_test_

make clean-test SHELL=/bin/bash > /dev/null
python night-shift/tests/unused_template_variable.py <(make -n $NIGHT_SHIFT_TARGETS)
make clean-test SHELL=/bin/bash > /dev/null
