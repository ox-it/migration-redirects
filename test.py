import yaml
import urllib2

tests = yaml.load(open('tests.yml'))

class MyHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        print " ->", headers['Location']
        return urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
    http_error_301 = http_error_303 = http_error_307 = http_error_302


opener = urllib2.build_opener(MyHTTPRedirectHandler)

for test in tests:
    s, t = test['s'], test['t']

    print '-'*80

    print s
    try:
        response = opener.open(s)
    except urllib2.HTTPError as response:
        pass
    print response.code, response.url

    if response.url != t:
        print "Exp", t
