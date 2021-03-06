#!/usr/bin/env python3

import os, sys, json, argparse, time
from urllib import request
from pathlib import Path
from datetime import datetime


class TestRunner():

    def __init__(self, args):

        self.args = args

        self.backends = [
            'https://backend.iobio.io',
            'https://mosaic.chpc.utah.edu/gru/api/v1',
            'https://mosaic.chpc.utah.edu/gru-dev',
        ]

    def run(self):

        # single specific test
        if self.args.path.endswith('.json'):

            if self.args.backend is not None:
                    self.handle_test(self.args.backend, self.args.path)
            else:
                for backend in self.backends:
                    self.handle_test(backend, self.args.path)
        else :

            while True:
                for (dirpath, dirnames, filenames) in os.walk(self.args.path):
                    for filename in filenames:
                        if Path(filename).suffix == '.json':
                            path = os.path.join(dirpath, filename)

                            for backend in self.backends:
                                self.handle_test(backend, path)
                time.sleep(3600)

    def handle_test(self, backend, path):
        with open(path) as f:
            config = json.load(f)

        endpoint = config['endpoint']
        url = f'{backend}{endpoint}'

        req = request.Request(url, headers={'Content-Type': 'text/plain'}, method='POST')

        data = json.dumps(config['data']).encode('utf-8')


        body = None

        success = True

        start_time = time.perf_counter()

        try:
            with request.urlopen(req, data=data) as res:
                body = res.read()

            for check in config['checks']:
                if check['type'] == 'contains':
                    if not check['value'].encode('utf-8') in body:
                        success = False
                elif check['type'] == 'endswith':
                    if not body.endswith(check['value'].encode('utf-8')):
                        success = False

        except request.HTTPError:
            success = False

        end_time = time.perf_counter()
        elapsed = end_time - start_time

        time_now = datetime.utcnow().replace(microsecond=0).isoformat()

        log = {
            'timestamp': time_now,
            'test': path,
            'result': 'SUCCESS' if success else 'FAILURE',
            'runtime': elapsed,
            'backend': backend,
        }

        if not success:
            print("\nFailed. Response body:\n", file=sys.stderr)
            print(body, file=sys.stderr)
            print("\ncurl repro command:\n", file=sys.stderr)
            print(build_curl(url, config['data']), file=sys.stderr)
            print("\n", file=sys.stderr)

        print(json.dumps(log), flush=True)


def build_curl(url, data):
    data_json = json.dumps(data)
    return f"curl -H 'Content-Type: text/plain' {url} --data-binary '{data_json}'"

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--path', default='.', help='Path to start searching for tests')
    parser.add_argument('--backend', help='Backend to use')
    args = parser.parse_args()

    runner = TestRunner(args)

    try:
        runner.run()
    except KeyboardInterrupt:
        print("Aborting", file=sys.stderr)
