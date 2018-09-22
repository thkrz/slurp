#!/usr/bin/env python3
import nntplib
import os
import re
import time
import sys
import xml.etree.ElementTree as ET
import zlib

from fnmatch import fnmatchcase
from numba import jit, byte
from threading import Thread

flags = {'u': '', 'p': '', 'h': '', 'ssl': False, 'threads': 11, 'list': False}


def bytetostr(size) -> str:
    q = ['', 'K', 'M', 'G', 'T']
    i = 0
    while size > 1024:
        size /= 1024
        i += 1
    if size < 10:
        return '{:3.1f}{}'.format(size, q[i])
    return '{:3.0f}{}'.format(size, q[i])


def die(s) -> None:
    log(s)
    sys.exit(1)


def fetch(segment, groups) -> None:
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
    for group in groups:
        try:
            s.group(group)
            s.body('<{}>'.format(segment['name']), file=segment['name'])
        except nntplib.NNTPTemporaryError:
            continue
        break
    s.quit()


def loadnzb(s) -> list:
    ns = '{http://www.newzbin.com/DTD/2003/nzb}'
    pat = re.compile(r'"(.*)"')
    nzb = []
    tree = ET.parse(s)
    root = tree.getroot()
    for e in root.iter(ns + 'file'):
        name = pat.search(e.attrib['subject']).group(1)
        date = time.localtime(int(e.attrib['date']))
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
            'date': date,
            'groups': groups,
            'segments': sorted(segments, key=lambda x: x['number']),
            'bytes': total
        })
    return sorted(nzb, key=lambda x: x['name'])


def log(s, end='\n') -> None:
    sys.stderr.write(s + end)
    sys.stderr.flush()


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
    log('usage: slurp [-ssl] [-threads n] [-u user [-p password]] -h host nzb [file...]'
        )
    sys.exit(1)


def ydec(name) -> None:
    @jit(byte[:](byte[:]))
    def decode(buf):
        data = bytearray()
        esc = False
        for c in buf:
            if c == 13 or c == 10:
                continue
            if c == 61 and not esc:
                esc = True
                continue
            else:
                if esc:
                    esc = False
                    c -= 64
                if 0 <= c <= 41:
                    dec = c + 214
                else:
                    dec = c - 42
            data.append(dec)
        return data

    def keywords(line) -> dict:
        words = line.decode('utf-8').split('=')
        key = words[1].split()[1]
        d = {}
        for s in words[2:-1]:
            pair = s.split()
            d[key] = pair[0]
            key = pair[1]
        d[key] = words[-1].strip()
        return d

    i = 0
    with open(name, 'rb') as f:
        lines = list(f)
    if len(lines) == 0:
        return
    while not lines[i].startswith(b'=ybegin '):
        i += 1
    header = keywords(lines[i])
    i += 1
    multipart = 'part' in header.keys()
    if multipart:
        i += 1
    j = i
    while not lines[j].startswith(b'=yend '):
        j += 1
    trailer = keywords(lines[j])
    data = decode(b''.join(lines[i:j]))
    key = 'pcrc32' if multipart else 'crc32'
    if key in trailer.keys():
        crc1 = zlib.crc32(data) & 0xffffffff
        crc2 = int(trailer[key], 16)
        if not crc1 == crc2:
            return
        # not reached
    mode = 'ab' if multipart and int(header['part']) != 1 else 'wb'
    with open(header['name'], mode) as f:
        f.write(data)


def main() -> int:
    files = loadnzb(sys.argv[0])
    if len(sys.argv) > 1:
        files = list(
            filter(
                lambda x: any([fnmatchcase(x['name'], arg) for arg in sys.argv[1:]]),
                files))

    if flags['list']:
        total = 0
        ts = time.time()
        for f in files:
            size = f['bytes']
            total += size
            fmt = '%b %e %H:%M' if ts - time.mktime(
                f['date']) < 1.577e7 else '%b %e %Y'
            date = time.strftime(fmt, f['date'])
            print('{} {:>12} {}'.format(bytetostr(size), date, f['name']))
        if len(files) > 1:
            print('total ' + bytetostr(total))
        return 0
        # not reached

    num_threads = flags['threads']
    for f in files:
        j = 0
        n = len(f['segments'])
        while n > 0:
            threads = []
            for i in range(min(n, num_threads)):
                threads.append(
                    Thread(target=fetch, args=(f['segments'][j], f['groups'])))
                j += 1
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            n -= num_threads
        n = len(f['segments'])
        for i, segment in enumerate(f['segments']):
            ydec(segment['name'])
            os.remove(segment['name'])
    return 0


if __name__ == '__main__':
    if parse() or len(sys.argv) == 0:
        usage()
    sys.exit(main())
