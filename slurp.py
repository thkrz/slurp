#!/usr/bin/env python3
import flag
import nntplib
import re
import sys
import xml.etree.ElementTree as ET
import yenc

flags = {'u': '', 'p': '', 'h': '', 'ssl': False, 'threads': 11}


def die(s) -> None:
    log(s)
    sys.exit(1)


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
    log('usage: slurp [-threads n] [-ssl] [-u user [-p password]] -h host nzb [pattern]'
        )
    sys.exit(1)


def main() -> int:
    files = loadnzb(sys.argv[0])
    host = flags['h']
    if not host:
        usage()
    if flags['ssl']:
        s = nntplib.NNTP_SSL(host)
    else:
        s = nntplib.NNTP(host)
    s.login(flags['u'], flags['p'])
    for f in files:
        s.group(f['groups'][0])
        fnames = []
        for part in f['segments']:
            resp, info = s.body('<{}>'.format(part['name']))
            with open(part['name'], 'w') as f:
                f.write(resp)
            fnames.append(part['name'])
        yenc.decode(fnames)
    s.quit()
    return 0


if __name__ == '__main__':
    if parse() or len(sys.argv) < 2:
        usage()
    sys.exit(main())
