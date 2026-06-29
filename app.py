from flask import Flask, render_template, request, redirect, url_for, session
import solver_backend as sb
import webbrowser
from threading import Timer
from flask import Flask, render_template, request, redirect, url_for, session
import solver_backend as sb

app = Flask(__name__)
# ... (your existing app.py setup code) ...

def open_browser():
    """Opens the local browser window automatically."""
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == "__main__":
    # Give the Flask server 1.5 seconds to start up, then launch the browser
    Timer(1.5, open_browser).start()
    
    # Run the application locally (turn off debug mode for production packaging)
    app.run(debug=False, port=5000)


app = Flask(__name__)

# Static secret key ensures session cookies remain signable
app.secret_key = "stable_wordle_solver_key_2026"
app.config['SESSION_PERMANENT'] = False

# Load the master dictionary datasets once on startup
WORDS = sb.load_words("guesses.txt")
FREQS = sb.load_frequencies("frequencies.csv")

def reset_game():
    """Wipes the session clean, forcing cookie size back to zero."""
    session.clear()
    session["history"] = []
    session.modified = True

@app.route("/", methods=["GET", "POST"])
def index():
    # Ensure history tracking initialization exists
    if "history" not in session:
        reset_game()

    error = None

    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "reset":
            reset_game()
            return redirect(url_for("index"))
            
        elif action == "submit":
            guess = request.form.get("guess", "").strip().lower()
            feedback = request.form.get("feedback", "").strip().lower()

            # Submission validations
            if len(guess) != 5 or len(feedback) != 5:
                error = "Please make sure the guess and feedback are complete."
            elif not all(c in "gyb" for c in feedback):
                error = "Feedback contains invalid characters."
            else:
                # Store ONLY small turn markers in the session cookie
                history = session.get("history", [])
                history.append({"guess": guess, "feedback": feedback})
                session["history"] = history
                session.modified = True
                return redirect(url_for("index"))

    # ── HISTORICAL RECONSTRUCTION LAYER ──
    # Re-filter the master list instantly on every page refresh using your history
    candidates = list(WORDS)
    game_over = False
    
    for turn in session.get("history", []):
        g = turn["guess"]
        f = turn["feedback"]
        
        if f == "ggggg":
            game_over = True
            
        color_list = [sb.WordleSolver.COLORS[c] for c in f]
        candidates = sb.filter_candidates(candidates, g, color_list)
        
    # Check alternate game termination flags
    if len(session.get("history", [])) >= 6 or not candidates:
        game_over = True

    # Generate recommendations based on the newly calculated candidates
    if not game_over:
        if len(session["history"]) == 0:
            top_options = [sb.WordleSolver.OPENER]
        else:
            top_options = sb.best_guesses(candidates, WORDS, FREQS, top_n=3)
    else:
        top_options = []

    # Filter down high-frequency word displays if remaining options are minimal
    possible_words = []
    if len(candidates) <= 10:
        possible_words = sorted(
            candidates, 
            key=lambda w: FREQS.get(w, 0), 
            reverse=True
        )

    return render_template(
        "index.html",
        history=session["history"],
        candidates_count=len(candidates),
        possible_words=possible_words,
        top_options=top_options,
        game_over=game_over,
        error=error
    )

if __name__ == "__main__":
    app.run(debug=True)
