import os
import re
import io
import datetime
import argparse
from math import log
from flask import *
from functools import wraps
from dateutil.parser import parse as parse_datetime

app  = Flask(__name__)

class Logs(object):
    # void
    def __init__(self, dir_project, date = None):
        self.dir_project = os.path.abspath(dir_project)
        self.dir_logs = os.path.join(self.dir_project, 'logs')
        self.rexp_dir_date = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        self.date_str = date or self.get_last_log_date() or str(datetime.date.today())
        self.date = parse_datetime(self.date_str).date()
        self.dir_date = os.path.join(self.dir_logs, self.date_str)

    # str
    def get_log_id(self, target):
        return target.replace("/", "_").replace('.','_')

    # str
    def get_content(self, file_path):
        if not os.path.exists(file_path):
            return None

        return io.open(file_path, 'r', encoding='utf-8').read().strip()

    # list<str>
    def find_available_log_dates(self):
        if not os.path.exists(self.dir_logs):
            return []

        return sorted(filter(lambda dir: self.rexp_dir_date.match(dir), os.listdir(self.dir_logs)))

    # str
    def get_last_log_date(self):
        log_dates = self.find_available_log_dates()
        return log_dates[-1] \
            if log_dates \
            else []

class TrackingShellLog(Logs):
    # str
    def get_timing_env_log_content(self):
        path = os.path.join(self.dir_date, 'timing_env.log')
        if os.path.exists(path):
            return io.open(path, 'r', encoding='utf-8').read()
        return u''

    # tupe<list<dict>,list<str>>
    def find_timing_env_commands(self):
        content = self.get_timing_env_log_content()
        if not content: return [], set(['Timing env log is not found!'])

        commands, ordered_commands, errors = {}, [], set()
        for line in content.split('\n'):
            try:
                data = json.loads(line)
            except:
                continue

            cmd_hash_key = (data['command'],data['unique_nr'])
            if cmd_hash_key not in commands.keys() and data['tag'] == 'BEGIN':
                commands[cmd_hash_key] = data
                commands[cmd_hash_key]['tags'] = [data['tag']]
                ordered_commands.append(commands[cmd_hash_key])

            elif cmd_hash_key in commands.keys() and data['tag'] in commands[cmd_hash_key]['tags']:
                errors.add('Found duplicated command: {}'.format(cmd))

            elif cmd_hash_key in commands.keys() and data['tag'] == 'END':
                commands[cmd_hash_key].update(data)
                commands[cmd_hash_key]['tags'].append(data['tag'])

            else:
                errors.add('Unknown error: {}'.format(cmd))

        for command in ordered_commands:
            command['started_at'] = parse_datetime(command['started_at'])
            if 'finished_at' in command: command['finished_at'] = parse_datetime(command['finished_at'])

        return ordered_commands, errors

    # str
    def get_timing_env_command_status(self, cmd_dict):
        if cmd_dict.get('started_at') and cmd_dict.get('finished_at'):
            return 'success' if cmd_dict['exit_code'] == 0 else 'failure'

        elif cmd_dict['date'] == datetime.date.today():
            return 'running'

        return 'timeout'

    # tuple<list<dict>,list<str>>
    def get_timing_env_commands_dict(self):
        ordered_commands, errors = self.find_timing_env_commands()
        if not ordered_commands: return ordered_commands, errors

        first_command_started_at, attempt_dict = ordered_commands[0]['started_at'], {}
        for cmd_dict in ordered_commands:
            started_at, finished_at = cmd_dict.get('started_at'), cmd_dict.get('finished_at', datetime.datetime.now())
            cmd_dict['date'] = started_at.date()
            cmd_dict['status'] = self.get_timing_env_command_status(cmd_dict)
            cmd_dict['waited'] = (started_at-first_command_started_at).total_seconds() / 60
            cmd_dict['length'] = (finished_at-started_at).total_seconds() / 60
            cmd_dict['log_id'] = self.get_log_id(cmd_dict['target'])
            attempt_dict.setdefault((cmd_dict['target'],cmd_dict['command']), 0)
            attempt_dict[(cmd_dict['target'],cmd_dict['command'])] += 1
            cmd_dict['attempt_nr'] = attempt_dict[(cmd_dict['target'],cmd_dict['command'])]

        return ordered_commands, errors

class TargetLogs(Logs):
    TARGET_LOG_IGNORE = ['timing_env','attempt','trackingshell']

    # str
    def get_path_by_log_id(self, log_id):
        for file_path in self.find_target_log_files():
            rel_file_path = os.path.relpath(file_path, self.dir_date)
            name, _ = os.path.splitext(rel_file_path)
            if self.get_log_id(name) == log_id:
                return file_path

    # list<str>
    def find_target_log_files(self):
        if not os.path.exists(self.dir_date):
            return []

        return [ os.path.join(self.dir_date, f) \
            for f in os.listdir(self.dir_date) \
            if f.endswith('.log') and not f.startswith(tuple(self.TARGET_LOG_IGNORE)) ]

    # dict
    def get_tracking_shell_log_content(self):
        ts_log_path = os.path.join(self.dir_date, 'trackingshell.log')
        if not os.path.exists(ts_log_path): return None
        return self.get_target_log_dict(ts_log_path, return_content = True)

    # bool
    def is_target_log_succeed(self, content):
        tracking_shell_lines = re.findall(r'\[tracking_shell [^\]]+\] Working on target (\S+) attempt', content, re.I)
        if not tracking_shell_lines:
            return False

        target_file_name = os.path.join(
            self.dir_project,
            tracking_shell_lines[-1]
        )
        if not target_file_name:
            return False

        return os.path.exists(target_file_name)

    # dict
    def get_target_log_dict(self, file_path, return_content = False):
        _, file_name = os.path.split(file_path)
        name, _ = os.path.splitext(file_name)
        content = self.get_content(file_path)

        return {
            'id': self.get_log_id(name),
            'name': name,
            'size': os.path.getsize(file_path),
            'lines': len(content.split('\n')),
            'success': self.is_target_log_succeed(content),
            'content': content if return_content else None
        }

    # list<dict>
    def get_target_logs_dict(self):
        for file_path in self.find_target_log_files():
            yield self.get_target_log_dict(file_path)

    # list<dict>
    def get_sorted_target_logs_dict(self):
        logs_sorted_by_size = sorted(self.get_target_logs_dict(), \
            lambda x,y: cmp(x['size'], y['size']), reverse = True)

        return sorted(logs_sorted_by_size, \
            lambda x,y: cmp(x['success'], y['success']))

# str
def filesize(n,pow=0,b=1024,u='B',pre=['']+[p+'i'for p in'KMGTPEZY']):
    pow,n=min(int(log(max(n*b**pow,1),b)),len(pre)-1),n*b**pow
    return "%%.%if %%s%%s"%abs(pow%(-pow-1))%(n/b**float(pow),pre[pow],u)

class resolve(object):
    # void
    def __init__(self, logger_cls):
        self.logger_cls = logger_cls
        self.dir_project = os.environ.get('NIGHT_SHIFT_PROJECT_DIR')

    # func
    def __call__(self, f):
        outer_cls = self

        @wraps(f)
        def decorated_function(date = None, *args, **kwargs):
            logger = outer_cls.logger_cls(outer_cls.dir_project, date)
            data = f(logger, *args, **kwargs)
            if isinstance(data, dict):
                data.update({
                    'page': f.__name__,
                    'current_date': logger.date,
                    'dates': logger.find_available_log_dates()[-7:],
                    'filesize': filesize,
                })
                return render_template('{}.html'.format(f.__name__), **data)
            else:
                return data

        return decorated_function

@app.route('/download/<date>/<log_id>')
@resolve(TargetLogs)
def download(ns, log_id):
    return ns.get_content(ns.get_path_by_log_id(log_id))

@app.route("/")
@app.route("/flow")
@app.route("/flow/<date>")
@app.route('/flow/<date>/<log_id>')
@resolve(TargetLogs)
def flow(ns, log_id = None):
    return {
        'target_logs': ns.get_sorted_target_logs_dict(),
        'log_id': log_id,
        'ts': ns.get_tracking_shell_log_content()
    }

@app.route("/gantt")
@app.route("/gantt/<date>")
@resolve(TrackingShellLog)
def gantt(ns):
    commands, _ = ns.get_timing_env_commands_dict()
    return {'commands': commands}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true')
    args = parser.parse_args()

    app.run(host='0.0.0.0', port=8000, threaded=True, debug=args.debug)
