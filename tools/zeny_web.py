#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from zeny_calc import ItemDatabase, MonsterDatabase, MapSpawnDatabase, LevelPenaltyDatabase, ZenyCalculator

app = Flask(__name__)

dbs = {'re': None, 'pre-re': None}

def load_dbs(mode):
    if dbs[mode]: return dbs[mode]
    print(f"Loading {mode} databases...")
    item_db = ItemDatabase()
    for f in ['etc', 'equip', 'usable']: item_db.load_from_yml(f'db/{mode}/item_db_{f}.yml')
    mob_db = MonsterDatabase()
    mob_db.load_from_yml(f'db/{mode}/mob_db.yml')
    penalty_db = LevelPenaltyDatabase()
    if mode == 're': penalty_db.load_from_yml('db/re/level_penalty.yml')
    spawn_db = MapSpawnDatabase()
    spawn_db.load_from_conf(f'npc/{mode}/scripts_monsters.conf')
    dbs[mode] = (item_db, mob_db, spawn_db, penalty_db)
    return dbs[mode]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/calculate')
def calculate():
    mode = 'pre-re' if request.args.get('pre_re') == 'true' else 're'
    item_db, mob_db, spawn_db, penalty_db = load_dbs(mode)
    calc = ZenyCalculator(item_db, mob_db, spawn_db, penalty_db, mode == 'pre-re')

    char_stats = {
        'level': int(request.args.get('char_level', 100)),
        'atk': int(request.args.get('atk', 200)),
        'hit': int(request.args.get('hit', 300)),
        'aspd': int(request.args.get('aspd', 180)),
        'flee': int(request.args.get('flee', 0))
    }

    base_drop_rate = int(request.args.get('base_drop_rate', 1))
    base_exp_rate = int(request.args.get('base_exp_rate', 1))
    oc_level = int(request.args.get('oc', 10))
    gum = request.args.get('gum') == 'on'
    exp_boost = 150 if request.args.get('manual') == 'on' else 100
    job_exp_boost = 150 if request.args.get('job_manual') == 'on' else 100
    optimize_for = request.args.get('optimize_for', 'zeny')

    mobs = calc.rank_mobs(
        char_stats,
        base_drop_rate=base_drop_rate,
        base_exp_rate=base_exp_rate,
        oc_level=oc_level,
        gum=gum,
        exp_boost=exp_boost,
        job_exp_boost=job_exp_boost,
        optimize_for=optimize_for
    )

    maps = calc.rank_maps(
        char_stats,
        base_drop_rate=base_drop_rate,
        base_exp_rate=base_exp_rate,
        oc_level=oc_level,
        gum=gum,
        exp_boost=exp_boost,
        job_exp_boost=job_exp_boost
    )

    return jsonify({
        'mobs': mobs[:50],
        'maps': maps[:50]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
