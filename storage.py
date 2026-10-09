"""High-score persistence (works on desktop and inside the Android sandbox)."""
import os


def load_high_score(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def save_high_score(path, score):
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(int(score)))
    except OSError:
        pass
