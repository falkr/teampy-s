import io
from flask import Flask
from flask import request
from flask import redirect
from flask import render_template
from flask import send_file
import uuid
import random
import string
from flask_pymongo import PyMongo

app = Flask(__name__)

app.config['SECRET_KEY'] = 'Hemmelig!'  ## is required
app.config["MONGO_DBNAME"] = "ratdb"  ## DB name
app.config["MONGO_URI"] = "mongodb://localhost:27017/ratdb"

mongo = PyMongo(app)
ratdb = mongo.db.ratdb

colors = ['STEELBLUE', 'CADETBLUE', 'LIGHTSEAGREEN', 'OLIVEDRAB', 
    'YELLOWGREEN', 'FORESTGREEN', 'MEDIUMSEAGREEN', 'LIGHTGREEN', 
    'LIMEGREEN', 'DARKMAGENTA', 'DARKORCHID', 'MEDIUMORCHID', 'ORCHID', 
    'ORANGE', 'ORANGERED', 'CORAL', 'LIGHTSALMON', 'PALEVIOLETRED', 
    'MEDIUMVIOLETRED', 'DEEPPINK', 'CRIMSON', 'SALMON']

class AnswerState():
    def __init__(self, question, symbol, correct=False, uncovered=False):
        self.question = question
        self.symbol = symbol
        self.correct = correct
        self.uncovered = uncovered
    
    def to_dict(self):
        d = {'symbol': self.symbol,
             'correct': self.correct,
             'uncovered': self.uncovered}
        return d

    @staticmethod
    def from_dict(d, question):
        return AnswerState(question, d['symbol'], d['correct'], d['uncovered'])
    
    def html(self):
        s = []
        if self.uncovered:
            if self.correct:
                s.append('<div class="btn-group" role="group">')
                s.append('<a class="answer btn btn-secondary btn-success disabled">')
                s.append('<svg class="bi bi-check-circle-fill" width="1em" height="1em" viewBox="0 0 16 16" fill="currentColor" xmlns="http://www.w3.org/2000/svg">')
                s.append('<path fill-rule="evenodd" d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zm-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/>')
                s.append('</svg>')
                s.append('</a>')
                s.append('</div>')
            else:
                s.append('<div class="btn-group" role="group">')
                s.append('<a class="answer btn btn-secondary btn-success disabled">&nbsp;</a>')
                s.append('</div>')
        else:
            if self.question.finished:
                s.append('<div class="btn-group" role="group">')
                s.append('<a class="answer btn btn-secondary disabled">&nbsp;</a>')
                s.append('</div>')
            else:
                url = './?question={}&alternative={}'.format(self.question.number, self.symbol)
                s.append('<div class="btn-group" role="group">')
                s.append('<a class="answer btn btn-secondary" href="{}">&nbsp;</a>'.format(url))
                s.append('</div>')
        return ''.join(s)

class Question():

    def __init__(self, number, finished, started, correct_on_first_attempt, first_guess, answers):
        self.number = number
        self.finished = finished
        self.started = started
        self.correct_on_first_attempt = correct_on_first_attempt
        self.first_guess = first_guess
        self.answers = answers
    
    def to_dict(self):
        d = {'number': self.number,
             'finished': self.finished,
             'started': self.started,
             'correct_on_first_attempt': self.correct_on_first_attempt,
             'first_guess': self.first_guess}
        d['answers'] = {key : self.answers[key].to_dict() for key in self.answers.keys()}
        return d

    @staticmethod
    def from_dict(d):
        question = Question(d['number'], 
            d['finished'], d['started'], 
            d['correct_on_first_attempt'], d['first_guess'], None)
        question.answers = {key: AnswerState.from_dict(d['answers'][key], question) for key in d['answers'].keys()}
        return question
  
    @staticmethod
    def new_question(number, correct_alternative, alternatives=4):
        answers = {}
        finished, started, correct_on_first_attempt = False, False, False
        first_guess = None
        question = Question(number, finished, started, correct_on_first_attempt, first_guess, answers)
        for symbol in 'ABCDEFGH'[:alternatives]:
            correct = symbol.lower() == correct_alternative.lower()
            question.answers[symbol] = AnswerState(question, symbol, correct=correct)
        return question
    
    def html(self):
        s = []
        s.append('<tr>')
        s.append('<td>{}</td>'.format(self.number))
        for a in self.answers.values():
            s.append('<td>')
            s.append(a.html())
            s.append('</td>')
        s.append('</tr>')
        return ''.join(s)

    def uncover(self, alternative):
        answer_state = self.answers[alternative]
        answer_state.uncovered = True
        if not self.started:
            self.first_guess = alternative
            if answer_state.correct:
                self.correct_on_first_attempt = True
        if answer_state.correct:
            self.finished = True
        self.started = True
        
    def get_state(self):
        if self.correct_on_first_attempt:
            return 'OK'
        elif self.started:
            return self.first_guess
        return ''

    def get_state_string_export(self):
        if self.started:
            return self.first_guess
        return '-'

class Card():

    def __init__(self, id, label, team, questions, alternatives, solution, color):
        self.id = id
        self.label = 'Team Quiz' if label is None else label
        self.team = team
        self.questions = questions
        self.alternatives = alternatives
        self.solution = solution
        self.color = color

    def to_dict(self):
        d = {'id': self.id,
             'label': self.label,
             'team': self.team,
             'alternatives': self.alternatives,
             'solution': self.solution,
             'color': self.color}
        d['questions'] = {key : self.questions[key].to_dict() for key in self.questions.keys()}
        return d

    @staticmethod
    def new_card(label, team, questions, alternatives, solution, color):
        id = '{}'.format(uuid.uuid4())
        questions = {}
        for index, c in enumerate(solution):
            questions[str(index+1)] = Question.new_question(index+1, c, alternatives=alternatives)
        return Card(id, label, team, questions, alternatives, solution, color)

    @staticmethod
    def from_dict(d):
        questions = {key: Question.from_dict(d['questions'][key]) for key in d['questions'].keys()}
        return Card(d['id'], d['label'], d['team'], 
            questions, d['alternatives'], d['solution'], d['color'])

    def uncover(self, question, alternative):
        question = self.questions[str(question)]
        question.uncover(alternative)

    def get_card_html(self, base_url):
        s = []
        s.append('<table width="100%">')
        s.append('<thead>')
        s.append('<tr>')
        s.append('<th></th>')
        for symbol in 'ABCDEFGH'[:self.alternatives]:
            s.append('<th>{}</th>'.format(symbol))
        s.append('</tr>')
        s.append('</thead>')
        s.append('<tbody>')
        for q in self.questions.values():
            s.append(q.html())
        s.append('</tbody>')
        s.append('</table>')
        url = base_url + 'card/' + self.id
        return render_template('card.html', table=''.join(s), label=self.label, team=self.team, url=url, primary=self.color)

    def get_link(self):
        return 'card/{}'.format(self.id)

    def get_state(self):
        started = False
        finished = True
        for q in self.questions.values():
            if q.started:
                started = True
            if not q.finished:
                finished = False
        if finished:
            return 'finished'
        elif started:
            return 'ongoing'
        return 'idle'

    def get_score(self):
        score = 0
        for q in self.questions.values():
            if q.correct_on_first_attempt:
                score = score + 1
        return score

    def get_table_row(self, base_url):
        s = []
        s.append('<tr>')
        url = base_url + 'card/' + self.id 
        s.append('<th scope="row"><a href="{}">{}</a></th>'.format(url, self.team))
        s.append('<td>{}</td>'.format(self.get_state()))
        s.append('<td>{}</td>'.format(self.get_score()))
        for q in self.questions.values():
            s.append('<td>{}</td>'.format(q.get_state()))
        s.append('</tr>')
        return ''.join(s)

    def get_text_result(self):
        s = []
        s.append('{}/'.format(self.team))
        for q in self.questions.values():
            s.append('{}'.format(q.get_state_string_export()))
        return ''.join(s)

class RAT():

    def __init__(self, private_id, public_id, label, teams, questions, alternatives, solution, team_colors):
        self.private_id = private_id
        self.public_id = public_id
        self.label = label
        self.teams = int(teams)
        self.questions = questions
        self.alternatives = alternatives
        self.solution = solution
        self.card_ids_by_team = {}
        self.grabbed_rats = []
        self.team_colors = team_colors

    def to_dict(self):
        d = {'private_id': self.private_id,
             'public_id' : self.public_id,
             'label': self.label,
             'teams': self.teams,
             'questions': self.questions,
             'alternatives': self.alternatives,
             'solution': self.solution,
             'team_colors': self.team_colors,
             'grabbed_rats': self.grabbed_rats,
             'card_ids_by_team': self.card_ids_by_team}
        return d

    @staticmethod
    def from_dict(d):
        rat = RAT(
            d['private_id'], d['public_id'], 
            d['label'], d['teams'], d['questions'], d['alternatives'], d['solution'], d['team_colors'])
        rat.grabbed_rats = d['grabbed_rats']
        rat.card_ids_by_team = d['card_ids_by_team']
        return rat

    def get_status_table(self, base_url, cards):
        s = []
        s.append('<table class="table table-sm">')
        s.append('<thead>')
        s.append('<tr>')
        s.append('<th scope="col">Team</th>')
        s.append('<th scope="col">Status</th>')
        s.append('<th scope="col">Score</th>')
        for q in range(1, int(self.questions) + 1, 1):
            s.append('<th scope="col">{}</th>'.format(q))
        s.append('</tr>')
        s.append('</thead>')
        s.append('<tbody>')
        for card in cards:
            s.append(card.get_table_row(base_url))
        s.append('</tbody>')
        s.append('</table>')
        return ''.join(s)

    def html_teacher(self, base_url, cards):
        s = []
        public_url = base_url + 'rat/{}'.format(self.public_id)
        private_url = base_url + 'teacher/{}'.format(self.private_id)
        download_url = base_url + 'download/{}'.format(self.private_id)
        return render_template('rat_teacher.html', public_url=public_url, private_url=private_url, table=self.get_status_table(base_url, cards), download_url=download_url)

    def html_students(self, base_url):
        s = []
        for team in range(1, self.teams + 1, 1):
            # /grab/<public_id>/<team>
            url = base_url + 'grab/{}/{}'.format(self.public_id, team)
            s.append('<li class="col mb-4"><a class="" href="{}"><div class="name text-decoration-none text-center pt-1 team" style="background-color: {}">Team {}</div></a></li>'.format(url, self.team_colors[team-1], team))
        return render_template('rat_students.html', teams=''.join(s), url=base_url, public_id=self.public_id)

    def grab(self, team):
        if team in self.grabbed_rats:
            return None
        else:
            self.grabbed_rats.append(team)
            # TODO check if team exists
            return self.card_ids_by_team[team]
    
    def download(self, format, cards):
        if format == "string":
            s = []
            for card in cards:
                s.append(card.get_text_result())
            return send_file(io.BytesIO('\n'.join(s).encode('utf-8')),
                     attachment_filename='trat.txt',
                     as_attachment=True,
                     mimetype='text/text')

# all scratchcards
cards = {}
# teacher UUID to RAT
rats_by_private_id = {}
# student access to RAT
rats_by_public_id = {}

use_variables = False

def find_rat_by_public_id(public_id):
    if use_variables:
        global rats_by_public_id
        if public_id in rats_by_public_id:
            return RAT.from_dict(rats_by_public_id[public_id])
    else:
        data = ratdb.find_one({'public_id': public_id})
        if data:
            return RAT.from_dict(data)
    return None

def find_rat_by_private_id(private_id):
    if use_variables:
        global rats_by_private_id
        if private_id in rats_by_private_id:
            d = rats_by_private_id[private_id]
            return RAT.from_dict(d)
    else:
        data = ratdb.find_one({'private_id': private_id})
        if data:
            return RAT.from_dict(data)
    return None

def store_rat(rat):
    data = rat.to_dict()
    if use_variables:
        global rats_by_private_id
        global rats_by_public_id
        rats_by_private_id[rat.private_id] = data
        rats_by_public_id[rat.public_id] = data
    else:
        ratdb.replace_one({'private_id': rat.private_id}, data, upsert=True)

def find_card_by_id(card_id):
    if use_variables:
        global cards
        if card_id in cards:
            return Card.from_dict(cards[card_id])
    else:
        data = ratdb.find_one({'id': card_id})
        if data:
            return Card.from_dict(data)
    return None

def store_card(card):
    data = card.to_dict()
    if use_variables:
        global cards
        cards[card.id] = data
    else:
        ratdb.replace_one({'id': card.id}, data, upsert=True)


@app.route('/')
def index():
    action_url = request.host_url + 'join'
    return render_template('start.html', primary='#007bff', action_url=action_url)

def return_student_page(public_id):
    rat = find_rat_by_public_id(public_id)
    if rat is None:
        return "Could not find rat."
    else:
        return rat.html_students(request.host_url)

@app.route('/join', methods=['POST', 'GET'])
def join():
    rat = request.args['rat']
    return return_student_page(rat)

@app.route('/rat/<public_id>/')
def show_rat_students(public_id):
    return return_student_page(public_id)

@app.route('/new/', methods=['POST', 'GET'])
def new():
    action_url = request.host_url + 'create'
    return render_template('new_rat.html', primary='#007bff', action_url=action_url)

def validate_solution(solution, questions, alternatives):
    valid_alternatives = 'ABCDDEFGH'[:alternatives]
    if len(solution) != questions:
        return 'You specified {} questions, but provided {} solution alternatives.'.format(questions, len(solution))
    for c in solution.upper():
        if c not in valid_alternatives:
            return 'The letter {} is not a valid solution with {} alternatives.'.format(c, alternatives)
    return None # all okay

@app.route('/create', methods=['POST', 'GET'])
def create():
    label = request.args['label'] if 'label' in request.args else None
    teams = int(request.args['teams'])
    questions = int(request.args['questions'])
    alternatives = int(request.args['alternatives'])
    solution = request.args['solution']
    message = validate_solution(solution, questions, alternatives)
    if message is not None:
        return message
    app.logger.debug('Create new RAT label: {}, teams: {}, questions: {}, alternatives: {}, solution: {}'.format(label, teams, questions, alternatives, solution))
    private_id = '{}'.format(uuid.uuid4())
    public_id = ''.join(random.choices(string.ascii_uppercase, k=5))
    team_colors = random.sample(colors, teams) 
    rat = RAT(private_id, public_id, label, teams, questions, alternatives, solution, team_colors)
    # create a new card for each team
    for team in range(1, int(teams) + 1, 1):
        card = Card.new_card(label, str(team), int(questions), int(alternatives), solution, rat.team_colors[team-1])
        store_card(card)
        rat.card_ids_by_team[str(team)] = card.id
    store_rat(rat)
    return redirect("../teacher/{}".format(rat.private_id), code=302)

@app.route('/teacher/<private_id>/')
def show_rat_teacher(private_id):
    rat = find_rat_by_private_id(private_id)
    if rat is None:
        return "Could not find rat."
    rat_cards = []
    for card_id in rat.card_ids_by_team.values():
        card = find_card_by_id(card_id)
        if card is not None:
            rat_cards.append(card)
    return rat.html_teacher(request.host_url, rat_cards)

@app.route('/card/<id>/')
def show_card(id):
    card = find_card_by_id(id)
    if card is None:
        return "Could not find card."
    # check if the page request also answers a question
    if ('question' in request.form): # and ('alternative' in request.form):
        question = request.form['question']
        alternative = request.form['alternative']
        card.uncover(question, alternative)
    if ('question' in request.args): # and ('alternative' in request.form):
        question = request.args['question']
        alternative = request.args['alternative']
        card.uncover(question, alternative)
    store_card(card)
    return card.get_card_html(request.host_url)

@app.route('/grab/<public_id>/<team>')
def grab_rat_students(public_id, team):
    rat = find_rat_by_public_id(public_id)
    if rat is None:
        return "Could not find RAT."
    card_id = rat.grab(team)
    if card_id is None:
        return 'Somebody already grabbed that card.'
    card = find_card_by_id(card_id)
    if card is None:
        return "Could not find card with ID {}".format(card_id)
    store_rat(rat)
    return redirect("../../card/{}".format(card_id), code=302)

@app.route('/download/<private_id>/<format>/')
def download(private_id, format):
    rat = find_rat_by_private_id(private_id)
    if rat is None:
        return "Could not find RAT."
    rat_cards = []
    for card_id in rat.card_ids_by_team.values():
        card = find_card_by_id(card_id)
        if card is not None:
            rat_cards.append(card)
    return rat.download(format, rat_cards)