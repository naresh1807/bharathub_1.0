from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('candidates', '0001_initial'),
        ('jobs', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='jobapplication',
            name='status',
            field=models.CharField(
                choices=[
                    ('new', '🆕 New'),
                    ('review', '👁️ Under Review'),
                    ('shortlisted', '✅ Shortlisted'),
                    ('interview', '📅 Interview'),
                    ('offered', '📧 Offer Sent'),
                    ('hired', '✅ Hired'),
                    ('rejected', '❌ Rejected'),
                ],
                default='new', max_length=15,
            ),
        ),
        migrations.CreateModel(
            name='Employment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('designation', models.CharField(max_length=150)),
                ('joining_date', models.DateField()),
                ('status', models.CharField(
                    choices=[
                        ('active', 'Active'),
                        ('resignation_requested', 'Resignation Requested'),
                        ('relieved', 'Relieved'),
                    ],
                    default='active', max_length=25,
                )),
                ('resignation_requested_at', models.DateTimeField(blank=True, null=True)),
                ('relieving_date', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('application', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='employment', to='jobs.jobapplication')),
                ('candidate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='employments', to='candidates.candidateprofile')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
