#!/usr/bin/python

import sys

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



if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] != '-':
        stream = open(sys.argv[1], 'r')
    else:
        print("reading from stdin...", file=sys.stderr)
        stream = sys.stdin

    for line in extract_cddl_lines(stream):
        sys.stdout.write(line)

    
