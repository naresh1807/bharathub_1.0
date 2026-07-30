from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0003_employment_salary_lpa'),
    ]

    operations = [
        migrations.AddField(
            model_name='employment',
            name='offer_status',
            field=models.CharField(
                choices=[('pending', 'Pending Acceptance'), ('accepted', 'Accepted')],
                default='pending', max_length=15,
            ),
        ),
        migrations.AddField(
            model_name='employment',
            name='offer_accepted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
