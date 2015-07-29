#!/usr/bin/env pypy
import argparse
import datetime
import io
import os
import random
import re
import sys
import boto3
import urllib
import subprocess
import json

def is_log_directory_target(target):
    return bool(re.match(ur'^logs/\d{4}-\d{2}-\d{2}$', target))

def now():
    return datetime.datetime.now().isoformat()

def only_run_for_make_level(f):
    def wrapper(target, next_plugin_fn = None):
        if target.is_makelevel():
            return f(target, next_plugin_fn)

        return next_plugin_fn(target)

    return wrapper

class MakeTarget:
    def __init__(self, file_name, date, command):
        self.file_name = file_name
        self.command = command
        self.date = date

    def is_makelevel(self):
        return "MAKELEVEL" in os.environ

# hooks will work similar node.js's exporess middlewares
# lowest-level: root_plugin: run target; return exit code
#   middlware can change target and react to exit code

def log_per_target_plugin(target, next_plugin_fn):
    if not target.is_makelevel():
        target.command = target.command
    elif is_log_directory_target(target.file_name):
        target.command = "({}) 2>&1".format(target.command)
    else:
        target_log_path = "logs/%s/%s.log" % (target.date, target.file_name.replace("/", "_"))
        attempt = os.environ.get('ATTEMPT_COUNT', "NULL")
        try:
            with io.open(target_log_path, "a", encoding='utf-8') as fd:
                fd.write(u"\n[tracking_shell {}] Working on target {} attempt {} command {}\n\n" \
                    .format(now(), target.file_name, attempt, repr(target.command)))
                fd.flush()
            target.command = "({}) 2>&1 | tee -a {}".format(target.command, target_log_path)
        except IOError:
            sys.stderr.write(u'tracking_shell: Could not open log %r\n' % target_log_path)
            sys.stderr.flush()
            target.command = "({}) 2>&1".format(target.command)
    return next_plugin_fn(target)

def log_timing_plugin(target, next_plugin_fn):
    timing_log = None
    timing_log_path = "logs/%s/timing_env.log" % target.date
    timing_log_data = {
        'command': target.command.replace('\n', ''),
        'target': target.file_name,
        'unique_nr': random.randint(0, 1000000),
        'has_make_level': target.is_makelevel(),
        'started_at': now(),
        'tag': 'BEGIN'
    }
    try:
        timing_log = io.open(timing_log_path, "a")
        timing_log.write(u"{}\n".format(json.dumps(timing_log_data)))
        timing_log.flush()
    except IOError:
        pass
    exit_code = next_plugin_fn(target)
    if timing_log:
        timing_log_data.update({
            'tag': 'END',
            'finished_at': now(),
            'exit_code': exit_code
        })
        timing_log.write(u"{}\n".format(json.dumps(timing_log_data)))
        timing_log.flush()
    return exit_code

def is_big_data_file(file_name):
    return file_name.endswith((".gz", ".csv", ".json"))

def s3_object_for_target(bucket_name, target, instance_id):
    s3 = boto3.resource('s3')
    path_without_date = re.sub(r'/\d{4}-\d{2}-\d{2}/', '/', target.file_name)
    key_name = os.path.join("data-flow", target.date, instance_id, path_without_date)
    return s3.Object(bucket_name, key_name)

@only_run_for_make_level
def upload_to_s3_plugin(target, next_plugin_fn):
    exit_code = next_plugin_fn(target)
    bucket_name = os.environ.get('S3_BUCKET')
    instance_id = os.environ.get('INSTANCE_ID', 'UNKNOWN-INSTANCE-ID')
    if bucket_name:
        if exit_code == 0 and os.path.exists(target.file_name):
            s3_object = s3_object_for_target(bucket_name, target, instance_id)
            if is_big_data_file(target.file_name):
                sys.stderr.write("tracking_shell: Will S3-upload empty %s\n" % target.file_name)
                s3_object.put(Body="EMPTY_STUB_CONTENT_FOR_TOO_LARGE_FILES")
            elif os.path.isfile(target.file_name):
                with open(target.file_name, 'rb') as target_content:
                    sys.stderr.write("tracking_shell: Will S3-upload %s\n" % target.file_name)
                    s3_object.put(Body=target_content)
    else:
        sys.stderr.write("tracking_shell: S3_BUCKET env var not set, will not upload to S3.\n")
    return exit_code

def root_plugin(target, next_plugin_fn):
    assert next_plugin_fn is None, "root_plugin requires that no next plugin is given."
    return subprocess.call(["/bin/bash", "-e", "-o", "pipefail", "-c", target.command])

def wrap_plugins(plugins):
    next_plugin, rest = plugins[0], plugins[1:]
    return lambda target: next_plugin(target, wrap_plugins(rest) if rest else None )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='tracking_shell')
    parser.add_argument('-t', '--target', help="name of the make target", nargs="?")
    parser.add_argument('-d', '--date', help="current date", nargs="?")
    parser.add_argument('-c', '--command', help="command to execute", required=True)
    args = parser.parse_args()

    # TODO: Create this list dynamically from plugins
    plugins = [
        upload_to_s3_plugin,
        log_timing_plugin,
        log_per_target_plugin,
        root_plugin
    ]

    target = MakeTarget(args.target or 'no-target', args.date, args.command)
    plugin_chain = wrap_plugins(plugins)
    exit_code = plugin_chain(target)
    sys.exit(exit_code)
