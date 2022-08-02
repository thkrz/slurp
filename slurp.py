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
from queue import Queue
from threading import Thread

flags = {"u": "", "p": "", "h": "", "ssl": False, "threads": 10, "list": False}
watchdog = Queue()


def bytetostr(size):
    q = ["", "K", "M", "G", "T"]
    i = 0
    while size > 1024:
        size /= 1024
        i += 1
    if size < 10:
        return "{:3.1f}{}".format(size, q[i])
    return "{:3.0f}{}".format(size, q[i])


def clean():
    while not watchdog.empty():
        try:
            os.remove(watchdog.get())
        except OSError:
            pass


def die(s):
    log(s)
    sys.exit(1)


def fetch(segment, groups):
    conn = nntplib.NNTP_SSL if flags["ssl"] else nntplib.NNTP
    port = 563 if flags["ssl"] else 119
    host = flags["h"]
    if ":" in host:
        host, port = host.split(":", 1)
        port = int(port)
    try:
        s = conn(host, port)
        s.login(flags["u"], flags["p"])
        for group in groups:
            try:
                s.group(group)
                watchdog.put(segment)
                s.body("<{}>".format(segment), file=segment)
            except nntplib.NNTPTemporaryError:
                continue
            break
        s.quit()
    except nntplib.NNTPPermanentError as e:
        log("slurp: nntp: " + str(e))


def loadnzb(s):
    ns = "{http://www.newzbin.com/DTD/2003/nzb}"
    pat = re.compile(r'"(.*)"')
    nzb = []
    tree = ET.parse(s)
    root = tree.getroot()
    for e in root.iter(ns + "file"):
        name = pat.search(e.attrib["subject"]).group(1)
        date = time.localtime(int(e.attrib["date"]))
        groups = []
        for g in e.iter(ns + "group"):
            groups.append(g.text)
        segments = []
        total = 0
        for s in e.iter(ns + "segment"):
            size = int(s.attrib["bytes"])
            total += size
            number = int(s.attrib["number"])
            sname = s.text
            segments.append({"bytes": size, "number": number, "name": sname})
        nzb.append(
            {
                "name": name,
                "date": date,
                "groups": groups,
                "segments": sorted(segments, key=lambda x: x["number"]),
                "bytes": total,
            }
        )
    return sorted(nzb, key=lambda x: x["name"])


def log(s, end="\n"):
    sys.stderr.write(s + end)
    sys.stderr.flush()


def parse():
    sys.argv.pop(0)
    argv = iter(sys.argv)
    p = []
    for a in argv:
        if a.startswith("-"):
            v = None
            if "=" in a:
                k, v = a.split("=", 1)
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


def usage():
    die(
        "usage: slurp [-ssl] [-threads n] [-u user [-p password]] -h host[:port] nzb [file...]"
    )


def ydec(name):
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

    def keywords(line):
        words = line.decode("utf-8").split("=")
        k = words[1].split()[1]
        d = {}
        for s in words[2:-1]:
            pair = s.split()
            d[k] = pair[0]
            k = pair[1]
        d[k] = words[-1].strip()
        return d

    i = 0
    with open(name, "rb") as f:
        lines = list(f)
    if len(lines) == 0:
        return
    while not lines[i].startswith(b"=ybegin "):
        i += 1
    header = keywords(lines[i])
    i += 1
    multipart = "part" in header.keys()
    if multipart:
        i += 1
    j = i
    while not lines[j].startswith(b"=yend "):
        j += 1
    trailer = keywords(lines[j])
    data = decode(b"".join(lines[i:j]))
    key = "pcrc32" if multipart else "crc32"
    if key in trailer.keys():
        crc1 = zlib.crc32(data) & 0xFFFFFFFF
        crc2 = int(trailer[key], 16)
        if not crc1 == crc2:
            return
        # not reached
    mode = "ab" if multipart and int(header["part"]) != 1 else "wb"
    with open(header["name"], mode) as f:
        f.write(data)


def main():
    files = loadnzb(sys.argv[0])
    if len(sys.argv) > 1:
        files = list(
            filter(
                lambda x: any([fnmatchcase(x["name"], arg) for arg in sys.argv[1:]]),
                files,
            )
        )

    if flags["list"]:
        total = 0
        ts = time.time()
        for f in files:
            size = f["bytes"]
            total += size
            fmt = "%b %e %H:%M" if ts - time.mktime(f["date"]) < 1.577e7 else "%b %e %Y"
            date = time.strftime(fmt, f["date"])
            print("{} {:>12} {}".format(bytetostr(size), date, f["name"]))
        if len(files) > 1:
            print("total " + bytetostr(total))
        return 0
        # not reached

    num_threads = flags["threads"]
    for f in files:
        j = 0
        n = len(f["segments"])
        total = f["bytes"]
        pend = 0
        while n > 0:
            threads = []
            for i in range(min(n, num_threads)):
                t = Thread(target=fetch, args=(f["segments"][j]["name"], f["groups"]))
                t.start()
                threads.append(t)
                j += 1
                pend += f["segments"][j]["bytes"]
            for t in threads:
                t.join()
            log(f"\r{f['name']}: {100.0*pend/total:3.0f} %", end="")
            n -= num_threads
        if watchdog.empty():
            return 1
        for segment in f["segments"]:
            ydec(segment["name"])
        clean()
    return 0


if __name__ == "__main__":
    if parse() or len(sys.argv) == 0:
        usage()
    try:
        rv = main()
    except KeyboardInterrupt:
        clean()
        rv = 32
    sys.exit(rv)
