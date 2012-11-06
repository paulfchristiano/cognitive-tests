import random
import ast
import utilities
from time import time
from utilities import open_processed as open
from utilities import pretty_print
from collections import Counter,defaultdict

# ------- Framework -------------

class Question:
    unknown = 0
    picked = 1

    def ask(self):
        interaction = Interaction(self)
        attempts = interaction.responses
        while len(attempts) < self.allowed_attempts:
            response = self.ask_once()
            if isinstance(response, Request):
                if response.type == Request.clarification:
                    self.respond_to_clarification_request(response)
                elif response.type == Request.quit:
                    self.finish()
                    return interaction.resolve(Interaction.quit)
                elif response.type == Request.give_up:
                    self.give_away()
                    self.finish()
                    return interaction.resolve(Interaction.give_up)
            else:
                attempts.append(response)
                if self.check(response.answer):
                    self.accept(response.answer)
                    return interaction.resolve(Interaction.correct)
                else:
                    self.reject(response.answer)
        self.give_away()
        self.finish()
        return interaction.resolve(Interaction.incorrect)

    def ask_once(self):
        while True:
            raw_answer = prompt(self.render())
            commands = {
                'help':Request.clarification,
                'explain':Request.clarification,
                'quit':Request.quit,
                'exit':Request.quit,
                'give up':Request.give_up,
                'pass':Request.give_up
            }
            if raw_answer in commands:
                return Request(commands[raw_answer])
            try:
                parsed_answer = self.parse(raw_answer)
                return Response(parsed_answer)
            except ValueError as e:
                self.complain(e)

    def give_away(self):
        print("The correct answer was {}".format(self.correct_answer))

    def accept(self, response):
        print("Correct!")

    def reject(self, response):
        print("Incorrect!")

    def respond_to_clarification_request(self, request):
        print("")
        self.clarify(request)

    def finish(self):
        pass

    def complain(self, e):
        print("That isn't a valid response!")

    def clarify(self, request):
        print("Sorry, no help available!")

    def parse(self, raw_answer):
        return raw_answer

    def check(self, answer):
        return self.test_answer_equality(self.correct_answer, answer)

    @classmethod
    def test_answer_equality(c, answer, correct_answer):
        return c.reduce_answer(answer) == c.reduce_answer(correct_answer)

    @classmethod
    def reduce_answer(c, x):
        return x

    @classmethod
    def make_instance_for_session(c, session, **args):
        if c.name() in session.open_questions:
            questions = session.open_questions[c.name()]
            if questions:
                max_count = max(count for (question, count) in questions.items())
                candidate_questions = set(question 
                                          for (question, count) in questions.items()
                                          if count == max_count)
                question = random.sample(candidate_questions, 1)[0]
                del questions[question]
                return question
        return c.make_instance(**args)

    @classmethod
    def make_instance(c, **args):
        return c(**args)

    @classmethod
    def name(c):
        return c.__name__

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __hash__(self):
        return utilities.make_hash(self.__dict__)

    def __init__(self, allowed_attempts=float("inf"), version=1):
        self.allowed_attempts=allowed_attempts
        self.data_format_version = version

class Interaction:
    indeterminate = 0
    correct = 1
    give_up = 2
    incorrect = 3
    quit = 4

    def resolve(self, status):
        self.status = status
        self.end_time = time()
        return self

    def __getstate__(self):
        picklable = self.__dict__.copy()
        return picklable

    def answer(self):
        if self.responses:
            return self.responses[-1].answer
        else:
            return None

    def __setstate__(self, state):
        assert('question' in state)
        assert('responses' in state)
        self.__dict__ = state

    def duration(self):
        return self.end_time - self.start_time

    def __init__(self, question):
        self.start_time = time()
        self.question = question
        self.end_time = float("inf")
        self.responses = []
        self.status = Interaction.indeterminate


class Response:
    def __init__(self, answer):
        self.answer = answer
        self.time = time()

class Request(Response):
    give_up = 0
    quit = 1
    clarification = 2
    change_user = 3
    options = 4

    def __init__(self, t):
        Response.__init__(self, None)
        self.type = t

class QuestionGenerator():
    def __init__(self, question_type, description="", clarification="", args={}):
        self.question_type = question_type
        self.description = description
        self.clarification = clarification
        self.args = args

    def __getstate__(self):
        picklable = self.__dict__.copy()
        if 'args' in picklable:
            picklable['args'] = None
        return picklable

    def make_instance_for_session(self, session):
        if self.args is None:
            raise Exception("Tried to use an unpickled QuestionGenerator!")
        return self.question_type.make_instance_for_session(session, **self.args)

def prompt(p):
    s = raw_input("\n{}\n\n>>> ".format(p))
    return s



# ------- Multiplication ---------

class MultiplicationQuestion(Question):
    def __init__(self, multiplicands, **args):
        Question.__init__(self, **args)
        self.multiplicands = multiplicands
        multiply = lambda x, y: x * y
        self.correct_answer = reduce(multiply, multiplicands)

    def render(self):
        return "What is {}?".format(" * ".join(str(x) for x in self.multiplicands))

    @classmethod
    def make_instance(c, lower=11, upper=99, n=2):
        return MultiplicationQuestion([random.randint(lower, upper) for i in range(n)])

    def parse(self, raw_answer):
        return int(raw_answer)

# --------- Analogies --------

class StringOperation:
    def apply(self, s):
        l = list(s)
        self.transform_list(l)
        return ''.join(l)

    def size(self):
        return 1

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    def __hash__(self):
        return utilities.make_hash((self.__class__, self.__dict__))
        
class Transposition(StringOperation):
    def __init__(self, i, j):
        self.i = i
        self.j = j

    def transform_list(self, l):
        c = l[self.i]
        l[self.i] = l[self.j]
        l[self.j] = c

    def __str__(self):
        return "Swap({},{})".format(self.i,self.j)

class Shift(StringOperation):
    def __init__(self, i, d):
        self.i = i
        self.d = d

    def transform_list(self, l):
        l[self.i] = self.alphabet[(self.alphabet.find(l[self.i])+self.d)%len(self.alphabet)]
        return l

    def __str__(self):
        return "Shift({},{})".format(self.i,self.d)

class Exchange(StringOperation):
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def transform_list(self, l):
        for i in range(len(l)):
            if l[i] == self.a:
                l[i] = self.b
            elif l[i] == self.b:
                l[i] = self.a

    def __str__(self):
        return "Exchange({},{})".format(self.a, self.b)

class Rotation(StringOperation):
    def __init__(self, d):
        self.d = d

    def transform_list(self, l):
        n = l[:]
        for i in range(len(l)):
            l[i] = n[(i+self.d)%len(n)]

    def __str__(self):
        return "Rotate({})".format(self.d)

class Reflection(StringOperation):
    def transform_list(self, l):
        l.reverse()

    def __str__(self):
        return "Reflect"

class CompositeOperation(StringOperation):
    def __init__(self, ops):
        self.ops = ops

    def transform_list(self, l):
        for op in self.ops:
            op.transform_list(l)

    def size(self):
        return sum(op.size() for op in self.ops)

    def __str__(self):
        return "({})".format(".".join(str(op) for op in self.ops))

def random_operation(size, alphabet):
    op = random.choice([
        lambda : Transposition( random.randint(0, size-1), random.randint(0,size-1)),
        lambda : Shift(random.randint(0, size-1), random.randint(1,len(alphabet)-1)),
        lambda : Exchange(random.choice(alphabet), random.choice(alphabet)),
        lambda : Rotation(random.randint(1, size-1)),
        lambda : Reflection()
    ])()
    op.alphabet = alphabet
    return op

def random_transformation(size, alphabet, length):
    return CompositeOperation([random_operation(size, alphabet) for i in range(length)])

def random_string(size, alphabet):
    return ''.join(random.choice(alphabet) for i in range(size))

class AnalogyQuestion(Question):
    def __init__(self, op, examples, test, alphabet):
        Question.__init__(self)
        self.op = op
        self.alphabet = alphabet
        self.labeled_examples = [(example, op.apply(example)) for example in examples]
        self.test = test
        self.correct_answer = op.apply(test)

    def render(self):
        return "Complete the pattern:\n{}\n{}".format(
            "\n".join("{} --> {}".format(example, label) 
                      for (example, label) in self.labeled_examples),
            "{} --> ?".format(self.test)
        )

    def give_away(self):
        print("The hidden transformation was {}".format(self.op))
        print("The answer was {}".format(self.correct_answer))

    def clarify(self, request):
        pretty_print('There is a simple rule that relates each string '\
              'on the left hand side to its partner on the right hand side.')
        print('Find the rule, and determine what string should replace "?".')
        pretty_print('The rule consists of up to {} atomic operations, '\
              'each of which is one of:'.format(self.op.size()))
        print(' (*) Switching two positions in the string')
        print(' (*) Reversing the string')
        print(' (*) Rotating the whole string a random distance to the left or right')
        print('     (e.g. shifting each symbol one step to the right, and replacing the first with the last)')
        print(' (*) Applying the substitution {} (or its reverse) at one index'.format(
            '->'.join(self.alphabet + self.alphabet[0])
        ))
        print(' (*) Replacing each {0} with {1} and vice versa (or {1} with {2}, etc.)'.format(
            self.alphabet[0], self.alphabet[1], self.alphabet[2]
        ))

    @classmethod
    def make_instance(c, size=8, alphabet='abc', length=4, examples=4):
        return AnalogyQuestion(
            random_transformation(size, alphabet, length),
            [random_string(size, alphabet) for i in range(examples)],
            random_string(size, alphabet),
            alphabet
        )

    def parse(self, raw_answer):
        answer = raw_answer.strip()
        if len(answer) != len(self.correct_answer):
            raise ValueError('len', len(answer))
        if not set(answer) <= set(self.alphabet):
            raise ValueError('chars')
        return answer

    def complain(self, e):
        if e.args[0] == 'len':
            print("You should enter a string of length {} (not {})".format(
                len(self.correct_answer),
                e.args[1]
            ))
        if e.args[0] == 'chars':
            print("Your string should use only letters {}".format(', '.join(self.alphabet)))

# ---------- Anagram Question ---------

dictionary = None

def get_dictionary():
    global dictionary
    if dictionary is None:
        dictionary = set()
        with open("dictionary", "r") as dictionary_file:
            for line in dictionary_file:
                word = line[:-1]
                if len(word) > 4 and len(word) < 8:
                    dictionary.add(word)
    return dictionary

class AnagramQuestion(Question):
    def __init__(self, original, scrambled):
        Question.__init__(self)
        self.correct_answer = original
        self.scrambled = scrambled

    def render(self):
        return "Anagram {}.".format(self.scrambled)

    def clarify(self, request):
        pretty_print('Rearrange the letters "{}" to make '\
              'an English word or proper noun.'.format(self.scrambled))

    def check(self, answer):
        return ((Counter(answer) == Counter(self.correct_answer)) 
                    and answer in get_dictionary())

    @classmethod
    def make_instance(c):
        word = random.sample(get_dictionary(), 1)[0]
        word_letters = list(word)
        random.shuffle(word_letters)
        return AnagramQuestion(word, ''.join(word_letters))


# ------------ Expression Question ------------

class ExpressionChecker(ast.NodeVisitor):
    def generic_visit(self, node):
        valid_node_types = {'Module', 'Expr', 'BinOp', 'Num', 'Mult', 'Sub', 'Add'}
        if type(node).__name__ not in valid_node_types:
            self.valid_expr = False
        if type(node).__name__ == 'Num':
            self.atoms[node.n]+=1
        ast.NodeVisitor.generic_visit(self, node)

    def check_expr(self, expr):
        self.valid_expr = True
        self.atoms = Counter()
        self.generic_visit(ast.parse(expr))
        return self.valid_expr and self.atoms == self.target_count

    def __init__(self, target_count):
        self.target_count = target_count

class Expression:
    @classmethod
    def random_expr(c, size, atoms):
        if size == 1:
            return Expression('Num', val=random.choice(atoms))
        else:
            op = random.choice(['Mult', 'Mult', 'Sub', 'Add', 'Add'])
            left = random.randint(1, size-1)
            right = size - left
            return Expression(op, c.random_expr(left, atoms), 
                                  c.random_expr(right, atoms))

    def render(self):
        if self.op == 'Num':
            return str(self.val)
        c = {
            'Sub':'-',
            'Mult':'*',
            'Add':'+'
        }[self.op]
        return "({} {} {})".format(self.left.render(), c, self.right.render())

    def eval(self):
        if self.op == 'Num':
            return self.val
        f = {
            'Sub':lambda x, y: x - y,
            'Mult':lambda x, y: x * y,
            'Add':lambda x, y: x + y
        }[self.op]
        return f(self.left.eval(), self.right.eval())

    def atoms(self):
        if self.op == 'Num':
            return Counter([self.val])
        return self.left.atoms() + self.right.atoms()

    def __init__(self, op, left=None, right=None, val=None):
        self.op = op
        self.left = left
        self.right = right
        self.val = val

    def __eq__(self, other):
        return self.render() == other.render()

    def __hash__(self):
        return hash(self.render())

class ExpressionQuestion(Question):
    def __init__(self, expr):
        Question.__init__(self)
        self.correct_answer = expr
        self.val = expr.eval()
        self.atoms = list(expr.atoms().elements())
        random.shuffle(self.atoms)

    def render(self):
        return "Make {} out of the numbers {}".format(
            str(self.val), ", ".join(str(x) for x in self.atoms)
        )

    def clarify(self, request):
        pretty_print("Find an arithmetic expression using the operators +, *, -, parentheses,"\
              " and the numbers {} each exactly once, whose value is {}".format( 
                  ", ".join(str(x) for x in self.atoms), self.val
             ))
        print("")
        pretty_print("Note that you can't use - to make a negative number directly, e.g. -3*4,"\
             " and you can't use / or ^.")
        

    def give_away(self):
        print("A correct answer was {}".format(self.correct_answer.render()))

    def parse(self, expr):
        try:
            eval(expr)
        except Exception as e:
            raise ValueError("Couldn't parse your answer: {}".format(e))
        return expr

    def complain(self, e):
        print(e)


    def check(self, expr):
        return (ExpressionChecker(Counter(self.atoms)).check_expr(expr) 
                and eval(expr) == self.val)

    @classmethod
    def make_instance(c, size=5, atoms=range(1, 13)):
        return ExpressionQuestion(Expression.random_expr(size, atoms))

# ------------ Medley ---------

class Medley(Question):
    @classmethod
    def make_instance_for_session(c, session):
        templates = [
            MultiplicationQuestion,
            AnagramQuestion,
            AnalogyQuestion,
            ExpressionQuestion
        ]
        times = defaultdict(lambda : 0)
        for interaction in session.interactions:
            if interaction.question:
                times[interaction.question.__class__] += interaction.duration()
        smallest_time = float('inf')
        least_popular = None
        for template in templates:
            time = times[template]
            noisy_time = time * (1 + 0.2 * random.random()) + random.random()
            if noisy_time < smallest_time:
                smallest_time = noisy_time
                least_popular = template
        return least_popular.make_instance_for_session(session)

# ------------ Menus ------------

class Pick(Question):
    def __init__(self, options, **args):
        Question.__init__(self, **args)
        self.options = options

    def reject(self, response):
        pass

    def accept(self, response):
        pass

    def give_away(self):
        pass

    def clarify(self, request):
        pretty_print("Enter the number to the left of a question type "\
              "to answer questions of that type.")
        for option in self.options:
            if 'clarification' in option and option['clarification']:
                pretty_print(option['clarification'])

    def render(self):
        return "\n".join("({}) {}".format(i, option['text']) 
                         for i, option in enumerate(self.options))

    def complain(self, e):
        print("You must enter an integer between 0 and {}.".format(len(self.options)-1))

    def parse(self, raw_answer):
        index = int(raw_answer)
        if index < 0 or index >= len(self.options):
            raise ValueError
        return self.options[index]['value']

    def check(self, answer):
        return True

class OptionMenu(Pick):
    def __init__(self, options, option_args={}):
        Pick.__init__(self, options)
        self.option_args = option_args

    def clarify(self, request):
        pretty_print("Enter the number to the left of a setting to toggle the indicated setting"\
        " or perform the indicated operation.")

    def check(self, response):
        return False

    def reject(self, response):
        response(**self.option_args)

    def __getstate__(self):
        picklable = self.__dict__.copy()
        if 'options' in picklable:
            del picklable['options']
        return picklable

    def render(self):
        return "\n".join("({}) {}".format(i, option['text'].format(
                option['display'](**self.option_args) if 'display' in option else ""
            )) for i, option in enumerate(self.options))

    @classmethod
    def make_instance_for_session(c, session, **args):
        option_args = {'session':session}
        if 'option_args' in args:
            option_args.update(args['option_args'])
        return c(option_args = option_args, **args)

class Survey(OptionMenu):
    def __init__(self, questions, answers):
        def inquire(x):
            def inquire_for_x():
                answers[x] = prompt(x)
            return inquire_for_x
        def display_answer(x):
            return lambda : answers.get(x, "")
        options = [{'text':"{} {}".format(question, "{}"), 
                           'display':display_answer(question),
                           'value':inquire(question)}
                         for question in questions]
        OptionMenu.__init__(self, options)

    @classmethod
    def make_instance_for_session(c, session, questions):
        return Survey(questions, session.survey_responses)
