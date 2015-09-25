import io
import os
import sys
import glob
import re
import argparse

class Parser(object):
    EXTENSIONS = ['sh', 'py', 'erb', 'rb', 'mk', 'sql']

    def __init__(self, directory, start_files_path):
        self.directory = os.path.abspath(directory)
        self.need_to_check_files_path = set(start_files_path)
        self.used_files_path = set()
        self.all_files_path = set(self.collect_files())
        self.not_found_mentions = set()

    @property
    def unused_files_path(self):
        return self.all_files_path - self.used_files_path

    def read(self):
        while len(self.need_to_check_files_path) != 0:
            f = self.need_to_check_files_path.pop()
            self.used_files_path.add(f)
            collected_files_path = set()

            with io.open(f, 'r', encoding='utf-8') as fd:
                _, ext = os.path.splitext(f)
                content = fd.read() \
                    .replace('$*', '*')

                if ext == '.sh':
                    content = content.replace('$(pwd)/$(dirname $0)', os.path.dirname(f)) \
                        .replace('$(dirname $0)', os.path.dirname(f)) \
                        .replace('$(pwd)', os.path.dirname(f))
                    content = re.sub(ur'\$\((.*?)\)', '*', content)
                    content = re.sub(ur'\$\{(.*?)\}', '*', content)
                    content = re.sub(ur'\$([^ \/\-]*?)', '*', content)

                if ext == '.rb':
                    for mention in re.findall(ur'require_relative "(.*?)"', content, re.I):
                        file_name = '{}.rb'.format(mention) if not mention.endswith('.rb') else mention
                        file_path = os.path.abspath(os.path.join(os.path.dirname(f), file_name))
                        if os.path.exists(file_path):
                            self.need_to_check_files_path.add(file_path)

                if ext == '.py':
                    for imports in re.findall(ur'import (.*?)\n', content, re.I):
                        for mention in imports.split(','):
                            file_path = os.path.abspath(os.path.join(os.path.dirname(f), '{}.py'.format(mention.strip())))
                            if os.path.exists(file_path):
                                self.need_to_check_files_path.add(file_path)

                    for level, mention in re.findall(ur'from ([\.]*)(.*?) import', content, re.I):
                        rel_file_path = '../'*(len(level)-1) + '{}.py'.format(mention.strip())
                        file_path = os.path.abspath(os.path.join(os.path.dirname(f), rel_file_path))
                        if os.path.exists(file_path):
                            self.need_to_check_files_path.add(file_path)

                for mention, ext in set(re.findall(ur'([a-z0-9\_\*\-\.\\\/]+\.({}))'.format('|'.join(self.EXTENSIONS)), content, re.I)):
                    possible_files_path = glob.glob(os.path.abspath(mention))
                    if possible_files_path:
                        map(collected_files_path.add, possible_files_path)
                        continue

                    possible_files_path = glob.glob(os.path.abspath(os.path.join(os.path.dirname(f), mention)))
                    if possible_files_path:
                        map(collected_files_path.add, possible_files_path)
                        continue

                    possible_files_path = glob.glob(os.path.abspath(os.path.join(self.directory, mention)))
                    if possible_files_path:
                        map(collected_files_path.add, possible_files_path)
                        continue

                    self.not_found_mentions.add((f, mention))

            for file_path in collected_files_path:
                if file_path.startswith(self.directory) and file_path not in self.used_files_path:
                    self.need_to_check_files_path.add(file_path)

        return self

    def collect_files(self):
        for root, dirs, files in os.walk(self.directory):
            for f in files:
                if f.endswith(tuple(self.EXTENSIONS)):
                    yield os.path.join(root, f)

    def show_recognizable_files(self):
        if not self.not_found_mentions:
            print 'Every file was recognizable!'
            return
        print
        print 'Not recognizable files ({}):'.format(len(self.not_found_mentions))
        print '\n'.join(sorted('  {} <- {}'.format(m,f) for f, m in self.not_found_mentions))

    def show_unused_files(self):
        if not self.unused_files_path:
            print 'No unused files found!'
            return
        print
        print 'Unused files list ({}):'.format(len(self.unused_files_path))
        print '\n'.join(sorted('  {}'.format(f) for f in self.unused_files_path))

    def show_used_files(self):
        if not self.used_files_path:
            print 'No used files found!'
            return
        print
        print 'Used files list ({}):'.format(len(self.used_files_path))
        print '\n'.join(sorted('  {}'.format(f) for f in self.used_files_path))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('files_pattern', nargs='+', help='entry point of files')
    parser.add_argument('-d', '--dir', help='directory to check', required = True)
    args = parser.parse_args()

    files_path = map(os.path.abspath, sum(map(glob.glob, sum(map(str.split, args.files_pattern), [])), []))
    p = Parser(args.dir, files_path).read()
    p.show_unused_files()
    sys.exit(min(len(p.unused_files_path),1))