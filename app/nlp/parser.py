import json
import re
import time
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from app.config import OLLAMA_HOST, OLLAMA_MODEL
from app.nlp.models import ParsedCommand
from app.nlp.prompts import SYSTEM_PROMPT


def parse_size_string(size_str: str) -> Optional[int]:
    if not size_str:
        return None
    size_str = size_str.strip().upper()
    match = re.match(r"^(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB)$", size_str)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2)
    multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    return int(value * multipliers.get(unit, 1))


def parse_time_string(time_str: str) -> Optional[float]:
    if not time_str:
        return None
    time_str = time_str.strip().lower()
    match = re.match(r"^(\d+)\s*(d|w|m|y|days?|weeks?|months?|years?)$", time_str)
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2)
    seconds_map = {
        "d": 86400, "day": 86400, "days": 86400,
        "w": 604800, "week": 604800, "weeks": 604800,
        "m": 2592000, "month": 2592000, "months": 2592000,
        "y": 31536000, "year": 31536000, "years": 31536000,
    }
    offset = value * seconds_map.get(unit, 86400)
    return time.time() - offset


class OllamaParserThread(QThread):
    result_ready = pyqtSignal(object)  # ParsedCommand or None
    error = pyqtSignal(str)

    def __init__(self, query: str, parent=None):
        super().__init__(parent)
        self.query = query

    def run(self):
        try:
            import ollama
            client = ollama.Client(host=OLLAMA_HOST)
            response = client.chat(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": self.query},
                ],
                options={"temperature": 0.1},
            )

            content = response["message"]["content"].strip()
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if not json_match:
                self.error.emit("Could not parse LLM response as JSON")
                return

            data = json.loads(json_match.group())
            cmd = ParsedCommand(
                action=data.get("action", "search"),
                filters=data.get("filters", {}),
                target=data.get("target"),
                tag=data.get("tag"),
                raw_query=self.query,
            )
            self.result_ready.emit(cmd)

        except ImportError:
            self.error.emit("Ollama package not installed. Run: pip install ollama")
        except Exception as e:
            error_msg = str(e)
            if "connection" in error_msg.lower() or "refused" in error_msg.lower():
                self.error.emit("Cannot connect to Ollama. Make sure 'ollama serve' is running.")
            else:
                self.error.emit(f"NLP Error: {error_msg}")


def check_ollama_connection() -> tuple[bool, str]:
    try:
        import ollama
        client = ollama.Client(host=OLLAMA_HOST)
        models = client.list()
        model_names = [m.get("name", m.get("model", "")) for m in models.get("models", [])]

        has_model = any(OLLAMA_MODEL in name for name in model_names)
        if has_model:
            return True, f"Connected. Model '{OLLAMA_MODEL}' available."
        else:
            available = ", ".join(model_names[:5]) if model_names else "none"
            return False, f"Connected but model '{OLLAMA_MODEL}' not found. Available: {available}. Run: ollama pull {OLLAMA_MODEL}"
    except ImportError:
        return False, "Ollama package not installed. Run: pip install ollama"
    except Exception as e:
        return False, f"Cannot connect to Ollama: {e}"
