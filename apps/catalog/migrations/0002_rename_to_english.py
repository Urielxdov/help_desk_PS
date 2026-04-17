from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0001_initial'),
    ]

    operations = [
        # Department
        migrations.RenameField('Department', 'nombre', 'name'),
        migrations.RenameField('Department', 'descripcion', 'description'),
        migrations.RenameField('Department', 'activo', 'active'),
        # ServiceCategory
        migrations.RenameField('ServiceCategory', 'nombre', 'name'),
        migrations.RenameField('ServiceCategory', 'activo', 'active'),
        # Service
        migrations.RenameField('Service', 'nombre', 'name'),
        migrations.RenameField('Service', 'descripcion', 'description'),
        migrations.RenameField('Service', 'tiempo_estimado_default', 'estimated_hours'),
        migrations.RenameField('Service', 'activo', 'active'),
    ]
