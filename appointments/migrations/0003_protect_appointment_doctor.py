from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('appointments', '0002_appointment_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appointment',
            name='doctor',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to='appointments.doctor',
            ),
        ),
    ]
