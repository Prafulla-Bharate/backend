from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userpreferences',
            name='accepted_career_title',
            field=models.CharField(
                blank=True,
                default='',
                help_text='The career title the user has accepted from their prediction',
                max_length=255,
            ),
            preserve_default=False,
        ),
    ]
