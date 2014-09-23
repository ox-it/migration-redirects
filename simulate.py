"""
Script for testing migration redirects.

Takes an .htaccess file as its first argument, and takes Apache logs on stdin.
Will apply the redirects, and make sure that each path in the logs ends up at a page.
"""

import csv
import enum
import json
import re
import sys
from urlparse import urljoin, urlparse, urlunparse

import requests

class Codes(enum.Enum):
    OK = 200
    FOUND = 302
    PERMANENT_R = 301
    BAD_REQUEST = 400
    FORBIDDEN = 403
    NOT_FOUND = 404
    GONE = 410

def parse_htaccess(htaccess):
    rewrites = []
    for line in htaccess:
        line = line.split('#')[0]
        if not line.startswith('RewriteRule '):
            continue
        line = line.split()
        target = line[2]
        for i in range(1, 10):
            target = target.replace('${0}'.format(i), '{{{0}}}'.format(i-1))
        rewrite = {'pattern': re.compile(line[1]),
                   'target': target}
        if len(line) > 3:
            opts = line[3][1:-1].split(',')
            for opt in opts:
                if opt == 'L':
                    rewrite['last'] = True
                elif opt == 'G':
                    rewrite['gone'] = True
        rewrites.append(rewrite)
    return rewrites

def apply_rewrites(rewrites, url):
    for rewrite in rewrites:
        match = rewrite['pattern'].search(url)
        if match:
            url = rewrite['target'].format(*match.groups())
            if rewrite.get('last'):
                break
            if rewrite.get('gone'):
                return Codes.GONE
    return url

def fix_domains(results, url):
    if isinstance(url, Codes):
         return url
    url = urlparse(url)
    if url.netloc in fix_domains.fixes:
        url = url._replace(netloc=fix_domains.fixes[url.netloc])
    if not url.netloc:
        # We didn't get redirected off-host, so there's nothing to be found
        return Codes.NOT_FOUND
    if url.netloc == 'ww1lit.nsms.ox.ac.uk':
        return Codes.OK
    url = urlunparse(url)
    if url in results['responses']:
        return Codes(results['responses'][url])
    if any(p.search(url) for p in fix_domains.known_good_patterns):
        return Codes.OK
    return url
fix_domains.fixes = {
    'help.it.ox.ac.uk': 'help-live.nsms.ox.ac.uk',
    'www.it.ox.ac.uk': 'dandy-live.nsms.ox.ac.uk',
}
fix_domains.known_good_patterns = map(re.compile, (
    r'^http://ww1lit\.nsms\.ox\.ac\.uk/',
    r'^http://courses\.it\.ox\.ac\.uk/detail/[A-Z\d]{4}$',
))

def get_paths(logfile):
    reader = csv.reader(logfile, delimiter=' ', doublequote=False, escapechar='\\')
    for i, row in enumerate(reader):
        if (i % 1000000) == 0:
            sys.stderr.write("Line {0}\n".format(i))
        if row[4] in ('404', '400'):
            continue
        req = row[3]
        try:
            method, path, proto = req.split(' ')
        except ValueError:
            continue
        path = path.split('#', 1)[0]
        path = path.split('?', 1)[0]
        if not path.startswith('/'):
            continue

        yield path[1:]

if __name__ == '__main__':
    import sys
    with open(sys.argv[1]) as htaccess:
        rewrites = parse_htaccess(htaccess)

    try:
        results = json.load(open('results'))
    except IOError:
        results = {
            'responses': {},
        }

    try:
        seen, request_count = set(), 0
        for path in get_paths(sys.stdin):
            if path in seen:
                continue
            seen.add(path)
            url = apply_rewrites(rewrites, path)
            status_or_target = fix_domains(results, url)
            if isinstance(status_or_target, basestring):
                try:
                    status = results['responses'][status_or_target]
                except KeyError:
                    try:
                        response = requests.head(status_or_target)
                    except Exception:
                        sys.stderr.write("Error HEADing {0}\n".format(status_or_target))
                        raise
                    status = results['responses'][status_or_target] = response.status_code
                    request_count += 1
                    if (request_count % 100) == 0:
                        sys.stderr.write("Request {0}\n".format(request_count))
                status = Codes(status)
            else:
                status = status_or_target
            print status.name.ljust(12), path.ljust(100), url
    except BaseException:
        with open('results', 'w') as f:
            json.dump(results, f, indent=2)
        raise

