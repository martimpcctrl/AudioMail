"""Fala pelo leitor de tela (NVDA, JAWS, etc.) usando accessible_output2, se estiver instalado."""

_output = None
_tried = False


def _get():
    global _output, _tried
    if not _tried:
        _tried = True
        try:
            import accessible_output2.outputs.auto as auto
            _output = auto.Auto()
        except Exception:
            _output = None
    return _output


def available():
    return _get() is not None


def speak(text, interrupt=False):
    """Fala o texto. Devolve True se um leitor de tela recebeu."""
    out = _get()
    if out is None:
        return False
    try:
        out.speak(text, interrupt=interrupt)
        return True
    except Exception:
        return False
