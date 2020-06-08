from flask import Flask
from flask import request
from flask import redirect
from flask import render_template
import uuid
import random
import string

app = Flask(__name__)

cards = {}
rats_by_private_id = {}
rats_by_public_id = {}

class AnswerState():
    def __init__(self, question, symbol, correct=False, uncovered=False):
        self.question = question
        self.symbol = symbol
        self.correct = correct
        self.uncovered = uncovered
    
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
    def __init__(self, number, correct_alternative, alternatives=4):
        self.number = number
        self.finished = False
        self.started = False
        self.correct_on_first_attempt = False
        self.first_guess = None
        self.answers = {}
        for symbol in 'ABCDEFGH'[:alternatives]:
            correct = symbol.lower() == correct_alternative.lower()
            self.answers[symbol] = AnswerState(self, symbol, correct=correct)
    
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
        print('question {} uncoiver {}'.format(self.number, alternative))
        
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

class Card():

    def __init__(self, id, label, team, questions, alternatives, solution):
        self.id = id
        self.label = 'Team Quiz' if label is None else label
        self.team = team
        self.questions = questions
        self.alternatives = alternatives
        self.solution = solution

    @staticmethod
    def new_card(label, team, questions, alternatives, solution):
        id = '{}'.format(uuid.uuid4())
        # TODO get card from code
        questions = {}
        for index, c in enumerate(solution):
            questions[str(index+1)] = Question(index+1, c, alternatives=alternatives)
        return Card(id, label, team, questions, alternatives, solution)

    def uncover(self, question, alternative):
        print('uncover {} {}'.format(question, alternative))
        question = self.questions[str(question)]
        question.uncover(alternative)
        # check now if the right answer is found implicitly
        # uncover the last remaining answer alternative
        # TODO

    def get_card_html(self, base_url):
        s = []
        s.append('<table width="100%">')
        s.append('<thead>')
        s.append('<tr>')
        s.append('<th></th>')
        for symbol in 'ABCD': # TODO make flexible
            s.append('<th>{}</th>'.format(symbol))
        s.append('</tr>')
        s.append('</thead>')
        s.append('<tbody>')
        for q in self.questions.values():
            s.append(q.html())
        s.append('</tbody>')
        s.append('</table>')
        url = base_url + 'card/' + self.id
        primary = 'red'
        return render_template('card.html', table=''.join(s), label=self.label, team=self.team, url=url, primary=primary)

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

class RAT():

    def __init__(self, private_id, public_id, label, teams, questions, alternatives, solution):
        self.private_id = private_id
        self.public_id = public_id
        self.label = label
        self.teams = int(teams)
        self.questions = questions
        self.alternatives = alternatives
        self.solution = solution
        self.card_ids_by_team = {}
        self.grabbed_rats = []

    @staticmethod
    def new_rat(label, teams, questions, alternatives, solution):
        app.logger.debug('Create new RAT label: {}, teams: {}, questions: {}, alternatives: {}, solution: {}'.format(label, teams, questions, alternatives, solution))
        private_id = '{}'.format(uuid.uuid4())
        public_id = ''.join(random.choices(string.ascii_uppercase, k=5)) 
        rat = RAT(private_id, public_id, label, teams, questions, alternatives, solution)
        global rats_by_private_id
        global rats_by_public_id
        rats_by_private_id[private_id] = rat
        rats_by_public_id[public_id] = rat
        # create a new card for each team
        global cards
        for team in range(1, int(teams) + 1, 1):
            team = str(team)
            card = Card.new_card(label, team, int(questions), int(alternatives), solution)
            cards[card.id] = card
            rat.card_ids_by_team[team] = card.id
        return rat

    def get_status_table(self, base_url):
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
        global cards
        for card_id in self.card_ids_by_team.values():
            card = cards[card_id]
            s.append(card.get_table_row(base_url))
        s.append('</tbody>')
        s.append('<table>')
        return ''.join(s)

    def html_teacher(self, base_url):
        s = []
        public_url = base_url + 'rat/{}'.format(self.public_id)
        private_url = base_url + 'teacher/{}'.format(self.private_id)
        return render_template('rat_teacher.html', public_url=public_url, private_url=private_url, table=self.get_status_table(base_url))

    def html_students(self, base_url):
        s = []
        for team in range(1, self.teams + 1, 1):
            # /grab/<public_id>/<team>
            url = base_url + 'grab/{}/{}'.format(self.public_id, team)
            s.append('<li class="col mb-4"><a class="" href="{}"><div class="name text-decoration-none text-center pt-1 team">Team {}</div></a></li>'.format(url, team))
        return render_template('rat_students.html', teams=''.join(s), url=base_url + 'rat/' + self.public_id)

    def grab(self, team):
        if team in self.grabbed_rats:
            return None
        else:
            self.grabbed_rats.append(team)
            # TODO check if team exists
            return self.card_ids_by_team[team]


def wrap_html(content):
    s = []
    s.append('<html>')
    s.append('<head>')
    s.append('</head>')
    s.append('<body>')
    s.append(content)
    s.append('</body>')
    s.append('</html>')
    return ''.join(s)

@app.route('/')
def index():
    return 'Digital RATs'

@app.route('/new/', methods=['POST', 'GET'])
def new():
    action_url = request.host_url + 'create'
    return render_template('new_rat.html', primary='#007bff', action_url=action_url)

@app.route('/create', methods=['POST', 'GET'])
def create():
    label = request.args['label'] if 'label' in request.args else None
    teams = request.args['teams']
    questions = request.args['questions']
    alternatives = request.args['alternatives']
    solution = request.args['solution']
    rat = RAT.new_rat(label, teams, questions, alternatives, solution)
    return redirect("../teacher/{}".format(rat.private_id), code=302)

@app.route('/teacher/<private_id>/')
def show_rat_teacher(private_id):
    global rats_by_private_id
    if private_id in rats_by_private_id:
        rat = rats_by_private_id[private_id]
        return rat.html_teacher(request.host_url)
    return "Could not find rat"

@app.route('/card/<id>/')
def show_card(id):
    global cards
    if id in cards:
        card = cards[id]
        # check if the page request also answers a question
        if ('question' in request.form): # and ('alternative' in request.form):
            question = request.form['question']
            alternative = request.form['alternative']
            card.uncover(question, alternative)
        if ('question' in request.args): # and ('alternative' in request.form):
            question = request.args['question']
            alternative = request.args['alternative']
            card.uncover(question, alternative)
        return card.get_card_html(request.host_url)
    else:
        return "Could not find rat {}".format(rats_by_public_id)

@app.route('/rat/<public_id>/')
def show_rat_students(public_id):
    global rats_by_public_id
    if public_id in rats_by_public_id:
        rat = rats_by_public_id[public_id]
        return rat.html_students(request.host_url)
    return "Could not find rat"

@app.route('/grab/<public_id>/<team>')
def grab_rat_students(public_id, team):
    global rats_by_public_id
    app.logger.debug(rats_by_public_id)
    app.logger.debug(public_id)
    if public_id not in rats_by_public_id:
        return "Could not find rat {}".format(rats_by_public_id)
    else:
        rat = rats_by_public_id[public_id]
        card_id = rat.grab(team)
        if card_id is None:
            return 'Somebody already grabbed that card.'
        else:
            global cards
            if card_id in cards:
                return redirect("../../card/{}".format(card_id), code=302)
            else:
                return "Could not find card with ID {}".format(card_id)

