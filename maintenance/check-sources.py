#!/usr/bin/env python3
"""Only moving VCS sources may skip SHA-256; local recipe inputs must be hashed."""
from pathlib import Path
import re
import sys


def check(text):
    fields = {}
    for line in text.splitlines():
        if ' = ' in line:
            key, value = line.strip().split(' = ', 1)
            fields.setdefault(key, []).append(value)
    source_keys = [key for key in fields if key == 'source' or key.startswith('source_')]
    if not source_keys:
        raise ValueError('No sources declared')
    for key in source_keys:
        sources = fields[key]
        hashes = fields.get('sha256sums' + key.removeprefix('source'), [])
        if len(sources) != len(hashes):
            raise ValueError('Every source must have a matching SHA-256 entry')
        for source, digest in zip(sources, hashes):
            origin = source.split('::', 1)[-1]
            if digest == 'SKIP':
                if fields.get('pkgbase') != ['fthr-clips-git'] or origin != 'git+https://github.com/FTHR-Community/FTHR-Clips.git#branch=linux':
                    raise ValueError('SKIP is permitted only for the linux-branch Git source')
            elif not re.fullmatch('[0-9a-f]{64}', digest):
                raise ValueError('Invalid SHA-256 digest')


if __name__ == '__main__':
    try:
        check(Path(sys.argv[1]).read_text())
    except (ValueError, OSError) as error:
        raise SystemExit(str(error))
