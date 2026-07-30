# Generated manually to match the 0001_initial.py style/formatting --
# adds EmployerProfile.company_logo (see accounts/models.py) so
# employers can upload a company logo, shown in the dashboard nav and
# used as the chat avatar (messaging/permissions.py avatar_url_for()).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='employerprofile',
            name='company_logo',
            field=models.ImageField(blank=True, null=True, upload_to='employer_logos/%Y/%m/'),
        ),
    ]
