# Dowloads content from download.txt preserving directory structure
import urllib
import urllib.parse
import urllib.request
import os
from pathlib import Path


links = []
with open('download.txt', 'r') as f:
    links = [urllib.parse.urlparse(link) for link in f.readlines()]

for link in links:
    url = link.geturl()
    with urllib.request.urlopen(url) as response:
        print('got ' + url)

        path = Path(link.path[1:]) # remove root slash
        dirname = path.parent
        os.makedirs(dirname, exist_ok=True)
        with open(path, 'wb') as f:
            print(url + ' -> ' + str(path))
            f.write(response.read())

