from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('catalog', '0003_rename_to_english'),
        ('helpdesks', '0004_helpdesk_impact'),
    ]

    operations = [
        migrations.CreateModel(
            name='TechnicianProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField(unique=True)),
                ('active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='technicians', to='catalog.department')),
            ],
            options={'db_table': 'sla_technicianprofile', 'ordering': ['user_id']},
        ),
        migrations.CreateModel(
            name='SLAConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('max_load', models.PositiveIntegerField(default=3)),
                ('score_overdue', models.IntegerField(default=1000)),
                ('score_company', models.IntegerField(default=100)),
                ('score_area', models.IntegerField(default=50)),
                ('score_individual', models.IntegerField(default=10)),
                ('score_critical', models.IntegerField(default=40)),
                ('score_high', models.IntegerField(default=30)),
                ('score_medium', models.IntegerField(default=20)),
                ('score_low', models.IntegerField(default=10)),
                ('department', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sla_config', to='catalog.department')),
            ],
            options={'db_table': 'sla_slaconfig'},
        ),
        migrations.CreateModel(
            name='ServiceQueue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('queued_at', models.DateTimeField(auto_now_add=True)),
                ('urgency_score', models.IntegerField(default=0)),
                ('help_desk', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='queue_entry', to='helpdesks.helpdesk')),
            ],
            options={'db_table': 'sla_servicequeue', 'ordering': ['-urgency_score', 'queued_at']},
        ),
    ]
