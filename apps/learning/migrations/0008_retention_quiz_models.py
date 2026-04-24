from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0007_deep_dive_phase_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="RetentionQuizQuestion",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("topic", models.CharField(max_length=120)),
                ("subtopic", models.CharField(blank=True, max_length=120)),
                (
                    "difficulty",
                    models.CharField(
                        choices=[("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")],
                        default="medium",
                        max_length=20,
                    ),
                ),
                ("question_text", models.TextField()),
                ("options", models.JSONField(blank=True, default=list)),
                ("correct_answer", models.CharField(max_length=32)),
                ("explanation", models.TextField(blank=True)),
                ("tags", models.JSONField(blank=True, default=list)),
                ("career_tracks", models.JSONField(blank=True, default=list)),
                ("is_active", models.BooleanField(default=True)),
                ("usage_count", models.PositiveIntegerField(default=0)),
            ],
            options={
                "ordering": ["topic", "difficulty", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="RetentionQuizAttempt",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "status",
                    models.CharField(
                        choices=[("started", "Started"), ("submitted", "Submitted")],
                        default="started",
                        max_length=20,
                    ),
                ),
                ("passing_score", models.PositiveIntegerField(default=70)),
                ("questions_snapshot", models.JSONField(blank=True, default=list)),
                ("answers", models.JSONField(blank=True, default=dict)),
                ("score", models.PositiveIntegerField(default=0)),
                ("passed", models.BooleanField(default=False)),
                ("weak_topics", models.JSONField(blank=True, default=list)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "enrollment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="retention_quiz_attempts",
                        to="learning.userlearningpathenrollment",
                    ),
                ),
                (
                    "target_phase",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="retention_quiz_attempts",
                        to="learning.learningphase",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="retention_quiz_attempts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="retentionquizquestion",
            index=models.Index(fields=["is_active", "difficulty"], name="learning_ret_is_acti_fca221_idx"),
        ),
        migrations.AddIndex(
            model_name="retentionquizquestion",
            index=models.Index(fields=["topic"], name="learning_ret_topic_9117f1_idx"),
        ),
        migrations.AddIndex(
            model_name="retentionquizattempt",
            index=models.Index(fields=["user", "status"], name="learning_ret_user_id_8e4f8f_idx"),
        ),
        migrations.AddIndex(
            model_name="retentionquizattempt",
            index=models.Index(fields=["enrollment", "target_phase"], name="learning_ret_enrollm_045994_idx"),
        ),
    ]
