from django.db import migrations


STATUS_MAP = {
    'abierto':    'open',
    'en_progreso': 'in_progress',
    'en_espera':  'on_hold',
    'resuelto':   'resolved',
    'cerrado':    'closed',
}

PRIORITY_MAP = {
    'baja':   'low',
    'media':  'medium',
    'alta':   'high',
    'critica': 'critical',
}

ORIGIN_MAP = {
    'error':         'error',
    'solicitud':     'request',
    'consulta':      'inquiry',
    'mantenimiento': 'maintenance',
}

ATTACHMENT_TYPE_MAP = {
    'archivo': 'file',
    'url':     'url',
}


def forwards(apps, schema_editor):
    HelpDesk = apps.get_model('helpdesks', 'HelpDesk')
    HDAttachment = apps.get_model('helpdesks', 'HDAttachment')

    for hd in HelpDesk.objects.all():
        changed = False
        if hd.status in STATUS_MAP:
            hd.status = STATUS_MAP[hd.status]
            changed = True
        if hd.priority in PRIORITY_MAP:
            hd.priority = PRIORITY_MAP[hd.priority]
            changed = True
        if hd.origin in ORIGIN_MAP:
            hd.origin = ORIGIN_MAP[hd.origin]
            changed = True
        if changed:
            hd.save(update_fields=['status', 'priority', 'origin'])

    for att in HDAttachment.objects.all():
        if att.type in ATTACHMENT_TYPE_MAP:
            att.type = ATTACHMENT_TYPE_MAP[att.type]
            att.save(update_fields=['type'])


def backwards(apps, schema_editor):
    reverse_status = {v: k for k, v in STATUS_MAP.items()}
    reverse_priority = {v: k for k, v in PRIORITY_MAP.items()}
    reverse_origin = {v: k for k, v in ORIGIN_MAP.items()}
    reverse_type = {v: k for k, v in ATTACHMENT_TYPE_MAP.items()}

    HelpDesk = apps.get_model('helpdesks', 'HelpDesk')
    HDAttachment = apps.get_model('helpdesks', 'HDAttachment')

    for hd in HelpDesk.objects.all():
        hd.status = reverse_status.get(hd.status, hd.status)
        hd.priority = reverse_priority.get(hd.priority, hd.priority)
        hd.origin = reverse_origin.get(hd.origin, hd.origin)
        hd.save(update_fields=['status', 'priority', 'origin'])

    for att in HDAttachment.objects.all():
        att.type = reverse_type.get(att.type, att.type)
        att.save(update_fields=['type'])


class Migration(migrations.Migration):

    dependencies = [
        ('helpdesks', '0002_rename_to_english'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
