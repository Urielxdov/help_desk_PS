from .models import ClassificationFeedback, ServiceKeyword
from .services import classify

WEIGHT_INCREMENT = 1
WEIGHT_DECREMENT = 1
MIN_WEIGHT = 1
MAX_WEIGHT = 10

STOPWORDS = {
    'de', 'la', 'el', 'en', 'y', 'a', 'que', 'es', 'se', 'no', 'un', 'una',
    'los', 'las', 'del', 'al', 'lo', 'por', 'con', 'para', 'su', 'me', 'mi',
    'te', 'le', 'nos', 'les', 'pero', 'si', 'ya', 'hay', 'fue', 'ser', 'con',
    'como', 'más', 'este', 'esta', 'esto', 'porque', 'cuando', 'muy', 'sin',
    'sobre', 'entre', 'has', 'the', 'and', 'or', 'not', 'can',
}


def _extract_candidates(text):
    words = text.lower().split()
    return {w.strip('.,;:!?()') for w in words if len(w) > 3 and w not in STOPWORDS}


def _adjust_weights(feedback):
    text = feedback.problem_description

    if feedback.accepted and feedback.suggested_service:
        # Keywords that matched → increase weight
        matched = [
            kw for kw in ServiceKeyword.objects.filter(service=feedback.chosen_service)
            if kw.keyword in text.lower()
        ]
        for kw in matched:
            kw.weight = min(kw.weight + WEIGHT_INCREMENT, MAX_WEIGHT)
            kw.save(update_fields=['weight'])

    elif not feedback.accepted and feedback.suggested_service:
        # Keywords that matched wrong service → decrease weight
        matched_wrong = [
            kw for kw in ServiceKeyword.objects.filter(service=feedback.suggested_service)
            if kw.keyword in text.lower()
        ]
        for kw in matched_wrong:
            new_weight = kw.weight - WEIGHT_DECREMENT
            if new_weight < MIN_WEIGHT:
                kw.delete()
            else:
                kw.weight = new_weight
                kw.save(update_fields=['weight'])

        # Extract new keyword candidates for the chosen service
        existing = set(
            ServiceKeyword.objects
            .filter(service=feedback.chosen_service)
            .values_list('keyword', flat=True)
        )
        candidates = _extract_candidates(text) - existing
        ServiceKeyword.objects.bulk_create([
            ServiceKeyword(service=feedback.chosen_service, keyword=c, weight=MIN_WEIGHT)
            for c in candidates
        ], ignore_conflicts=True)


def run_training():
    """Procesa todos los feedbacks no entrenados y ajusta pesos."""
    pending = ClassificationFeedback.objects.filter(trained=False).select_related(
        'suggested_service', 'chosen_service'
    )
    count = pending.count()
    for feedback in pending:
        _adjust_weights(feedback)
        feedback.trained = True
        feedback.save(update_fields=['trained'])
    return count
