#!/bin/bash

# This is a wrapper gets triggered by cron and wraps a Makefile.

# This script will run the Makefile at most NIGHT_SHIFT_MAX_ATTEMPTS times
# If the final attempt produces no errors, this script will never
# output anything.

# However if the final attempt failed, this script
# will print all log output from all previous attempts so that
# cron can send an email.

cd $(dirname $0)/../..
export PATH=$PATH:/usr/local/bin/
source config/night_shift.sh

if [ -f locked ]
then
    exit 0
fi

DATE=$(date +"%Y-%m-%d")

export ATTEMPT_COUNT=$(ls -1H logs/${DATE}/attempt-*.log 2>/dev/null|wc -l|sed 's/ *$//;s/^ *//')
if [ $ATTEMPT_COUNT -gt $NIGHT_SHIFT_MAX_ATTEMPTS ]; then
    exit 0
fi

mkdir -p "logs/${DATE}"

THIS_ATTEMPT=`printf "logs/${DATE}/attempt-%02d.log" ${ATTEMPT_COUNT}`
echo -e "\n\n[+] Starting attempt No ${ATTEMPT_COUNT} with PID $$..." >> $THIS_ATTEMPT
date >> $THIS_ATTEMPT

# To prevent race conditions on the same file and triggering
# MR jobs twice, we only continue if there is no other script in running.
if ps aux | grep -v $$ | grep -v $PPID | egrep '/bin/bash.+[r]un_workflow.sh' >> $THIS_ATTEMPT; then
    echo -e "[!] Detected other run_workflow.sh is still in progress: Aborting" >> $THIS_ATTEMPT

    if [[ "$ATTEMPT_COUNT" -ge $NIGHT_SHIFT_MAX_ATTEMPTS ]]; then
        echo "[!] Max attempts (${NIGHT_SHIFT_MAX_ATTEMPTS}) reached but processing is still running!"
        exit 1
    else
        exit 0
    fi
fi

# Run the main targets:
MAKE_EXIT_CODES=0
# Make won't do anything if everything is ready
for TARGET in "-k -j $NIGHT_SHIFT_PARALLEL_JOBS $NIGHT_SHIFT_TARGETS" $NIGHT_SHIFT_TARGETS backup; do
    echo -e "\n\n[+] Working on target ${TARGET}" >> $THIS_ATTEMPT
    make ${TARGET} >> $THIS_ATTEMPT 2>&1
    LAST_EXIT_CODE=$?
    MAKE_EXIT_CODES=$(expr ${LAST_EXIT_CODE} + ${MAKE_EXIT_CODES})
    echo -e "\n\n[+] Completed ${TARGET}" >> $THIS_ATTEMPT
    date >> $THIS_ATTEMPT
done

# If there were no errors at all or this is the last attempt: clean up
if [[ "$MAKE_EXIT_CODES" -eq 0 || "$ATTEMPT_COUNT" -ge $NIGHT_SHIFT_MAX_ATTEMPTS ]]; then
    make cleanup >> $THIS_ATTEMPT 2>&1
    LAST_EXIT_CODE=$?
    MAKE_EXIT_CODES=$(expr ${LAST_EXIT_CODE} + ${MAKE_EXIT_CODES})
fi

# If this is the last attempt...
if [[ "$ATTEMPT_COUNT" -ge $NIGHT_SHIFT_MAX_ATTEMPTS ]]; then

    # If any of the make targets failed in the final attempt:
    if [[ "$MAKE_EXIT_CODES" -gt 0 ]]; then
        # This will produce cron output, which is emailed to us:
        echo "[!] Final exit code was $MAKE_EXIT_CODES, here are all the logs:"
        cat logs/${DATE}/attempt-*.log
        exit 1
    fi

    # Tests attempts log size.
    python night-shift/tests/attempt_log_sizes.py
    if [[ `echo $?` -gt 0 ]]; then
        ls -l "logs/${DATE}/"
        exit 1
    fi

    echo "Everything is ok."
    exit 0

else
    # Silently ignore error and retry in 30 minutes
    exit 0
fi
