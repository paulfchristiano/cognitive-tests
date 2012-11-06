import pdb
import sys
from session import *
from questions import *
from utilities import pretty_print
import data

def need_db_sync():
    try:
        with open('data/sync_history', 'r') as f:
            return any(time() - float(line) > 36000 for line in f)
    except Exception as e:
        return True

def db_sync():
        print("Syncing with database...")
        db_sessions = data.load_sessions_from_db()
        print("...loaded sessions from database...")
        file_sessions = data.load_sessions_from_file()
        data.write_sessions_to_db(file_sessions)
        print("...wrote sessions to database.")
        for session in db_sessions:
            session.save()
        with open('data/sync_history', 'w') as f:
            f.write("{}\n".format(time()))

def display_intro():
    paragraphs = []
    paragraph = ""
    last_line = None
    try:
        with open('intro', 'r') as f:
            for line in f:
                if line == '\n' and last_line == '\n':
                    pretty_print(paragraph)
                    raw_input()
                    paragraph = ""
                else:
                    paragraph = paragraph + line
                last_line = line
            pretty_print(paragraph)
            raw_input("")
    except IOError:
        pretty_print("You should have gotten an intro just then, but something went wrong!"\
        " Sorry about that. Anyway, it's not that hard; you'll catch on.\n")

def is_first_time():
    try:
        open('users', 'r')
        return False
    except:
        return True

if __name__ == "__main__" and 'noop' not in sys.argv:
    if is_first_time():
        display_intro()
    if need_db_sync():
        db_sync()

    survey_questions = [
        "When did you last eat?",
        "When did you wake up?",
        "How long did you sleep?",
        "What is the background noise?",
        "If you're listening to music, what?",
        "What drug have you taken recently, if any?",
        "If so, at what dose?",
        "If so, when did you take it?",
        "Where are you sitting?",
        "Any other notes?"
    ]

    def sync_in_session(session):
        db_sync()
        session.refresh()
    def toggle_user_online(session):
        session.user.from_online = not session.user.from_online

    session_options = [
        {'text':'Use questions from online? Currently: {}', 
         'display':lambda session: session.user.from_online,
         'value':toggle_user_online},
        {'text':'Sync with database now.',
         'value':sync_in_session},
        {'text':'Change user. Currently: {}',
         'display':lambda session: session.user.name,
         'value':lambda session: session.set_user(User.pick_user())}
    ]

    question_generators = [
        QuestionGenerator(MultiplicationQuestion, 'Arithmetic'),
        QuestionGenerator(AnagramQuestion, 'Anagrams'),
        QuestionGenerator(AnalogyQuestion, 'Analogies'),
        QuestionGenerator(ExpressionQuestion, 'Make N'),
        QuestionGenerator(Medley, 'Medley', 'Medley is a balanced mix of the other problems'),
        QuestionGenerator( 
            Survey, 'Take the survey.', 
            "The survey is a set of questions evaluating your current state, "\
            "to help determine what conditions lead to improved or impaired performance",
            args = {'questions': survey_questions}
        ), QuestionGenerator(
            OptionMenu, 'Options',
            args = {'options': session_options}
        )
    ]

    session = Session(question_generators)
    session.start()
