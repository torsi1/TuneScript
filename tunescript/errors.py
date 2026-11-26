"""Error classes: every error has a category, line and column."""


class TuneError(Exception):
    category = "Error"

    def __init__(self, message, line=None, col=None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col

    def location(self):
        return f"{self.line}:{self.col}" if self.line else "-"

    def format(self, source=None):
        loc = f" {self.line}:{self.col}" if self.line else ""
        out = f"[{self.category}]{loc} – {self.message}"
        if source and self.line:
            lines = source.splitlines()
            if 1 <= self.line <= len(lines):
                out += "\n    " + lines[self.line - 1]
                out += "\n    " + " " * (max(self.col or 1, 1) - 1) + "^"
        return out


class LexicalError(TuneError):
    category = "Lexical error"


class SyntaxErr(TuneError):
    category = "Syntax error"


class SemanticError(TuneError):
    category = "Semantic error"
