from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helpdesks', '0003_data_values_to_english'),
    ]

    operations = [
        migrations.AddField(
            model_name='helpdesk',
            name='impact',
            field=models.CharField(
                choices=[('individual', 'Individual'), ('area', 'Area'), ('company', 'Company')],
                default='individual',
                max_length=10,
            ),
        ),
    ]
