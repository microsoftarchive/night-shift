#!/usr/bin/env pypy

import os
import re
import io
import sys
import json
import random
import datetime
import logging
import trackingshell as ts

class MakeTarget(ts.MakeTarget):
    # void
    def set_logger(self):
        log_dir = 'logs/{}'.format(str(self.date))
        if not os.path.exists(log_dir): return

        handler = logging.FileHandler(os.path.join(log_dir, 'trackingshell.log'))
        handler.setFormatter(logging.Formatter('%(levelname)s\t%(asctime)s\t%(name)s\t%(target)s\t%(command)s\t%(message)s'))
        self.logger.setLevel(logging.WARNING)
        self.logger.addHandler(handler)

    # bool
    def is_log_directory_target(self):
        return bool(re.match(ur'^logs/\d{4}-\d{2}-\d{2}$', self.target))

    # bool
    def is_log_target(self):
        return bool(re.match(ur'^logs/\d{4}-\d{2}-\d{2}/.*$', self.target))

    # bool
    def is_results_target(self):
        return bool(re.match(ur'^results/\d{4}-\d{2}-\d{2}/.*$', self.target))

    # bool
    def is_big_data_file(self):
        return self.target.endswith((".gz", ".csv", ".json", ".zip", ".xml"))

@ts.only_run_in_make_level
@ts.plugin
def target_plugin(mt, next_plugin_fn):
    if mt.is_log_directory_target():
        mt.command = "({}) 2>&1".format(mt.command)

    else:
        path = "logs/{}/{}.log".format(mt.date, mt.target.replace("/", "_"))
        attempt_nr = os.environ.get('ATTEMPT_COUNT', "NULL")

        try:
            with io.open(path, "a", encoding='utf-8') as fd:
                fd.write(u"\n[tracking_shell {}] Working on target {} attempt {} command {}\n\n" \
                    .format(datetime.datetime.now(), mt.target, attempt_nr, repr(mt.command)))
                fd.flush()
            mt.command = "({}) 2>&1 | tee -a {}".format(mt.command, path)

        except IOError:
            mt.logger.error(u'Could not open target log `{}`'.format(path), extra = mt.as_dict())
            mt.command = "({}) 2>&1".format(mt.command)

    return next_plugin_fn(mt)

@ts.plugin
def timing_env_plugin(mt, next_plugin_fn):
    try:
        with io.open("logs/{}/timing_env.log".format(mt.date), "a", encoding = 'utf-8') as fd:
            data = {
                'command': mt.command.replace('\n', ''),
                'target': mt.target,
                'unique_nr': random.randint(0, 1000000),
                'has_make_level': mt.has_makelevel(),
                'started_at': datetime.datetime.now().isoformat(),
                'tag': 'BEGIN'
            }
            fd.write(u"{}\n".format(json.dumps(data)))
            fd.flush()

            exit_code = next_plugin_fn(mt)

            data.update({
                'tag': 'END',
                'finished_at': datetime.datetime.now().isoformat(),
                'exit_code': exit_code
            })
            fd.write(u"{}\n".format(json.dumps(data)))
            fd.flush()
    
    except IOError:
        exit_code = next_plugin_fn(mt)

    return exit_code

if __name__ == '__main__':
    shell = ts.Shell(sys.argv[1:])
    shell.parser.add_argument('-d', '--date', help="current date")
    shell.cls = MakeTarget
    shell.plugins.register(timing_env_plugin)
    shell.plugins.register(target_plugin)
    shell.delegate()