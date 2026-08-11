from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('trails', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='trail',
            name='photo',
            field=models.ImageField(blank=True, upload_to='trail_photos/'),
        ),
    ]