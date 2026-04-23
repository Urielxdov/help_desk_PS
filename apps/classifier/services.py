import unicodedata
from difflib import SequenceMatcher
from django.db.models import Count
from .models import ServiceKeyword

MIN_SCORE = 0.5  # Lowered for fuzzy + IDF scoring
TOP_N = 3
FUZZY_THRESHOLD = 0.85  # 85% similarity for fuzzy matching


def normalize(text):
    """Remove accents and convert to lowercase."""
    nfkd_form = unicodedata.normalize('NFKD', text.lower().strip())
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])


def fuzzy_match(keyword, text, threshold=FUZZY_THRESHOLD):
    """Check if keyword matches text with fuzzy matching."""
    text_words = text.split()
    for word in text_words:
        similarity = SequenceMatcher(None, keyword, word).ratio()
        if similarity >= threshold:
            return True
    return False


def classify(text):
    """
    Clasifica texto contra los keywords registrados.

    Normaliza el texto y keywords (remueve acentos), luego busca
    usando fuzzy matching para tolerar errores ortográficos.
    Acumula el weight por servicio usando IDF: weight / num_services_with_keyword.
    Devuelve los top TOP_N servicios ordenados por score descendente.

    Retorna lista de dicts: [{'service_id', 'service_name', 'score'}, ...]
    """
    text_normalized = normalize(text)

    keywords = (
        ServiceKeyword.objects
        .select_related('service__category__department')
        .filter(service__active=True)
    )

    # Build IDF map: count how many services have each keyword
    keyword_service_counts = (
        ServiceKeyword.objects
        .filter(service__active=True)
        .values('keyword')
        .annotate(n=Count('service', distinct=True))
    )
    idf_map = {row['keyword']: row['n'] for row in keyword_service_counts}

    scores = {}
    for kw in keywords:
        keyword_normalized = normalize(kw.keyword)
        if fuzzy_match(keyword_normalized, text_normalized, FUZZY_THRESHOLD):
            sid = kw.service_id
            if sid not in scores:
                scores[sid] = {'service': kw.service, 'score': 0}
            # IDF: divide weight by number of services that have this keyword
            n_services = idf_map.get(kw.keyword, 1)
            scores[sid]['score'] += kw.weight / n_services

    results = [
        {
            'service_id': sid,
            'service_name': data['service'].name,
            'category_id': data['service'].category_id,
            'category_name': data['service'].category.name,
            'department_id': data['service'].category.department_id,
            'department_name': data['service'].category.department.name,
            'score': data['score'],
        }
        for sid, data in scores.items()
        if data['score'] >= MIN_SCORE
    ]

    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:TOP_N]
