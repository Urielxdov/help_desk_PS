from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('catalog', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HelpDesk',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('folio', models.CharField(blank=True, max_length=20, unique=True)),
                ('solicitante_id', models.IntegerField(blank=True, db_index=True, null=True)),
                ('responsable_id', models.IntegerField(blank=True, db_index=True, null=True)),
                ('origen', models.CharField(max_length=20)),
                ('prioridad', models.CharField(max_length=10)),
                ('estado', models.CharField(db_index=True, default='abierto', max_length=15)),
                ('descripcion_problema', models.TextField()),
                ('descripcion_solucion', models.TextField(blank=True, null=True)),
                ('fecha_asignacion', models.DateTimeField(blank=True, null=True)),
                ('fecha_compromiso', models.DateTimeField(blank=True, null=True)),
                ('fecha_efectividad', models.DateTimeField(blank=True, null=True)),
                ('tiempo_estimado', models.PositiveIntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='helpdesks', to='catalog.service')),
            ],
            options={
                'db_table': 'helpdesks_helpdesk',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='HDComment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('autor_id', models.IntegerField(blank=True, null=True)),
                ('contenido', models.TextField()),
                ('es_interno', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('help_desk', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='helpdesks.helpdesk')),
            ],
            options={
                'db_table': 'helpdesks_hdcomment',
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='HDAttachment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(max_length=10)),
                ('nombre', models.CharField(max_length=200)),
                ('valor', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('help_desk', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='helpdesks.helpdesk')),
            ],
            options={
                'db_table': 'helpdesks_hdattachment',
                'ordering': ['-created_at'],
            },
        ),
    ]
