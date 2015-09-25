#!/usr/bin/env pypy

import sys
import argparse
import datetime
import subprocess
from croniter import croniter

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--rule', help='crontab rule from day', required = True)
    parser.add_argument('-c', '--command', help='command to exexute', required = True)
    args = parser.parse_args()

    base = datetime.datetime.now()
    iter = croniter("* * {}".format(args.rule), base)
    run_at = iter.get_next(datetime.datetime)

    if base.date() != run_at.date():
        print 'Skipped, next run at: {}'.format(run_at.date())
        sys.exit(0)

    exit_code = subprocess.call(["/bin/bash", "-e", "-o", "pipefail", "-c", args.command])
    sys.exit(exit_code)