from django.db.models import Count

from .models import ClassificationFeedback, ServiceKeyword, UserFeedbackProfile
from .services import classify, normalize, fuzzy_match, FUZZY_THRESHOLD

WEIGHT_INCREMENT = 1
WEIGHT_DECREMENT = 1
MIN_WEIGHT = 1
MAX_WEIGHT = 10
MAX_SERVICES_FOR_NEW_KW = 2

# Trust score thresholds
TRUST_LOW_THRESHOLD = 0.25   # Por debajo de este valor: no mueve ningún peso
TRUST_HIGH_THRESHOLD = 0.80  # Por encima: delta doble (increment/decrement = 2)
MIN_SAMPLE_FOR_CONSENSUS = 5  # Mínimo de feedbacks entrenados para recalcular trust

STOPWORDS = {
    'de', 'la', 'el', 'en', 'y', 'a', 'que', 'es', 'se', 'no', 'un', 'una',
    'los', 'las', 'del', 'al', 'lo', 'por', 'con', 'para', 'su', 'me', 'mi',
    'te', 'le', 'nos', 'les', 'pero', 'si', 'ya', 'hay', 'fue', 'ser', 'con',
    'como', 'más', 'este', 'esta', 'esto', 'porque', 'cuando', 'muy', 'sin',
    'sobre', 'entre', 'has', 'the', 'and', 'or', 'not', 'can',
}


def _extract_candidates(text):
    """Extract candidate keywords from text: normalize, filter stopwords and short words."""
    text_normalized = normalize(text)
    words = text_normalized.split()
    candidates = {
        w.strip('.,;:!?()')
        for w in words
        if len(w) > 3 and w not in STOPWORDS
    }
    return candidates


def _adjust_weights(feedback, increment, decrement):
    text = feedback.problem_description
    text_normalized = normalize(text)

    if feedback.accepted and feedback.suggested_service:
        matched = [
            kw for kw in ServiceKeyword.objects.filter(service=feedback.chosen_service)
            if fuzzy_match(normalize(kw.keyword), text_normalized, FUZZY_THRESHOLD)
        ]
        for kw in matched:
            kw.weight = min(kw.weight + increment, MAX_WEIGHT)
            kw.save(update_fields=['weight'])

    elif not feedback.accepted and feedback.suggested_service:
        matched_wrong = [
            kw for kw in ServiceKeyword.objects.filter(service=feedback.suggested_service)
            if fuzzy_match(normalize(kw.keyword), text_normalized, FUZZY_THRESHOLD)
        ]
        for kw in matched_wrong:
            new_weight = kw.weight - decrement
            if new_weight < MIN_WEIGHT:
                kw.delete()
            else:
                kw.weight = new_weight
                kw.save(update_fields=['weight'])

        existing = set(
            ServiceKeyword.objects
            .filter(service=feedback.chosen_service)
            .values_list('keyword', flat=True)
        )
        candidates = _extract_candidates(text) - existing

        if candidates:
            shared_counts = (
                ServiceKeyword.objects
                .filter(keyword__in=candidates)
                .values('keyword')
                .annotate(n=Count('service', distinct=True))
            )
            too_generic = {row['keyword'] for row in shared_counts if row['n'] >= MAX_SERVICES_FOR_NEW_KW}
            candidates -= too_generic

        ServiceKeyword.objects.bulk_create([
            ServiceKeyword(service=feedback.chosen_service, keyword=normalize(c), weight=MIN_WEIGHT)
            for c in candidates
        ], ignore_conflicts=True)


def _update_trust_scores(user_ids):
    """
    Recalcula trust_score por consenso para los usuarios del batch.

    Compara el comportamiento de cada usuario contra la mayoría: si la mayoría
    acepta una sugerencia y el usuario la rechaza (o vice versa) consistentemente,
    su trust_score baja. El decaimiento es asimétrico (más rápido que la recuperación)
    para ser conservador contra gaming.
    """
    # Una sola query con todos los feedbacks entrenados y no rate_limited con sugerencia
    all_feedbacks = list(
        ClassificationFeedback.objects
        .filter(trained=True, rate_limited=False, suggested_service__isnull=False)
        .values('suggested_service_id', 'accepted', 'user_id')
    )

    # Tasa de aceptación global por servicio sugerido (mínimo 3 votos para ser válido)
    service_votes: dict = {}
    for fb in all_feedbacks:
        sid = fb['suggested_service_id']
        if sid not in service_votes:
            service_votes[sid] = {'accepted': 0, 'total': 0}
        service_votes[sid]['total'] += 1
        if fb['accepted']:
            service_votes[sid]['accepted'] += 1

    service_majority_accepts = {
        sid: votes['accepted'] / votes['total'] >= 0.5
        for sid, votes in service_votes.items()
        if votes['total'] >= 3
    }

    # Alineación de cada usuario del batch contra el consenso
    user_stats: dict = {uid: {'aligned': 0, 'total': 0} for uid in user_ids}
    for fb in all_feedbacks:
        uid = fb['user_id']
        if uid not in user_stats:
            continue
        sid = fb['suggested_service_id']
        if sid not in service_majority_accepts:
            continue
        user_stats[uid]['total'] += 1
        if service_majority_accepts[sid] == fb['accepted']:
            user_stats[uid]['aligned'] += 1

    profiles = {p.user_id: p for p in UserFeedbackProfile.objects.filter(user_id__in=user_ids)}
    for uid, stats in user_stats.items():
        if stats['total'] < MIN_SAMPLE_FOR_CONSENSUS:
            continue
        profile = profiles.get(uid)
        if not profile:
            continue

        alignment_rate = stats['aligned'] / stats['total']
        old_trust = profile.trust_score

        # EMA asimétrica: el trust cae más rápido de lo que sube
        if alignment_rate < old_trust:
            new_trust = old_trust * 0.7 + alignment_rate * 0.3
        else:
            new_trust = old_trust * 0.9 + alignment_rate * 0.1

        profile.trust_score = round(max(0.1, min(1.0, new_trust)), 4)
        profile.save(update_fields=['trust_score'])


def run_training():
    """Procesa feedbacks pendientes y ajusta pesos según confianza del usuario."""
    pending = list(
        ClassificationFeedback.objects
        .filter(trained=False, rate_limited=False)
        .select_related('suggested_service', 'chosen_service')
    )

    if not pending:
        return 0

    # Cargar perfiles de todos los usuarios del batch en una sola query (evita N+1)
    user_ids_in_batch = {fb.user_id for fb in pending if fb.user_id is not None}
    profiles = {
        p.user_id: p
        for p in UserFeedbackProfile.objects.filter(user_id__in=user_ids_in_batch)
    }

    processed_user_ids = set()
    count = 0

    for feedback in pending:
        uid = feedback.user_id
        profile = profiles.get(uid) if uid is not None else None
        trust = profile.trust_score if profile else 0.5

        # Usuarios bloqueados: marcar como entrenado sin mover ningún peso
        if profile and profile.flagged:
            feedback.trained = True
            feedback.save(update_fields=['trained'])
            continue

        # Trust muy bajo: el feedback existe pero no influye en los pesos
        if trust <= TRUST_LOW_THRESHOLD:
            feedback.trained = True
            feedback.save(update_fields=['trained'])
            continue

        # Delta escalado por nivel de confianza
        increment = 2 if trust >= TRUST_HIGH_THRESHOLD else WEIGHT_INCREMENT
        decrement = 2 if trust >= TRUST_HIGH_THRESHOLD else WEIGHT_DECREMENT

        _adjust_weights(feedback, increment, decrement)
        feedback.trained = True
        feedback.save(update_fields=['trained'])
        count += 1

        if uid is not None:
            processed_user_ids.add(uid)

    if processed_user_ids:
        _update_trust_scores(processed_user_ids)

    return count
