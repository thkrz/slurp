#!/usr/bin/env python3
import nntplib
import re
import sys
import xml.etree.ElementTree as ET

from fnmatch import fnmatchcase
from threading import Thread

flags = {'u': '', 'p': '', 'h': '', 'ssl': False, 'threads': 11}


def die(s) -> None:
    log(s)
    sys.exit(1)


def fetch(segment, group):
    host = flags['h']
    port = None
    if ':' in host:
        host, port = tuple(host.split(':', 1))
        port = int(port)
    if flags['ssl']:
        if not port:
            port = 563
        s = nntplib.NNTP_SSL(host, port)
    else:
        if not port:
            port = 119
        s = nntplib.NNTP(host, port)
    s.login(flags['u'], flags['p'])
    s.group(group)
    resp, info = s.body('<{}>'.format(segment['name']))
    with open(segment['name'], 'w') as f:
        f.write(resp)
    s.quit()


def loadnzb(s) -> list:
    ns = '{http://www.newzbin.com/DTD/2003/nzb}'
    pat = re.compile(r'"(.*)"')
    nzb = []
    tree = ET.parse(s)
    root = tree.getroot()
    for e in root.iter(ns + 'file'):
        name = pat.search(e.attrib['subject']).group(1)
        groups = []
        for g in e.iter(ns + 'group'):
            groups.append(g.text)
        segments = []
        total = 0
        for s in e.iter(ns + 'segment'):
            size = int(s.attrib['bytes'])
            total += size
            number = int(s.attrib['number'])
            sname = s.text
            segments.append({'bytes': size, 'number': number, 'name': sname})
        nzb.append({
            'name': name,
            'groups': groups,
            'segments': segments.sort(key=lambda x: x['number']),
            'bytes': total
        })
    return nzb


def log(s) -> None:
    sys.stderr.write(s + '\n')


def parse() -> bool:
    sys.argv.pop(0)
    argv = iter(sys.argv)
    p = []
    for a in argv:
        if a.startswith('-'):
            v = None
            if '=' in a:
                k, v = tuple(a.split('=', 1))
            else:
                k = a
            k = k[1:]
            if k not in flags.keys():
                return True
            cast = type(flags[k])
            if cast == bool:
                flags[k] = True
            else:
                if v is None:
                    v = next(argv)
                    p.append(v)
                flags[k] = cast(v)
            p.append(a)
    for e in p:
        sys.argv.remove(e)
    return False


def usage() -> int:
    log('usage: slurp [-ssl] [-threads n] [-u user [-p password]] -h host nzb [pattern]'
        )
    sys.exit(1)


def ydec(name):
    pass


def main() -> int:
    files = loadnzb(sys.argv[0])
    for f in files:
        if len(sys.argv) > 1 and not fnmatchcase(f['name'], sys.argv[1]):
            continue
        n = len(f['segments'])
        j = 0
        while n > 0:
            threads = []
            for i in range(min(n, flags['threads'])):
                threads.append(
                    Thread(
                        target=fetch, args=(f['segments'][j], f['groups'][0])))
                j += 1
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            n -= j
        for segment in f['segments']:
            ydec(segment)

    return 0


if __name__ == '__main__':
    if parse() or len(sys.argv) == 0 or len(sys.argv) > 2 or not flags['h']:
        usage()
    sys.exit(main())
