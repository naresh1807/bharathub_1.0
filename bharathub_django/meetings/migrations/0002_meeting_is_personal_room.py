from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meetings', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='meeting',
            name='is_personal_room',
            field=models.BooleanField(default=False),
        ),
    ]
