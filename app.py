import os
import time
from flask import Flask, jsonify, request
from flask_cors import CORS
import generator
import analytics

app = Flask(__name__)

# In production (Render), set ALLOWED_ORIGINS to your real frontend domain(s), comma-separated.
# Example: ALLOWED_ORIGINS=https://mas-miami.com,https://www.mas-miami.com
# Left unset (defaults to "*"), CORS stays wide open — fine for local dev, not for production.
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
CORS(app, origins=allowed_origins)

@app.route('/api/generate', methods=['GET'])
def generate_api():
    target_topic = request.args.get('topic', 'General')
    target_difficulty = request.args.get('difficulty', 'medium').lower()
    if target_difficulty not in ('easy', 'medium', 'hard'):
        target_difficulty = 'medium'
    exclude_str = request.args.get('exclude', '')
    
    # Extraemos la lista de IDs que el jugador ya resolvió en partidas anteriores
    exclude_ids = []
    if exclude_str:
        try:
            exclude_ids = [int(x) for x in exclude_str.split(',') if x.strip().isdigit()]
        except ValueError:
            pass
            
    print(f"🌐 Request: {target_topic} - {target_difficulty} | Excluyendo {len(exclude_ids)} palabras.")

    t0 = time.monotonic()
    resultado = generator.generate_crossword(
        topic=target_topic,
        difficulty=target_difficulty,
        exclude_ids=exclude_ids
    )

    # Solo se registra si el frontend manda su anon_id (excluye bots y llamadas sueltas)
    anon_id = analytics.clean_anon_id(request.args.get('aid'))
    if anon_id:
        analytics.log_event(
            'generate',
            anon_id=anon_id,
            logged_in=request.args.get('li') == '1',
            topic=target_topic,
            difficulty=target_difficulty,
            success=bool(resultado),
            words_placed=resultado['count'] if resultado else 0,
            duration_ms=int((time.monotonic() - t0) * 1000)
        )

    if resultado:
        return jsonify({
            "success": True,
            "count": resultado['count'],
            "placed_words": resultado['placed_words'],
            "grid": resultado['grid']
        }), 200
    else:
        return jsonify({
            "success": False,
            "message": f"Could not generate a board for topic '{target_topic}'."
        }), 500

@app.route('/api/available', methods=['GET'])
def available_api():
    availability = generator.get_availability()
    # La página llama a este endpoint una vez al cargar: cuenta como visita.
    # El keep-alive (cron) no manda 'aid', así que no se registra.
    anon_id = analytics.clean_anon_id(request.args.get('aid'))
    if anon_id:
        analytics.log_event(
            'visit',
            anon_id=anon_id,
            logged_in=request.args.get('li') == '1',
            ref_host=analytics.clean_host(request.args.get('ref'))
        )
    if availability is not None:
        return jsonify({"success": True, "availability": availability}), 200
    else:
        return jsonify({"success": False, "message": "DB Error"}), 500

if __name__ == '__main__':
    # FLASK_DEBUG must be explicitly set to "true" to enable the interactive debugger.
    # Safe by default even if this file is ever run directly on a reachable machine.
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    print(f"🌍 API Server running. Listening on http://localhost:5000 (debug={debug_mode})")
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
