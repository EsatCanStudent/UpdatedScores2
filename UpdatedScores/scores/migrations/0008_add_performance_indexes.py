from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scores', '0007_add_lineup_model'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='match',
            index=models.Index(fields=['match_date'], name='match_date_idx'),
        ),
        migrations.AddIndex(
            model_name='match',
            index=models.Index(fields=['status'], name='match_status_idx'),
        ),
        migrations.AddIndex(
            model_name='event',
            index=models.Index(fields=['event_type'], name='event_type_idx'),
        ),
        migrations.AddIndex(
            model_name='lineup',
            index=models.Index(fields=['match', 'team'], name='lineup_match_team_idx'),
        ),
        migrations.AddIndex(
            model_name='lineupplayer',
            index=models.Index(fields=['lineup', 'is_starter'], name='lineup_player_starter_idx'),
        ),
    ]
