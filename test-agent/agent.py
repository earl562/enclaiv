import urllib.request
try:
    r = urllib.request.urlopen("http://arxiv.org", timeout=5)
    print("arxiv.org: ALLOWED")
except Exception as e:
    print("arxiv.org: " + str(e))

try:
    r = urllib.request.urlopen("http://evil.com", timeout=5)
    print("evil.com: ALLOWED")
except Exception as e:
    print("evil.com: BLOCKED")
