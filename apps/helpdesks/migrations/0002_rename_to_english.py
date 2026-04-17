from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('helpdesks', '0001_initial'),
        ('catalog', '0003_rename_to_english'),
    ]

    operations = [
        # HelpDesk
        migrations.RenameField('HelpDesk', 'solicitante_id', 'requester_id'),
        migrations.RenameField('HelpDesk', 'responsable_id', 'assignee_id'),
        migrations.RenameField('HelpDesk', 'origen', 'origin'),
        migrations.RenameField('HelpDesk', 'prioridad', 'priority'),
        migrations.RenameField('HelpDesk', 'estado', 'status'),
        migrations.RenameField('HelpDesk', 'descripcion_problema', 'problem_description'),
        migrations.RenameField('HelpDesk', 'descripcion_solucion', 'solution_description'),
        migrations.RenameField('HelpDesk', 'fecha_asignacion', 'assigned_at'),
        migrations.RenameField('HelpDesk', 'fecha_compromiso', 'due_date'),
        migrations.RenameField('HelpDesk', 'fecha_efectividad', 'resolved_at'),
        migrations.RenameField('HelpDesk', 'tiempo_estimado', 'estimated_hours'),
        # HDComment
        migrations.RenameField('HDComment', 'autor_id', 'author_id'),
        migrations.RenameField('HDComment', 'contenido', 'content'),
        migrations.RenameField('HDComment', 'es_interno', 'is_internal'),
        # HDAttachment
        migrations.RenameField('HDAttachment', 'tipo', 'type'),
        migrations.RenameField('HDAttachment', 'nombre', 'name'),
        migrations.RenameField('HDAttachment', 'valor', 'value'),
    ]
