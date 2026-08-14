from flask import Flask, jsonify, request
from flask_cors import CORS
import generator

app = Flask(__name__)
CORS(app)

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
    
    resultado = generator.generate_crossword(
        topic=target_topic, 
        difficulty=target_difficulty,
        exclude_ids=exclude_ids
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
    if availability is not None:
        return jsonify({"success": True, "availability": availability}), 200
    else:
        return jsonify({"success": False, "message": "DB Error"}), 500

if __name__ == '__main__':
    print("🌍 API Server running. Listening on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)