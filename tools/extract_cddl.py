#!/usr/bin/python

import argparse
import re
import subprocess
import sys
import tempfile

def augmented_open(fname, mode="r"):
    if fname == '-':
        if 'w' in mode:
            return sys.stdout
        else:
            return sys.stdin
    return open(fname, mode)

def warn(s):
    sys.stderr.write(s)

def extract_cddl_lines(f):
    """
    I'm going to have cddl blocks begin with an indented line starting with
    a semicolon, and end with a less-indented line.
    """
    in_cddl = True

    for line in f:
        if in_cddl:
            if line and not line[:4].isspace():
                in_cddl = False
            else:
                yield line
        else:
            if line[:4].isspace() and line.strip().startswith(";"):
                in_cddl = True
                yield line

def strip_directives_for_ruby_cddl(s):
    """
    Remove directives that the ruby cddl implementation doesn't understand.
    """
    s = s.replace("bstr .cbor ", "").replace("encoded-cbor .cbor ", "")
    return re.sub(r'.within \w+', '', s)

def main(argv):
    progname = argv[0]
    parser = argparse.ArgumentParser(prog=progname)
    parser.add_argument("--check", action="store_true",
                        help="use a cddl implementation to check the scripts")
    parser.add_argument("--toplevel",
                        help="treat given symbol as top-level CDDL production")
    parser.add_argument("--output", default="-",
                        help="where to write [- for stdout]")
    parser.add_argument("input", default=["-"], nargs="*",
                        help="files to read from [- for stdin]")

    args = parser.parse_args(argv[1:])

    if args.output != '-' and args.check:
        warn("Can't use --check and --output together.")
        sys.exit(1)

    if args.check:
        outf = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8')
        filt = strip_directives_for_ruby_cddl
    else:
        outf = augmented_open(args.output, 'w')
        filt = lambda x: x

    if args.toplevel:
        print("TOPLEVEL_ = %s\n"%args.toplevel, file=outf)

    try:
        for fname in args.input:
            with augmented_open(fname) as inf:
                for line in extract_cddl_lines(inf):
                    outf.write(filt(line))
    finally:
        outf.close()

    if args.check:
        subprocess.run(["cddl", outf.name, "generate"])

if __name__ == '__main__':
    main(sys.argv)

