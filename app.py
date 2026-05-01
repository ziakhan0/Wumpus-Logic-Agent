from flask import Flask, jsonify, request
from flask_cors import CORS
import random
import json
from itertools import combinations

app = Flask(__name__)
CORS(app)

# ─── Knowledge Base & Resolution Engine ───────────────────────────────────────

class KnowledgeBase:
    def __init__(self):
        self.clauses = set()       # CNF clauses as frozensets of literals
        self.raw_facts = []        # Human-readable facts
        self.inference_steps = 0

    def tell(self, clause_list, description=""):
        """Add clauses (CNF) to KB"""
        for clause in clause_list:
            self.clauses.add(frozenset(clause))
        if description:
            self.raw_facts.append(description)

    def tell_no_breeze(self, r, c, rows, cols):
        """No breeze → no pits in adjacent cells"""
        neighbors = get_neighbors(r, c, rows, cols)
        clauses = []
        facts = []
        for nr, nc in neighbors:
            # ¬P_{nr,nc}
            clauses.append([f"NOT_P_{nr}_{nc}"])
            facts.append(f"¬P_{nr},{nc}")
        self.tell(clauses, f"No breeze at ({r},{c}) → {', '.join(facts)}")
        return facts

    def tell_no_stench(self, r, c, rows, cols):
        """No stench → no Wumpus in adjacent cells"""
        neighbors = get_neighbors(r, c, rows, cols)
        clauses = []
        facts = []
        for nr, nc in neighbors:
            clauses.append([f"NOT_W_{nr}_{nc}"])
            facts.append(f"¬W_{nr},{nc}")
        self.tell(clauses, f"No stench at ({r},{c}) → {', '.join(facts)}")
        return facts

    def tell_breeze(self, r, c, rows, cols):
        """Breeze → at least one adjacent pit"""
        neighbors = get_neighbors(r, c, rows, cols)
        if not neighbors:
            return []
        pos_lits = [f"P_{nr}_{nc}" for nr, nc in neighbors]
        # Breeze ⇒ (P_n1 ∨ P_n2 ∨ ...)
        self.tell([pos_lits], f"Breeze at ({r},{c}) → {' ∨ '.join(['P_'+str(nr)+','+str(nc) for nr,nc in neighbors])}")
        return pos_lits

    def tell_stench(self, r, c, rows, cols):
        """Stench → at least one adjacent Wumpus"""
        neighbors = get_neighbors(r, c, rows, cols)
        if not neighbors:
            return []
        pos_lits = [f"W_{nr}_{nc}" for nr, nc in neighbors]
        self.tell([pos_lits], f"Stench at ({r},{c}) → {' ∨ '.join(['W_'+str(nr)+','+str(nc) for nr,nc in neighbors])}")
        return pos_lits

    def ask_safe(self, r, c):
        """Use Resolution Refutation to prove ¬P_{r,c} ∧ ¬W_{r,c}"""
        safe_pit = self._resolution_refutation(f"P_{r}_{c}")
        safe_wumpus = self._resolution_refutation(f"W_{r}_{c}")
        return safe_pit and safe_wumpus

    def ask_dangerous(self, r, c):
        """Try to prove P_{r,c} or W_{r,c}"""
        has_pit = self._prove_positive(f"P_{r}_{c}")
        has_wumpus = self._prove_positive(f"W_{r}_{c}")
        return has_pit or has_wumpus

    def _resolution_refutation(self, literal):
        """
        Resolution Refutation: To prove ¬P, assume P and derive contradiction.
        Adds negation of goal, then resolves until empty clause (contradiction).
        """
        self.inference_steps += 1
        # Negate the literal we want to disprove
        neg_lit = literal if literal.startswith("NOT_") else f"NOT_{literal}"
        # Start with KB + negation of ¬P (i.e., assume P)
        working_clauses = set(self.clauses)
        working_clauses.add(frozenset([literal]))  # assume the hazard exists

        # Resolution loop
        new_clauses = set()
        MAX_ITER = 500
        iterations = 0
        while iterations < MAX_ITER:
            iterations += 1
            clause_list = list(working_clauses)
            found_new = False
            for i in range(len(clause_list)):
                for j in range(i + 1, len(clause_list)):
                    resolvents = self._resolve(clause_list[i], clause_list[j])
                    for r in resolvents:
                        self.inference_steps += 1
                        if len(r) == 0:  # Empty clause = contradiction!
                            return True  # Proved ¬P
                        if r not in working_clauses:
                            new_clauses.add(r)
                            found_new = True
            if not found_new:
                break
            working_clauses |= new_clauses
            new_clauses = set()
        return False  # Could not prove

    def _prove_positive(self, literal):
        """Try to prove literal directly"""
        self.inference_steps += 1
        neg = f"NOT_{literal}" if not literal.startswith("NOT_") else literal[4:]
        working_clauses = set(self.clauses)
        working_clauses.add(frozenset([neg]))
        MAX_ITER = 200
        iterations = 0
        while iterations < MAX_ITER:
            iterations += 1
            clause_list = list(working_clauses)
            found_new = False
            for i in range(len(clause_list)):
                for j in range(i + 1, len(clause_list)):
                    resolvents = self._resolve(clause_list[i], clause_list[j])
                    for r in resolvents:
                        self.inference_steps += 1
                        if len(r) == 0:
                            return True
            break
        return False

    def _resolve(self, c1, c2):
        """Resolve two clauses, return list of resolvents"""
        resolvents = []
        for lit in c1:
            # Find complementary literal in c2
            complement = lit[4:] if lit.startswith("NOT_") else f"NOT_{lit}"
            if complement in c2:
                new_clause = (c1 - {lit}) | (c2 - {complement})
                resolvents.append(frozenset(new_clause))
        return resolvents

# ─── Game State ───────────────────────────────────────────────────────────────

game_state = {}

def get_neighbors(r, c, rows, cols):
    dirs = [(-1,0),(1,0),(0,-1),(0,1)]
    return [(r+dr, c+dc) for dr,dc in dirs if 0 <= r+dr < rows and 0 <= c+dc < cols]

@app.route('/api/new_game', methods=['POST'])
def new_game():
    data = request.json
    rows = max(2, min(8, int(data.get('rows', 4))))
    cols = max(2, min(8, int(data.get('cols', 4))))
    num_pits = max(1, min(rows*cols//4, int(data.get('pits', 3))))

    # Place agent at (0,0), don't place hazards there
    all_cells = [(r,c) for r in range(rows) for c in range(cols) if (r,c) != (0,0)]
    random.shuffle(all_cells)

    pits = set()
    for cell in all_cells[:num_pits]:
        pits.add(cell)

    wumpus_candidates = [cell for cell in all_cells if cell not in pits]
    wumpus = random.choice(wumpus_candidates) if wumpus_candidates else None

    gold_candidates = [cell for cell in all_cells if cell not in pits and cell != wumpus]
    gold = random.choice(gold_candidates) if gold_candidates else (0, 0)

    kb = KnowledgeBase()

    game_state.clear()
    game_state.update({
        'rows': rows,
        'cols': cols,
        'pits': list(pits),
        'wumpus': list(wumpus) if wumpus else None,
        'gold': list(gold),
        'agent': [0, 0],
        'visited': [[0, 0]],
        'safe_cells': [[0, 0]],
        'confirmed_danger': [],
        'has_gold': False,
        'game_over': False,
        'win': False,
        'kb': kb,
        'percepts_history': [],
        'move_count': 0,
        'log': []
    })

    percepts = get_percepts(0, 0)
    process_percepts(0, 0, percepts)

    return jsonify(get_client_state(percepts))

@app.route('/api/move', methods=['POST'])
def move():
    if not game_state or game_state.get('game_over'):
        return jsonify({'error': 'No active game'}), 400

    data = request.json
    direction = data.get('direction')
    dirs = {'up': (-1,0), 'down': (1,0), 'left': (0,-1), 'right': (0,1)}

    if direction not in dirs:
        return jsonify({'error': 'Invalid direction'}), 400

    r, c = game_state['agent']
    dr, dc = dirs[direction]
    nr, nc = r + dr, c + dc
    rows, cols = game_state['rows'], game_state['cols']

    if not (0 <= nr < rows and 0 <= nc < cols):
        return jsonify({'error': 'Out of bounds'}), 400

    # Check if KB says it's safe
    kb = game_state['kb']
    is_safe = kb.ask_safe(nr, nc)
    is_visited = [nr, nc] in game_state['visited']

    game_state['agent'] = [nr, nc]
    game_state['move_count'] += 1

    if [nr, nc] not in game_state['visited']:
        game_state['visited'].append([nr, nc])

    percepts = get_percepts(nr, nc)

    # Check death conditions
    if (nr, nc) in [tuple(p) for p in game_state['pits']]:
        game_state['game_over'] = True
        game_state['win'] = False
        game_state['log'].append(f"💀 Fell into pit at ({nr},{nc})!")
        return jsonify(get_client_state(percepts, died='pit'))

    if game_state['wumpus'] and (nr, nc) == tuple(game_state['wumpus']):
        game_state['game_over'] = True
        game_state['win'] = False
        game_state['log'].append(f"💀 Eaten by Wumpus at ({nr},{nc})!")
        return jsonify(get_client_state(percepts, died='wumpus'))

    if [nr, nc] == game_state['gold']:
        game_state['has_gold'] = True
        game_state['log'].append(f"✨ Found gold at ({nr},{nc})!")

    if game_state['has_gold'] and [nr, nc] == [0, 0]:
        game_state['game_over'] = True
        game_state['win'] = True
        game_state['log'].append("🏆 Returned home with gold! Victory!")
        return jsonify(get_client_state(percepts, won=True))

    process_percepts(nr, nc, percepts)
    game_state['log'].append(
        f"Moved to ({nr},{nc}). KB said {'safe ✓' if is_safe else 'unknown'}. Percepts: {percepts}"
    )

    return jsonify(get_client_state(percepts))

@app.route('/api/auto_move', methods=['POST'])
def auto_move():
    """Agent chooses best move using KB"""
    if not game_state or game_state.get('game_over'):
        return jsonify({'error': 'No active game'}), 400

    r, c = game_state['agent']
    rows, cols = game_state['rows'], game_state['cols']
    kb = game_state['kb']
    neighbors = get_neighbors(r, c, rows, cols)

    # Priority: unvisited safe cells → visited cells → unknown cells
    best = None
    for nr, nc in neighbors:
        if [nr, nc] not in game_state['visited'] and kb.ask_safe(nr, nc):
            best = ('down' if nr > r else 'up' if nr < r else 'right' if nc > c else 'left')
            break

    if not best:
        # Try any unvisited (risky)
        for nr, nc in neighbors:
            if [nr, nc] not in game_state['visited']:
                best = ('down' if nr > r else 'up' if nr < r else 'right' if nc > c else 'left')
                break

    if not best:
        # Backtrack to visited
        for nr, nc in neighbors:
            if [nr, nc] in game_state['visited']:
                best = ('down' if nr > r else 'up' if nr < r else 'right' if nc > c else 'left')
                break

    if not best:
        return jsonify({'error': 'Agent is stuck!'}), 400

    return move_in_direction(best)

def move_in_direction(direction):
    """Internal helper"""
    from flask import Request
    import werkzeug
    with app.test_request_context('/api/move', method='POST',
                                   content_type='application/json',
                                   data=json.dumps({'direction': direction})):
        return move()

@app.route('/api/ask_cell', methods=['POST'])
def ask_cell():
    """Ask KB about a specific cell"""
    data = request.json
    r, c = int(data['r']), int(data['c'])
    kb = game_state['kb']
    is_safe = kb.ask_safe(r, c)
    is_danger = kb.ask_dangerous(r, c)
    return jsonify({
        'safe': is_safe,
        'dangerous': is_danger,
        'inference_steps': kb.inference_steps,
        'kb_size': len(kb.clauses)
    })

@app.route('/api/state', methods=['GET'])
def get_state():
    if not game_state:
        return jsonify({'error': 'No game'}), 404
    percepts = get_percepts(*game_state['agent'])
    return jsonify(get_client_state(percepts))

# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_percepts(r, c):
    percepts = []
    neighbors = get_neighbors(r, c, game_state['rows'], game_state['cols'])
    for nr, nc in neighbors:
        if (nr, nc) in [tuple(p) for p in game_state['pits']]:
            if 'Breeze' not in percepts:
                percepts.append('Breeze')
        if game_state['wumpus'] and (nr, nc) == tuple(game_state['wumpus']):
            if 'Stench' not in percepts:
                percepts.append('Stench')
    if [r, c] == game_state['gold'] and not game_state['has_gold']:
        percepts.append('Glitter')
    return percepts

def process_percepts(r, c, percepts):
    kb = game_state['kb']
    rows, cols = game_state['rows'], game_state['cols']
    if 'Breeze' not in percepts:
        kb.tell_no_breeze(r, c, rows, cols)
    else:
        kb.tell_breeze(r, c, rows, cols)
    if 'Stench' not in percepts:
        kb.tell_no_stench(r, c, rows, cols)
    else:
        kb.tell_stench(r, c, rows, cols)

    # Update safe/danger cells
    for nr, nc in [(i,j) for i in range(rows) for j in range(cols)]:
        if kb.ask_safe(nr, nc) and [nr, nc] not in game_state['safe_cells']:
            game_state['safe_cells'].append([nr, nc])
        if kb.ask_dangerous(nr, nc) and [nr, nc] not in game_state['confirmed_danger']:
            game_state['confirmed_danger'].append([nr, nc])

def get_client_state(percepts, died=None, won=False):
    kb = game_state['kb']
    return {
        'rows': game_state['rows'],
        'cols': game_state['cols'],
        'agent': game_state['agent'],
        'visited': game_state['visited'],
        'safe_cells': game_state['safe_cells'],
        'confirmed_danger': game_state['confirmed_danger'],
        'has_gold': game_state['has_gold'],
        'game_over': game_state['game_over'],
        'win': game_state.get('win', False),
        'percepts': percepts,
        'inference_steps': kb.inference_steps,
        'kb_size': len(kb.clauses),
        'kb_facts': kb.raw_facts[-10:],
        'move_count': game_state['move_count'],
        'log': game_state['log'][-8:],
        'died': died,
        'gold': game_state['gold'],
        'pits': game_state['pits'] if game_state['game_over'] else [],
        'wumpus': game_state['wumpus'] if game_state['game_over'] else None,
    }

if __name__ == '__main__':
    app.run(debug=True, port=5000)
