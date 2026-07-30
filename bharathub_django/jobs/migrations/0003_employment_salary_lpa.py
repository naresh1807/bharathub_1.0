from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0002_jobapplication_hired_status_employment'),
    ]

    operations = [
        migrations.AddField(
            model_name='employment',
            name='salary_lpa',
            # ఇప్పటికే ఉన్న Employment రికార్డులు (ఏమైనా ఉంటే) NULL
            # పడిపోకుండా ఉండటానికి ఇక్కడ మాత్రమే ఒక తాత్కాలిక default
            # (0.00) -- models.py లో మాత్రం ఏ default లేదు, కొత్త Mark as
            # Hired ఫారమ్ ప్రతిసారీ నిజమైన అంకె తప్పనిసరిగా అడుగుతుంది.
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=6, verbose_name='Salary (LPA)'),
            preserve_default=False,
        ),
    ]
