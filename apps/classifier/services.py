from .models import ServiceKeyword

MIN_SCORE = 1
TOP_N = 3


def classify(text):
    """
    Clasifica texto contra los keywords registrados.

    Busca cada keyword en el texto (case-insensitive, substring match).
    Acumula el weight por servicio y devuelve los top TOP_N servicios
    ordenados por score descendente.

    Retorna lista de dicts: [{'service_id', 'service_name', 'score'}, ...]
    """
    text_lower = text.lower()

    keywords = (
        ServiceKeyword.objects
        .select_related('service__category__department')
        .filter(service__active=True)
    )

    scores = {}
    for kw in keywords:
        if kw.keyword in text_lower:
            sid = kw.service_id
            if sid not in scores:
                scores[sid] = {'service': kw.service, 'score': 0}
            scores[sid]['score'] += kw.weight

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
