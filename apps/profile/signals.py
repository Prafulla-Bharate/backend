"""
Profile Signals
===============
Signal handlers for profile-related events.
"""

import logging

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from apps.profile.models import UserSkill, UserExperience, Skill

logger = logging.getLogger(__name__)


@receiver(post_save, sender=UserSkill)
def update_skill_popularity(sender, instance: UserSkill, created: bool, **kwargs):
    """Increase skill popularity score when a user adds a skill."""
    if created:
        Skill.objects.filter(id=instance.skill_id).update(
            popularity_score=Skill.objects.get(id=instance.skill_id).popularity_score + 1
        )
        logger.debug(f"Updated popularity for skill: {instance.skill.name}")


@receiver(post_delete, sender=UserSkill)
def decrease_skill_popularity(sender, instance: UserSkill, **kwargs):
    """Decrease skill popularity score when a user removes a skill."""
    try:
        skill = Skill.objects.get(id=instance.skill_id)
        if skill.popularity_score > 0:
            skill.popularity_score -= 1
            skill.save(update_fields=["popularity_score"])
    except Skill.DoesNotExist:
        pass


@receiver(post_save, sender=UserExperience)
def log_experience_saved(sender, instance: UserExperience, created: bool, **kwargs):
    """Log when user experience is created or updated."""
    action = "created" if created else "updated"
    logger.info(f"Experience {action} for user {instance.user_id}: {instance.id}")
