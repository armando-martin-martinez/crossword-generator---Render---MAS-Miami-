import os
import random
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def print_board(grid):
    print("\n")
    for row in grid:
        linea = " ".join(row).replace(".", "⬛")
        print(linea)
    print("\n")

def can_place_word(grid, word, row, col, direction):
    size = len(grid)
    if row < 0 or col < 0: return False
    if direction == "H" and col + len(word) > size: return False
    if direction == "V" and row + len(word) > size: return False

    if direction == "H":
        if col - 1 >= 0 and grid[row][col-1] != ".": return False
        if col + len(word) < size and grid[row][col+len(word)] != ".": return False
    elif direction == "V":
        if row - 1 >= 0 and grid[row-1][col] != ".": return False
        if row + len(word) < size and grid[row+len(word)][col] != ".": return False

    for i, char in enumerate(word):
        r = row if direction == "H" else row + i
        c = col + i if direction == "H" else col
        if grid[r][c] != "." and grid[r][c] != char: return False
        if grid[r][c] == ".":
            if direction == "H":
                if r - 1 >= 0 and grid[r-1][c] != ".": return False
                if r + 1 < size and grid[r+1][c] != ".": return False
            elif direction == "V":
                if c - 1 >= 0 and grid[r][c-1] != ".": return False
                if c + 1 < size and grid[r][c+1] != ".": return False
    return True

def count_intersections(grid, word, row, col, direction):
    """Cuenta cuántas letras de la nueva palabra cruzan con palabras existentes."""
    intersections = 0
    for i in range(len(word)):
        r = row if direction == "H" else row + i
        c = col + i if direction == "H" else col
        if grid[r][c] != ".":
            intersections += 1
    return intersections

def place_word(grid, word, row, col, direction):
    for i, char in enumerate(word):
        r = row if direction == "H" else row + i
        c = col + i if direction == "H" else col
        grid[r][c] = char

def place_word_tracked(grid, word, row, col, direction):
    modified = []
    for i, char in enumerate(word):
        r = row if direction == "H" else row + i
        c = col + i if direction == "H" else col
        if grid[r][c] == ".":
            grid[r][c] = char
            modified.append((r, c, "."))
    return modified

def remove_word_tracked(grid, modified):
    for r, c, old_val in modified:
        grid[r][c] = old_val

def get_all_valid_positions(word, grid, placed_words):
    candidates = set()
    for p_word_obj in placed_words:
        p_word = p_word_obj['word']
        p_r = p_word_obj['row']
        p_c = p_word_obj['col']
        p_dir = p_word_obj['dir']

        for i, char in enumerate(word):
            for j, p_char in enumerate(p_word):
                if char == p_char:
                    new_dir = "V" if p_dir == "H" else "H"
                    new_r = p_r - i if new_dir == "V" else p_r + j
                    new_c = p_c + j if new_dir == "V" else p_c - i

                    if can_place_word(grid, word, new_r, new_c, new_dir):
                        candidates.add((new_r, new_c, new_dir))
    
    # HEURÍSTICA DE GRAVEDAD: Puntuamos los candidatos por densidad (intersecciones)
    scored_candidates = []
    for r, c, d in candidates:
        score = count_intersections(grid, word, r, c, d)
        scored_candidates.append((score, r, c, d))
        
    score_groups = {}
    for sc, r, c, d in scored_candidates:
        score_groups.setdefault(sc, []).append((r, c, d))
        
    final_candidates = []
    # Retornamos los candidatos ordenados (los de más puntaje primero)
    for sc in sorted(score_groups.keys(), reverse=True):
        group = score_groups[sc]
        random.shuffle(group)
        final_candidates.extend(group)
        
    return final_candidates

def backtrack(remaining_words, grid, placed_words, best_result, search_state, target_max):
    search_state['nodes_visited'] += 1
    
    if len(placed_words) > best_result['count']:
        best_result['count'] = len(placed_words)
        best_result['placed_words'] = list(placed_words)
        best_result['grid'] = [row[:] for row in grid]
        
    if best_result['count'] >= target_max:
        return True 

    if search_state['nodes_visited'] > search_state['max_nodes']: return False
    if not remaining_words: return False

    word_candidates = {}
    for w in remaining_words:
        cands = get_all_valid_positions(w, grid, placed_words)
        if cands:
            word_candidates[w] = cands
            
    if not word_candidates: return False
    
    valid_words = [w for w in remaining_words if w in word_candidates]
    
    # NUEVO ALGORITMO INTELIGENTE: Mezclamos para no forzar siempre la palabra más larga
    random.shuffle(valid_words)
    
    # Exploramos hasta 4 palabras diferentes en esta rama (evita quedarse atascado en una)
    for best_word in valid_words[:4]: 
        candidates = word_candidates[best_word]
        rest = [w for w in remaining_words if w != best_word]

        # PODA (PRUNING): Tomamos solo las 5 mejores posiciones para no gastar los "max_nodes"
        for row, col, direction in candidates[:5]:
            modified = place_word_tracked(grid, best_word, row, col, direction)
            placed_words.append({'word': best_word, 'row': row, 'col': col, 'dir': direction})
            
            done = backtrack(rest, grid, placed_words, best_result, search_state, target_max)
            
            remove_word_tracked(grid, modified)
            placed_words.pop()
            
            if done: return True
            # Si se acaba el presupuesto de nodos, abortamos completamente esta búsqueda
            if search_state['nodes_visited'] > search_state['max_nodes']: 
                return False

    return False

def generate_crossword(topic='Science', difficulty='medium', exclude_ids=None):
    if exclude_ids is None: exclude_ids = []
    
    config_dificultad = {
        'easy': {'min': 17, 'max': 20, 'grid_size': 20, 'max_nodes': 8000},
        'medium': {'min': 25, 'max': 30, 'grid_size': 25, 'max_nodes': 8000},
        'hard': {'min': 35, 'max': 40, 'grid_size': 30, 'max_nodes': 8000}
    }
    
    ajustes = config_dificultad.get(difficulty.lower(), config_dificultad['medium'])
    min_palabras = ajustes['min']
    max_palabras = ajustes['max']
    size = ajustes['grid_size']
    
    best_result = {'placed_words': [], 'grid': None, 'count': 0}
    grid = [["." for _ in range(size)] for _ in range(size)]
    placed_words = []
    metadata_map = {}
    
    current_exclude_ids = list(exclude_ids)
    max_retries = 3
    
    try:
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        for attempt in range(max_retries):
            print(f"🔄 Motor intentando inyectar datos (Piscina: 100 palabras) - Intento {attempt + 1}...")
            
            query_base = """
                SELECT DISTINCT ON (w.id) w.id AS word_id, w.word, c.clue, def.definition
                FROM words w
                JOIN clues c ON c.word_id = w.id
                JOIN word_categories wc ON wc.word_id = w.id
                JOIN categories cat ON cat.id = wc.category_id
                LEFT JOIN definitions def ON def.word_id = w.id
                WHERE LOWER(cat.name) = LOWER(%s)
                  AND c.difficulty = %s
                  AND c.approved = TRUE
                  AND w.is_allowed = TRUE
            """
            params = [topic.strip(), difficulty.lower()]
            if current_exclude_ids:
                query_base += " AND w.id <> ALL(%s::int[])"
                params.append(current_exclude_ids)
                
            query = f"SELECT word, clue, definition, word_id FROM ({query_base} ORDER BY w.id, RANDOM()) sub ORDER BY RANDOM() LIMIT 100;"
            
            cur.execute(query, params)
            db_data = cur.fetchall()
            
            if not db_data: 
                print("⚠️ No hay más palabras en la Base de Datos para este tema.")
                break
                
            for row in db_data:
                current_exclude_ids.append(row[3])
                metadata_map[row[0]] = {
                    'clue': row[1] if row[1] else "No clue provided.",
                    'definition': row[2] if row[2] else "No dictionary definition available for this word.",
                    'id': row[3]
                }
                
            # Mantenemos esto para que la primera palabra (ancla) sea larga, pero luego el backtrack ya es aleatorio
            db_data.sort(key=lambda x: len(x[0]), reverse=True)
            words = [row[0] for row in db_data]
            
            placed_word_strings = set(pw['word'] for pw in best_result['placed_words'])
            remaining_words = [w for w in words if w not in placed_word_strings]
            
            if not best_result['placed_words'] and remaining_words:
                first_word = remaining_words.pop(0)
                start_dir = random.choice(["H", "V"])
                start_r = (size // 2) + random.randint(-1, 1)
                start_c = (size // 2) - (len(first_word) // 2) + random.randint(-1, 1)
                
                start_r = max(0, min(start_r, size - (len(first_word) if start_dir == "V" else 1)))
                start_c = max(0, min(start_c, size - (len(first_word) if start_dir == "H" else 1)))

                place_word(grid, first_word, start_r, start_c, start_dir)
                placed_words.append({'word': first_word, 'row': start_r, 'col': start_c, 'dir': start_dir})
                best_result['count'] = 1
                best_result['placed_words'] = list(placed_words)
                best_result['grid'] = [row[:] for row in grid]

            search_state = {'nodes_visited': 0, 'max_nodes': ajustes['max_nodes']}
            grid_copy = [row[:] for row in best_result['grid']]
            placed_words_copy = list(best_result['placed_words'])
            
            backtrack(remaining_words, grid_copy, placed_words_copy, best_result, search_state, target_max=max_palabras)
            
            if best_result['count'] >= min_palabras:
                print(f"✅ ¡Éxito! Alcanzó el margen de tolerancia con {best_result['count']} palabras.")
                break
            else:
                print(f"⚠️ Se atascó en {best_result['count']} palabras. Solicitando nueva inyección de datos a la BD...")

        cur.close()
        conn.close()
    except Exception as e:
        print("❌ DB Error:", e)
        return None

    # VALIDACIÓN FINAL CORREGIDA: Si después de todos los intentos no cumple el mínimo, falla elegantemente.
    if best_result['grid'] and best_result['count'] >= min_palabras:
        min_r = min(obj['row'] for obj in best_result['placed_words'])
        max_r = max((obj['row'] + len(obj['word']) - 1) if obj['dir'] == 'V' else obj['row'] for obj in best_result['placed_words'])
        min_c = min(obj['col'] for obj in best_result['placed_words'])
        max_c = max((obj['col'] + len(obj['word']) - 1) if obj['dir'] == 'H' else obj['col'] for obj in best_result['placed_words'])
        
        min_r, max_r = max(0, min_r - 1), min(size - 1, max_r + 1)
        min_c, max_c = max(0, min_c - 1), min(size - 1, max_c + 1)

        cropped_grid = []
        for r in range(min_r, max_r + 1):
            cropped_grid.append(best_result['grid'][r][min_c:max_c + 1])
            
        best_result['grid'] = cropped_grid

        start_positions = {}
        for obj in best_result['placed_words']:
            obj['row'] -= min_r
            obj['col'] -= min_c
            meta = metadata_map[obj['word']]
            obj['clue'] = meta['clue']
            obj['definition'] = meta['definition']
            obj['id'] = meta['id']
            pos = (obj['row'], obj['col'])
            if pos not in start_positions: start_positions[pos] = []
            start_positions[pos].append(obj)
            
        sorted_positions = sorted(start_positions.keys(), key=lambda p: (p[0], p[1]))
        
        current_number = 1
        for pos in sorted_positions:
            for obj in start_positions[pos]:
                obj['number'] = current_number
            current_number += 1

        return best_result
    else:
        # Devuelve None si no logró el mínimo, permitiendo que la app.py y el front-end manejen el reintento.
        return None

def get_availability():
    try:
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        query = """
            SELECT cat.name AS topic, cl.difficulty, COUNT(DISTINCT w.id) AS word_count
            FROM clues cl
            JOIN words w ON w.id = cl.word_id
            JOIN word_categories wc ON wc.word_id = w.id
            JOIN categories cat ON cat.id = wc.category_id
            WHERE cl.approved = TRUE AND w.is_allowed = TRUE
            GROUP BY cat.name, cl.difficulty
        """
        cur.execute(query)
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        return None

    topic_totals = {}
    for topic, difficulty, count in rows:
        topic_totals[topic] = topic_totals.get(topic, 0) + count

    MIN_TOTAL_WORDS = 50
    limites = {'easy': 17, 'medium': 25, 'hard': 35}
    availability = {}
    
    for topic, difficulty, count in rows:
        if topic_totals.get(topic, 0) < MIN_TOTAL_WORDS:
            continue
            
        dif_lower = difficulty.lower()
        availability.setdefault(topic, {})[dif_lower] = {
            "count": count,
            "sufficient": count >= limites.get(dif_lower, 17)
        }
    return availability
