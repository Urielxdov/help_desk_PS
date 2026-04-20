from celery import shared_task

from .training import run_training


@shared_task
def train_classifier():
    """Procesa feedbacks pendientes y ajusta pesos de keywords."""
    processed = run_training()
    return {'processed': processed}
