from domains.help_desk.classifier import HelpDeskClassifier


def clf():
    return HelpDeskClassifier()


def test_classify_infrastructure():
    result = clf().classify('VPN no conecta', 'No puedo acceder a la VPN desde casa')
    assert result.category == 'infrastructure'
    assert result.method == 'keyword'


def test_classify_access():
    result = clf().classify('Contraseña bloqueada', 'Mi cuenta está bloqueada, necesito resetear mi password')
    assert result.category == 'access'


def test_classify_hardware():
    result = clf().classify('Impresora no funciona', 'La impresora del área no imprime')
    assert result.category == 'hardware'


def test_classify_critical_priority():
    result = clf().classify('Sistema caído', 'El sistema de producción está completamente caído, urgente')
    assert result.priority == 'critical'


def test_classify_unknown_returns_defaults():
    result = clf().classify('xyz', 'abc')
    assert result.category in ('other', 'infrastructure', 'software', 'hardware', 'access')
    assert result.priority in ('low', 'medium', 'high', 'critical')
    assert 0.0 <= result.confidence <= 1.0


def test_confidence_range():
    result = clf().classify('Red caída en producción', 'El servidor principal está caído')
    assert 0.0 <= result.confidence <= 1.0


def test_normalize_accents():
    # "caída" debe matchear aunque tenga acento
    result = clf().classify('Sistema caída', 'producción bloqueada')
    assert result.priority == 'critical'
