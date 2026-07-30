from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import webmail.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MailAddress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('local_part', models.CharField(max_length=30, unique=True, validators=[webmail.models.LOCAL_PART_VALIDATOR])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='mail_address', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['local_part'],
            },
        ),
        migrations.CreateModel(
            name='Email',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('to_raw', models.CharField(blank=True, max_length=150)),
                ('subject', models.CharField(blank=True, max_length=255)),
                ('body', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('is_draft', models.BooleanField(default=False)),
                ('sender_trashed', models.BooleanField(default=False)),
                ('is_read', models.BooleanField(default=False)),
                ('is_starred', models.BooleanField(default=False)),
                ('recipient_trashed', models.BooleanField(default=False)),
                ('recipient', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='received_emails', to='webmail.mailaddress')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_emails', to='webmail.mailaddress')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
