from __future__ import print_function
import re
import sys
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='diff_make_targets', \
        description="Compares makefile's targets and returns the unused ones")
    parser.add_argument('production_targets_file', type=argparse.FileType('r'), \
        help='list of targets which running in production')
    parser.add_argument('all_targets_file', type=argparse.FileType('r'), \
        help="list of all makefile's target")
    args = parser.parse_args()

    production_targets = set(map(str.strip, args.production_targets_file.readlines()))
    pattern_targets = set(map(str.strip, args.all_targets_file.readlines())) - production_targets

    for pattern_target in list(pattern_targets):
        r_pattern = pattern_target.replace('%', '.+')
        if r_pattern.endswith('/'):
            r_pattern = r_pattern[:-1]
        
        re_target = re.compile(r'^{}$'.format(r_pattern))
        for prod_target in production_targets:
            if re_target.match(prod_target):
                pattern_targets.remove(pattern_target)
                break

    if len(pattern_targets) == 0:
        print("No unused target found")
        sys.exit(0)

    print("Unused targets:\n")
    print('\n'.join(sorted(list(pattern_targets))))
    sys.exit(1)