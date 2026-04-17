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
                ('requester_id', models.IntegerField(blank=True, db_index=True, null=True)),
                ('assignee_id', models.IntegerField(blank=True, db_index=True, null=True)),
                ('origin', models.CharField(choices=[('error', 'Error'), ('request', 'Request'), ('inquiry', 'Inquiry'), ('maintenance', 'Maintenance')], max_length=20)),
                ('priority', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], max_length=10)),
                ('status', models.CharField(choices=[('open', 'Open'), ('in_progress', 'In Progress'), ('on_hold', 'On Hold'), ('resolved', 'Resolved'), ('closed', 'Closed')], db_index=True, default='open', max_length=15)),
                ('problem_description', models.TextField()),
                ('solution_description', models.TextField(blank=True, null=True)),
                ('assigned_at', models.DateTimeField(blank=True, null=True)),
                ('due_date', models.DateTimeField(blank=True, null=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('estimated_hours', models.PositiveIntegerField(help_text='Hours')),
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
                ('author_id', models.IntegerField(blank=True, null=True)),
                ('content', models.TextField()),
                ('is_internal', models.BooleanField(default=False, help_text='Only visible to IT')),
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
                ('type', models.CharField(choices=[('file', 'File'), ('url', 'URL')], max_length=10)),
                ('name', models.CharField(max_length=200)),
                ('value', models.TextField(help_text='File path or URL')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('help_desk', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='helpdesks.helpdesk')),
            ],
            options={
                'db_table': 'helpdesks_hdattachment',
                'ordering': ['-created_at'],
            },
        ),
    ]
