from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('career', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='careerprediction',
            name='is_accepted',
            field=models.BooleanField(
                blank=True,
                default=None,
                help_text='True = accepted, False = rejected, None = no decision yet',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='careerprediction',
            name='accepted_career_title',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Career title the user accepted from this prediction',
                max_length=255,
            ),
            preserve_default=False,
        ),
    ]
