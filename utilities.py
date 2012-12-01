from datetime import datetime
from glob import glob as raw_glob
import os
import math
import random
import string
import sys
import copy

def mean(xs):
    l = list(xs)
    return sum(l) / len(l) if l else 0

def equivalent(s1, s2):
    if s1 is None or s2 is None:
        return s1 is None and s2 is None
    return ''.join(s1.split()) == ''.join(s2.split())

def hourse_elapsed(datetime, hour):
    return ((datetime.hour + datetime.minute / 60.) - hour) % 24

def deviation(xs):
    l = list(xs)
    m = mean(l)
    return math.sqrt(mean((x - m)**2.0 for x in l))

def wrap(text, width):
    """
    A word-wrap function that preserves existing line breaks
    and most spaces in the text. Expects that existing line
    breaks are posix newlines (\n).
    """
    return reduce(lambda line, word, width=width: '%s%s%s' %
                  (line,
                   ' \n'[(len(line)-line.rfind('\n')-1
                         + len(word.split('\n',1)[0]
                              ) >= width)],
                   word),
                  text.split(' ')
                 )


def pretty_print(s):
    print(wrap(s, 80))

def glob(pattern):
    pattern = process_path(pattern)
    return raw_glob(pattern)

def process_path(path):
    if getattr(sys, 'frozen', None):
         basedir = os.path.abspath(sys._MEIPASS)
    else:
         basedir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(basedir, path)

def open_processed(path, mode):
    if not os.path.isabs(path):
        path = process_path(path)
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    return open(path, mode)

def render_time(t):
    if t < 60:
        return "{0:.1f} seconds".format(t)
    seconds = int(t)
    if seconds < 3600:
        return "{0}:{1:>02d}".format(seconds/60, seconds%60)
    else:
        return "{0}:{1:>02d}:{2:>02d}".format(seconds/3600, (seconds%3600)/60, seconds%60)

def random_id():
    return ''.join(random.choice(
        string.ascii_uppercase + string.ascii_lowercase + string.digits
    ) for i in range(10))

def make_hash(o):
    if isinstance(o, set) or isinstance(o, tuple) or isinstance(o, list):
        return hash(tuple([make_hash(e) for e in o]))
    elif not isinstance(o, dict):
        return hash(o)
    new_o = copy.deepcopy(o)
    for k, v in new_o.items():
        new_o[k] = make_hash(v)

    return hash(tuple(frozenset(new_o.items())))
