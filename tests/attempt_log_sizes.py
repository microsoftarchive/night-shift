from __future__ import print_function
import os
import sys
import glob
import argparse
import datetime

# datetime.date
def valid_date(s):
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()

    except ValueError:
        msg = "Not a valid date: `{}`.".format(s)
        raise argparse.ArgumentTypeError(msg)

# float
def median(lst):
    if not lst:
        return None
    elif len(lst) % 2 == 1:
        return sorted(lst)[((len(lst)+1)/2)-1]
    else:
        return float(sum(sorted(lst)[(len(lst)/2)-1:(len(lst)/2)+1]))/2.0

# list<int>
def get_log_size_for_date(date):
    return sum(map(os.path.getsize, map(os.path.abspath, glob.glob("logs/{}/attempt-*.log".format(str(date))))))

# list<int>
def get_log_size_for_last_week(date):
    return filter(lambda v: v, [ get_log_size_for_date(date - datetime.timedelta(days=i)) for i in range(7) ])

# tuple<int,int,int>
def get_median_thresholds(lst):
    median_value = median(lst)
    return int(median_value * 0.9), int(median_value), int(median_value * 1.15)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='test_log_sizes')
    parser.add_argument('-d', '--date', help="current date", type=valid_date, default=str(datetime.date.today()))
    args = parser.parse_args()

    log_sizes_lst = list(get_log_size_for_last_week(args.date))
    if not log_sizes_lst:
        print('[!] No log files were found!')
        sys.exit(0)

    if len(log_sizes_lst) < 5:
        print('[!] Not enough log files are available!')
        sys.exit(0)

    min_thr, _, max_thr = get_median_thresholds(log_sizes_lst)
    today_log_size = get_log_size_for_date(args.date)
    if today_log_size > max_thr or today_log_size < min_thr:
        print('[!] Log size is below or above threshold:')
        print('Expected min: {min_thr} < actual: {actual} < max: {max_thr}' \
            .format(min_thr=min_thr, max_thr=max_thr, actual=today_log_size))
        sys.exit(1)

    sys.exit(0)
