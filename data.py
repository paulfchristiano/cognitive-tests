import cPickle
from session import *
from questions import *
from collections import Counter
import re
import utilities
from utilities import open_processed as open
from datetime import datetime
from collections import defaultdict
import pymysql

DEFAULT_FILES="data/Session-*"

def load_sessions_from_db(cursor=None, load_all=False):
    if cursor is None:
        cursor = get_cursor()
    sessions = set()
    corruptions = set()
    if load_all:
        cursor.execute("SELECT id, pickled from sessions")
    else:
        cursor.execute("SELECT id, pickled from sessions where corrupt=FALSE")
    for (session_id, pickled) in cursor.fetchall():
        try:
            sessions.add(cPickle.loads(pickled))
        except:
            corruptions.add(session_id)
    if corruptions:
        print("Warning! Failed to pickle {} sessions from the database.".format(
            len(corruptions)
        ))
        for session_id in corruptions:
            cursor.execute("UPDATE sessions set corrupt=TRUE where id={}".format(
                pymysql.escape_string(session_id)
            ))
    return sessions

def pickled_sessions_from_db():
    cursor = get_cursor()
    cursor.execute('SELECT id, pickled from sessions')
    return list(cursor.fetchall())

def load_sessions_from_file(files=DEFAULT_FILES):
    sessions = set()
    corruptions = set()
    try:
        with open('data/corruptions', 'r') as f:
            for line in f:
                corruptions.add(line[:-1])
    except:
        pass
    for record in utilities.glob(files):
        if record not in corruptions:
            with open(record, 'r') as f:
                try:
                    sessions.add(cPickle.load(f))
                except:
                    corruptions.add(record)
    if corruptions:
        print("Warning! Failed to pickle {} sessions stored locally.".format(
            len(corruptions)
        ))
    with open('data/corruptions', 'w') as f:
        for s in corruptions:
            f.write("{}\n".format(s))
    return sessions

def get_cursor():
    HOST = '198.101.212.47'
    DB = 'psychometrics'
    USER = 'participant'
    PASSWD = 'obscure8999city'
    cursor = pymysql.connect(host=HOST, db=DB, user=USER, passwd=PASSWD, connect_timeout=5).cursor()
    cursor.execute('set autocommit = 1')
    return cursor

def write_data_to_db(data_dict, cursor=None, table='sessions'):
    if cursor is None:
        cursor = get_cursor()
    data_list = data_dict.items()
    fs = [item[0] for item in data_list]
    vs = [pymysql.escape_string(str(item[1])) for item in data_list]
    cursor.execute(
        'INSERT INTO {table} ({fields}) values ({values})'\
        'ON DUPLICATE KEY UPDATE {update}'.format(
            table=table, fields=','.join(fs), values=','.join(vs), 
            update=','.join('{}={}'.format(f, v) for f, v in zip(fs, vs))
        )
    )

def file_sessions(files=DEFAULT_FILES):
    regexp = re.compile(files.replace('*', '(.*)'))
    return set([regexp.match(s).group(1) for s in utilities.glob(files)])

def db_sessions(cursor=None):
    if cursor is None:
        cursor = get_cursor()
    cursor.execute('SELECT id from sessions')
    return {x[0] for x in cursor.fetchall()}

def write_sessions_to_db(sessions, force=False):
    c = get_cursor()
    known_sessions = db_sessions(c)
    [ 
        write_data_to_db({
            'id':session.id,
            'pickled':cPickle.dumps(session),
            'username':session.user.name,
            'corrupt':0
        }, table='sessions', cursor=c) 
        for session in sessions if force or session.id not in known_sessions 
    ]

def questions(session):
    return {interaction.question 
            for interaction in session.interactions 
            if interaction.question}

def open_questions(sessions, user=None):
    result = Counter()
    user_qs = reduce(set.union, 
                     (questions(session) 
                      for session in sessions
                      if user and session.user and session.user.name == user.name),
                     set())
    for session in sessions:
        result.update(question for question in questions(session) - user_qs )
    return result

def by_type(questions):
    result = defaultdict(lambda : Counter())
    for question, occurences in questions.items():
        result[question.name()][question] += occurences
    return result
