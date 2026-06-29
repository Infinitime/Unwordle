import csv
from collections import Counter
# Note: wordfreq is imported but not used directly in this script, leaving it in case you use it elsewhere.
from wordfreq import word_frequency


def load_words(filepath: str) -> list[str]:
    """
    Load words directly from the frequencies CSV file to eliminate guesses.txt.
    This ensures both datasets stay perfectly synchronized in memory.
    """
    words = []
    try:
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 1:
                    continue
                word = row[0].strip().lower()
                # Skip header row if present, or any rows that aren't exactly 5 letters
                if word == "word" or len(word) != 5:
                    continue
                words.append(word)
    except FileNotFoundError:
        print(f"⚠️ Warning: '{filepath}' not found when trying to build word list.")
    return words


def load_frequencies(filepath: str) -> dict[str, int]:
    """
    Load word frequencies from a CSV file containing 'word,count'.
    Handles optional headers automatically.
    """
    freqs = {}
    try:
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 2:
                    continue
                # Skip header row if present
                if row[0].strip().lower() == "word":
                    continue
                try:
                    word = row[0].strip().lower()
                    count = int(row[1].strip())
                    freqs[word] = count
                except ValueError:
                    continue
    except FileNotFoundError:
        print(f"⚠️ Warning: '{filepath}' not found. Falling back to 0 for all frequencies.")
    return freqs


def score_guess(guess: str, answer: str) -> list[str]:
    """
    Score a guess against the answer.
    Returns a list of 5 colors: 'green', 'yellow', or 'gray'.
    """
    result = ["gray"] * 5
    answer_chars = list(answer)

    # First pass: find greens
    for i, (g, a) in enumerate(zip(guess, answer)):
        if g == a:
            result[i] = "green"
            answer_chars[i] = None  # Mark as used

    # Second pass: find yellows
    for i, g in enumerate(guess):
        if result[i] == "green":
            continue
        if g in answer_chars:
            result[i] = "yellow"
            answer_chars[answer_chars.index(g)] = None  # Mark as used

    return result


def filter_candidates(candidates: list[str], guess: str, feedback: list[str]) -> list[str]:
    """Filter the candidate word list based on guess + feedback."""
    def is_consistent(word: str) -> bool:
        for i, (letter, color) in enumerate(zip(guess, feedback)):
            if color == "green":
                if word[i] != letter:
                    return False
            elif color == "yellow":
                if letter not in word:
                    return False
                if word[i] == letter:
                    return False
            elif color == "gray":
                green_yellow_count = sum(
                    1 for j, (l, c) in enumerate(zip(guess, feedback))
                    if l == letter and c in ("green", "yellow")
                )
                if word.count(letter) > green_yellow_count:
                    return False
        return True

    return [word for word in candidates if is_consistent(word)]


def best_guesses(candidates: list[str], all_words: list[str], frequencies: dict[str, int], top_n: int = 3) -> list[str]:
    """
    Pick the top N next guesses prioritizing the highest usage count from the CSV.
    """
    if len(candidates) <= 2:
        return sorted(candidates, key=lambda w: frequencies.get(w, 0), reverse=True)[:top_n]

    # Count letter distribution density across the remaining valid options
    freq = Counter()
    for word in candidates:
        freq.update(set(word))

    def score_word(word: str) -> tuple:
        unique_letters = set(word)
        letter_score = sum(freq[ch] for ch in unique_letters)
        in_candidates = word in candidates
        word_count = frequencies.get(word, 0)
        
        # FIXED: Flipped 'word_count' to come before 'letter_score'.
        # Because sorted runs with reverse=True, higher counts now take absolute priority.
        return (in_candidates, word_count, letter_score)

    # Sort all words by score descending and return the top N
    return sorted(all_words, key=score_word, reverse=True)[:top_n]


class WordleSolver:
    """Interactive Wordle solver utilizing letter structures and CSV frequencies."""

    COLORS = {"g": "green", "y": "yellow", "b": "gray"}
    OPENER = "crane"

    def __init__(self, freq_file: str):
        # Pointing both datasets directly to the frequency CSV file
        self.frequencies = load_frequencies(freq_file)
        self.all_words = load_words(freq_file)
        self.candidates = list(self.all_words)

    def reset(self):
        self.candidates = list(self.all_words)

    def parse_feedback(self, feedback_str: str) -> list[str]:
        feedback_str = feedback_str.strip().lower()
        if len(feedback_str) != 5 or not all(c in self.COLORS for c in feedback_str):
            raise ValueError("Feedback must be 5 characters: g (green), y (yellow), b (gray)")
        return [self.COLORS[c] for c in feedback_str]

    def start(self):
        print("=" * 40)
        print("       WORDLE SOLVER (FREQUENCY OPTIMIZED)")
        print("=" * 40)
        print("After each guess, enter feedback as 5 chars:")
        print("  g = green  (right letter, right spot)")
        print("  y = yellow (right letter, wrong spot)")
        print("  b = gray   (letter not in word)")
        print("Type 'quit' to exit, 'reset' to start over.\n")

        self.reset()
        attempt = 1

        while attempt <= 6:
            print(f"Candidates remaining: {len(self.candidates)}")

            if len(self.candidates) <= 10:
                sorted_candidates = sorted(
                    self.candidates, 
                    key=lambda w: self.frequencies.get(w, 0), 
                    reverse=True
                )
                print(f"  Possible words (sorted by frequency): {', '.join(sorted_candidates)}")

            if attempt == 1:
                top_options = [self.OPENER]
            else:
                top_options = best_guesses(self.candidates, self.all_words, self.frequencies, top_n=3)

            default_guess = top_options[0]

            print(f"\nAttempt {attempt}/6 — Top suggested guesses:")
            for i, g in enumerate(top_options, 1):
                print(f"  {i}. {g.upper()}")

            override = input(f"\nPress Enter to use '{default_guess.upper()}', or type your own: ").strip().lower()
            if override == "quit":
                print("Goodbye!")
                return
            if override == "reset":
                self.reset()
                attempt = 1
                print("\n--- Restarting ---\n")
                continue
            
            guess = override if override else default_guess

            while True:
                feedback_str = input(f"Enter feedback for '{guess.upper()}': ").strip()
                if feedback_str.lower() == "quit":
                    print("Goodbye!")
                    return
                try:
                    feedback = self.parse_feedback(feedback_str)
                    break
                except ValueError as e:
                    print(f"  Error: {e}")

            if all(f == "green" for f in feedback):
                print(f"\n✅ Solved in {attempt} attempt(s)! The word was {guess.upper()}.")
                return

            self.candidates = filter_candidates(self.candidates, guess, feedback)
            attempt += 1

            if not self.candidates:
                print("\n❌ No candidates left — the word may not be in the list.")
                return

            print()

        print("❌ Could not solve in 6 attempts.")


# ── Self-test (auto-play) ─────────────────────────────────────────────────────

def auto_solve(answer: str, all_words: list[str], frequencies: dict[str, int], opener: str = "crane") -> int:
    candidates = list(all_words)
    guess = opener

    for attempt in range(1, 7):
        feedback = score_guess(guess, answer)
        if all(f == "green" for f in feedback):
            return attempt
        candidates = filter_candidates(candidates, guess, feedback)
        if not candidates:
            return -1
        
        guess = best_guesses(candidates, all_words, frequencies, top_n=1)[0]

    return -1


if __name__ == "__main__":
    import sys

    freq_file = "frequencies.csv"

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        freqs = load_frequencies(freq_file)
        words = load_words(freq_file)
        test_words = words[:200]
        results = [auto_solve(w, words, freqs) for w in test_words]
        solved = [r for r in results if r != -1]
        print(f"Tested {len(test_words)} words")
        print(f"Solved: {len(solved)}/{len(test_words)}")
        print(f"Average attempts: {sum(solved)/len(solved):.2f}")
        print(f"Distribution: { {i: solved.count(i) for i in range(1,7)} }")
    else:
        solver = WordleSolver(freq_file)
        solver.start()