from __future__ import print_function
import io
import os
import re
import sys
import glob
import shlex
import argparse

def get_commands(fd):
    current_command, concat_next = [], False
    for line in args.commands_file.readlines():
        trimmed_line = line.strip()
        concat_next = trimmed_line.endswith('\\')
        current_command.append(trimmed_line.strip('\\'))

        if concat_next:
            continue

        yield ' '.join(current_command)
        current_command = []

def parse_command(command):
    attrs = filter(lambda x: x not in ('dialect', 'config', 'csv'), re.findall('--(\w+)', command, re.I))
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dialect')
    parser.add_argument('-c', '--config')
    parser.add_argument('--csv', action='store_true')
    for attr in attrs:
        parser.add_argument('--{}'.format(attr))
    parser.add_argument('templates', nargs="+")
    args = parser.parse_args(shlex.split(command)[1:])
    return set(attrs), args.templates

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('commands_file', type=argparse.FileType('r'), help='make -n result file')
    args = parser.parse_args()

    warnings, errors = [], []
    commands = map(lambda x: re.split('\>|\|', x)[0].strip(), filter(lambda x: x.startswith('night-shift/lib/run_sql_template.rb'), get_commands(args.commands_file)))

    for command in commands:
        attrs, templates = parse_command(command)
        founded = set([])
        if not all(map(os.path.exists, map(os.path.abspath, templates))):
            print(map(os.path.abspath, templates))
            print(map(os.path.exists, map(os.path.abspath, templates)))
            warnings.append( ' => SQL template file is not exists at `{}`'.format(template) )
            continue

        for template in templates:
            with io.open(os.path.abspath(template), 'r', encoding='utf-8') as fd:
                content = fd.read()
                for attr in attrs:
                    res = re.findall('(\<\%\= ' + attr + ' \%\>|\#\{' + attr + '}|\<\%.*' + attr + '.*\%\>)', content)
                    if res:
                        founded.add(attr)

        if not attrs.issubset(founded):
            errors.append( ' => `{}` at `{}`'.format(', '.join(attrs-founded), ' '.join(templates)) )

    if warnings:
        print()
        print('Warnings during the unsued template variable investigation:')
        print('\n'.join(warnings))

    if errors:
        print
        print('Unused template variables were found:')
        print('\n'.join(errors))
        sys.exit(1)
    else:
        print('No unused template variable found.')

    sys.exit(0)