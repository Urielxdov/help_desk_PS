"""
Clasificador de tickets — Fase 1: reglas por palabras clave.

En Fase 2 se reemplaza el método classify() con una llamada a LLM o
un modelo entrenado con los datos acumulados. La interfaz no cambia.
"""
from dataclasses import dataclass, field


@dataclass
class ClassificationResult:
    category: str
    priority: str
    confidence: float           # 0.0 – 1.0
    method: str = 'keyword'


# Categorías y prioridades por defecto (sobrescritas por settings si existen)
_DEFAULT_CATEGORIES = {
    'infrastructure': [
        'servidor', 'server', 'red', 'network', 'vpn', 'firewall',
        'internet', 'wifi', 'storage', 'almacenamiento', 'nube', 'cloud',
    ],
    'software': [
        'aplicacion', 'aplicación', 'error', 'falla', 'crash', 'instalar',
        'actualizar', 'licencia', 'software', 'programa', 'sistema',
    ],
    'hardware': [
        'impresora', 'teclado', 'mouse', 'monitor', 'equipo', 'computadora',
        'laptop', 'telefono', 'teléfono', 'escaner', 'escáner',
    ],
    'access': [
        'contraseña', 'password', 'acceso', 'permiso', 'usuario', 'cuenta',
        'bloqueo', 'login', 'sesion', 'sesión', 'autenticacion',
    ],
    'other': [],
}

_DEFAULT_PRIORITIES = {
    'critical': [
        'caido', 'caída', 'urgente', 'produccion', 'producción',
        'todos', 'bloqueado', 'sin servicio',
    ],
    'high': [
        'lento', 'intermitente', 'degradado', 'varios usuarios',
    ],
    'medium': [
        'problema', 'falla', 'no funciona',
    ],
    'low': [
        'pregunta', 'solicitud', 'como', 'cómo', 'informacion',
    ],
}


class HelpDeskClassifier:
    def __init__(self, categories: dict = None, priorities: dict = None):
        try:
            from django.conf import settings
            self._categories = categories or getattr(settings, 'CLASSIFIER_CATEGORIES', _DEFAULT_CATEGORIES)
            self._priorities = priorities or getattr(settings, 'CLASSIFIER_PRIORITIES', _DEFAULT_PRIORITIES)
        except Exception:
            self._categories = categories or _DEFAULT_CATEGORIES
            self._priorities = priorities or _DEFAULT_PRIORITIES

    def classify(self, subject: str, description: str) -> ClassificationResult:
        text = self._normalize(f'{subject} {description}')
        category, cat_score = self._best_match(text, self._categories, default='other')
        priority, pri_score = self._best_match(text, self._priorities, default='medium')
        confidence = round((cat_score + pri_score) / 2, 2)
        return ClassificationResult(
            category=category,
            priority=priority,
            confidence=confidence,
        )

    @staticmethod
    def _normalize(text: str) -> str:
        import unicodedata
        nfkd = unicodedata.normalize('NFKD', text.lower())
        return ''.join(c for c in nfkd if not unicodedata.combining(c))

    @staticmethod
    def _best_match(text: str, keyword_map: dict, default: str) -> tuple[str, float]:
        scores: dict[str, float] = {}
        for label, keywords in keyword_map.items():
            if not keywords:
                continue
            hits = sum(1 for kw in keywords if kw in text)
            if hits:
                scores[label] = hits / len(keywords)
        if not scores:
            return default, 0.0
        best = max(scores, key=scores.get)
        return best, min(scores[best], 1.0)
