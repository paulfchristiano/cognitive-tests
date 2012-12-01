from datetime import datetime
from time import time
from collections import defaultdict, OrderedDict
from os import path,makedirs
from questions import *
import utilities
from utilities import open_processed as open
import random
import sys
import cPickle
import string
import data

class Session:
    def start(self):
        try:
            self.intro()
            while True:
                question_options = [ {'value':qg, 
                                      'text':qg.description, 
                                      'clarification':qg.clarification} 
                                     for qg in self.question_generators]
                interaction = Pick(question_options).ask()
                if interaction.status == Interaction.quit:
                    return
                elif interaction.answer():
                    self.interactions.append(interaction)
                    self.pose_question(interaction.answer())
        finally:
            self.end_session()

    def intro(self):
        print("\nWelcome, {}!".format(self.user.name))
        pretty_print("Type 'help' for help, 'exit' to quit, or 'pass' to give up on a problem.")

    def pose_question(self, question_generator):
        while True:
            interaction = question_generator.make_instance_for_session(self).ask()
            if interaction.status == Interaction.quit:
                return
            else:
                self.interactions.append(interaction)
                if not question_generator.repeat:
                    return

    def end_session(self): 
        self.end_time = time()
        self.user.last_survey_responses = self.survey_responses.copy()
        self.user.lact_activity = datetime.now()
        self.user.save()
        self.save()
        print("Your session lasted for {}".format(utilities.render_time(self.duration())))
        return self

    def duration(self):
        return self.end_time - self.start_time if self.end_time else time() - self.start_time

    def save(self):
        with open(self.filename(), 'w') as f:
            cPickle.dump(self, f)

    def set_user(self, user):
        self.user = user
        User.set_default(user)
        self.open_questions = data.by_type(
            data.open_questions(data.load_sessions_from_file(),self.user)
        )

    def filename(self):
        return "data/Session-{}".format(self.id)

    def refresh(self):
        self.set_user(self.user)

    def defined(self, p):
        for rule in interpretation_rules[p]:
            if utilities.equivalent(
                    self.survey_responses[rule['question']], 
                    rule['answer']):
                return True
        return False

    def get(self, p):
        for rule in interpretation_rules[p]:
            if utilities.equivalent(
                    self.survey_responses[rule['question']], 
                    rule['answer']):
                return rule['result']
        return None

    def __getstate__(self):
        picklable = self.__dict__.copy()
        if 'open_questions' in picklable:
            del picklable['open_questions']
        if 'survey_responses' in picklable:
            picklable['survey_responses'] = dict(picklable['survey_responses'])
        return picklable

    def __setstate__(self, state):
        assert('interactions' in state)
        survey_responses = state.get('survey_responses', dict())
        state['survey_responses'] = defaultdict(lambda : None, survey_responses)
        self.__dict__ = state

    def __init__(self, question_generators, user=None):
        self.start_time = time()
        self.date = datetime.now()
        self.interactions = []
        self.id = utilities.random_id()
        self.question_generators = question_generators
        self.end_time = float("inf")
        self.set_user(user if user is not None else User.default())
        self.survey_responses = self.user.last_survey_responses.copy()

users = None

class User:
    make_new = "new"

    def __init__(self):
        self.name = prompt("What username do you want to use?")
        self.from_online = True
        self.last_activity = datetime.now()
        self.last_survey_responses = {}
        self.save()

    def __str__(self):
        return "User<{}>".format(self.name)

    @classmethod
    def load_users(c):
        global users
        if not users:
            try:
                with open('users', 'r') as f:
                    users = cPickle.load(f)
            except:
                users = {}
        return users

    @classmethod
    def save_users(c, users):
        try:
            with open('users', 'w') as f:
                cPickle.dump(users, f)
        except:
            pass

    @classmethod
    def set_default(c, user):
        users = c.load_users()
        users['default'] = user
        c.save_users(users)

    def save(self):
        users = self.load_users()
        for key in users:
            if users[key].name == self.name:
                users[key] = self
        users[self.name] = self
        self.save_users(users)
        return self

    def __setstate__(self, state):
        if 'last_survey_responses' not in state:
            state['last_survey_responses'] = {}
        self.__dict__ = state

    @classmethod
    def default(c, users=None):
        if users is None:
            users = c.load_users()
        if 'default' not in users:
            users['default'] = c.pick_user(users)
        c.save_users(users)
        return users['default']

    @classmethod
    def pick_user(c, users=None):
        if users is None:
            users = c.load_users()
        if not users:
            return c()
        else:
            user = None
            distinct_users = set(users.values())
            while not user:
                user = Pick([{'text':user.name, 'value':user} for user in distinct_users] +
                            [{'text':'New user', 'value':User.make_new}]).ask().answer()
            if user == User.make_new:
                return User()
            else:
                return user

interpretation_rules = defaultdict(list)

def load_interpretation_rules():
    with open('interpretation_rules', 'r') as f:
        for line in f:
            (p, question, answer, result) = line.split()
            interpretation_rules[p].append({'question':question, 'answer':answer, 'result':result})

def add_interpretation_rule(p, question, answer, result):
    interpretation_rules[p].append({'question':question, 'answer':answer, 'result':result})

def save_interpretation_rules():
    with open('interpretation_rules', 'w') as f:
        for p in interpretation_rules:
            for rule in interpretation_rules[p]:
                f.write("{} {} {} {}\n".format(p, rule['question'], rule['answer'], rule['result']))

def annotate_sessions(sessions):
    p = raw_input("What is the name of the property you want to annotate?\n")
    matched_questions = set()
    unmatched_questions = set()
    for session in sessions:
        if not session.defined(p):
            questions = set(session.survey_responses.keys()) - unmatched_questions
            question = None
            for q in matched_questions & questions:
                if not question:
                    question = q
                else:
                    raise Exception("Multiple matched questions!")
            if not questions:
                question = None
            elif not question:
                picker = Pick(
                    [{'text':q, 'value':q} for q in questions] + \
                    [{'text':"None of the above.", 'value':None}],
                    prompt = "What question do you want to use?"
                )
                question = picker.get_response()
                if question:
                    matched_questions.add(question)
                unmatched_questions.update(questions - {question})
        while not session.defined(p):
            answer = session.survey_responses[question]
            if answer:
                result = input('What value goes with "{}"?\n'.format(answer))
                add_interpretation_rule(p, question, answer, result)
            else:
                break
    save_interpretation_rules()
