from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0002_rename_to_english'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='client_close',
            field=models.BooleanField(default=True, help_text='Allow requester to close the ticket'),
        ),
    ]
