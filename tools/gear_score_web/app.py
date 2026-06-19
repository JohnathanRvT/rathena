from flask import Flask, render_template, request, jsonify
import os
import json
from item_db_loader import load_item_db

app = Flask(__name__)

# Attempt to find rAthena root directory
def get_rathena_root():
    current = os.path.dirname(os.path.abspath(__file__))
    while current != os.path.dirname(current):
        if os.path.exists(os.path.join(current, 'conf', 'inter_athena.conf')):
            return current
        current = os.path.dirname(current)
    return "."

RATHENA_ROOT = get_rathena_root()
item_db = load_item_db(RATHENA_ROOT)

@app.route('/')
def simulator():
    return render_template('simulator.html')

@app.route('/api/items/search')
def search_items():
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])

    results = []
    for item_id, info in item_db.items():
        if query in info['name'].lower() or query == str(item_id):
            results.append({
                'id': item_id,
                'name': info['name'],
                'atk': info['atk'],
                'matk': info['matk'],
                'def': info['def'],
                'wlv': info['wlv'],
                'alv': info['alv']
            })
            if len(results) >= 10:
                break

    return jsonify(results)

@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.json
    total_score = 0
    breakdown = []

    for slot, item in data.items():
        item_id = item.get('id')
        if not item_id or item_id not in item_db:
            continue

        info = item_db[item_id]
        refine = item.get('refine', 0)
        cards = item.get('cards', [])

        score = 0
        # Base score from item level
        score += (info.get('wlv', 0) + info.get('alv', 0)) * 100
        # Stat bonuses
        score += info.get('atk', 0)
        score += info.get('def', 0) * 5
        score += info.get('matk', 0)

        # Refine bonus
        if refine > 0:
            score += (refine * refine) * 10

        # Card bonus
        for card_id in cards:
            if card_id and card_id != 0:
                score += 50

        total_score += score
        breakdown.append({
            'slot': slot,
            'name': info['name'],
            'score': score
        })

    return jsonify({
        'total_score': total_score,
        'breakdown': breakdown
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
