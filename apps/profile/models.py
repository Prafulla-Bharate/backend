"""
Profile Models
==============
Models for user profile data including education, experience, skills, and interests.
"""

import uuid
from typing import Optional

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel, SoftDeleteModel, TimeStampedModel


class UserEducation(TimeStampedModel, SoftDeleteModel):
    """
    Model for storing user education history.
    
    Tracks educational qualifications including degrees, institutions,
    and relevant details for career assessment.
    """
    
    class DegreeType(models.TextChoices):
        HIGH_SCHOOL = "high_school", _("High School")
        ASSOCIATE = "associate", _("Associate Degree")
        BACHELOR = "bachelor", _("Bachelor's Degree")
        MASTER = "master", _("Master's Degree")
        DOCTORATE = "doctorate", _("Doctorate (Ph.D.)")
        PROFESSIONAL = "professional", _("Professional Degree")
        CERTIFICATE = "certificate", _("Certificate")
        DIPLOMA = "diploma", _("Diploma")
        OTHER = "other", _("Other")
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="educations"
    )
    institution_name = models.CharField(
        max_length=255,
        help_text=_("Name of the educational institution")
    )
    degree_type = models.CharField(
        max_length=20,
        choices=DegreeType.choices,
        default=DegreeType.BACHELOR,
        help_text=_("Type of degree obtained")
    )
    degree_name = models.CharField(
        max_length=255,
        help_text=_("Name of the degree/program"),
        blank=True
    )
    field_of_study = models.CharField(
        max_length=255,
        help_text=_("Major or field of study"),
        blank=True
    )
    start_date = models.DateField(
        help_text=_("When education started")
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("When education ended (null if ongoing)")
    )
    is_current = models.BooleanField(
        default=False,
        help_text=_("Whether currently enrolled")
    )
    gpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(10.0)
        ],
        help_text=_("Grade Point Average (0.0 - 10.0 scale)")
    )
    gpa_scale = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=10.0,
        help_text=_("GPA scale (e.g., 4.0, 5.0, 10.0)")
    )
    description = models.TextField(
        blank=True,
        help_text=_("Additional details about education")
    )
    achievements = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of achievements during education")
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Location of the institution")
    )
    institution_url = models.URLField(
        blank=True,
        help_text=_("Website of the institution")
    )
    is_verified = models.BooleanField(
        default=False,
        help_text=_("Whether education has been verified")
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When education was verified")
    )

    class Meta:
        db_table = "user_education"
        verbose_name = _("User Education")
        verbose_name_plural = _("User Educations")
        ordering = ["-end_date", "-start_date"]
        indexes = [
            models.Index(fields=["user", "-end_date"]),
            models.Index(fields=["degree_type"]),
            models.Index(fields=["field_of_study"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.degree_name} at {self.institution_name}"

    def save(self, *args, **kwargs):
        """Set end_date to null if is_current is True."""
        if self.is_current:
            self.end_date = None
        super().save(*args, **kwargs)


class UserExperience(TimeStampedModel, SoftDeleteModel):
    """
    Model for storing user work experience.
    
    Tracks employment history including roles, companies,
    and detailed responsibilities for career assessment.
    """
    
    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", _("Full-time")
        PART_TIME = "part_time", _("Part-time")
        CONTRACT = "contract", _("Contract")
        FREELANCE = "freelance", _("Freelance")
        INTERNSHIP = "internship", _("Internship")
        APPRENTICESHIP = "apprenticeship", _("Apprenticeship")
        SELF_EMPLOYED = "self_employed", _("Self-employed")
        VOLUNTEER = "volunteer", _("Volunteer")
        OTHER = "other", _("Other")
    
    class WorkLocation(models.TextChoices):
        ONSITE = "onsite", _("On-site")
        REMOTE = "remote", _("Remote")
        HYBRID = "hybrid", _("Hybrid")
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="experiences"
    )
    company_name = models.CharField(
        max_length=255,
        help_text=_("Name of the company/organization")
    )
    job_title = models.CharField(
        max_length=255,
        help_text=_("Job title/role")
    )
    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME,
        help_text=_("Type of employment")
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Location of work")
    )
    work_location_type = models.CharField(
        max_length=10,
        choices=WorkLocation.choices,
        default=WorkLocation.ONSITE,
        help_text=_("Work location arrangement")
    )
    start_date = models.DateField(
        help_text=_("When employment started")
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("When employment ended (null if current)")
    )
    is_current = models.BooleanField(
        default=False,
        help_text=_("Whether currently employed here")
    )
    description = models.TextField(
        blank=True,
        help_text=_("Job description and responsibilities")
    )
    responsibilities = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of key responsibilities")
    )
    achievements = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of achievements in this role")
    )
    technologies = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Technologies/tools used in this role")
    )
    company_url = models.URLField(
        blank=True,
        help_text=_("Website of the company")
    )
    company_industry = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Industry of the company")
    )
    company_size = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Size of the company (e.g., '50-100 employees')")
    )
    salary_range = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Salary range (optional)")
    )
    is_verified = models.BooleanField(
        default=False,
        help_text=_("Whether experience has been verified")
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When experience was verified")
    )
    
    # AI-extracted metadata
    extracted_skills = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Skills extracted from description by AI")
    )
    normalized_title = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Normalized job title for matching")
    )

    class Meta:
        db_table = "user_experience"
        verbose_name = _("User Experience")
        verbose_name_plural = _("User Experiences")
        ordering = ["-end_date", "-start_date"]
        indexes = [
            models.Index(fields=["user", "-end_date"]),
            models.Index(fields=["job_title"]),
            models.Index(fields=["company_name"]),
            models.Index(fields=["employment_type"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.job_title} at {self.company_name}"

    def save(self, *args, **kwargs):
        """Set end_date to null if is_current is True."""
        if self.is_current:
            self.end_date = None
        super().save(*args, **kwargs)

    @property
    def duration_months(self) -> Optional[int]:
        """Calculate duration in months."""
        if not self.start_date:
            return None
        end = self.end_date or timezone.now().date()
        delta = end - self.start_date
        return delta.days // 30


class SkillCategory(BaseModel):
    """
    Category for organizing skills.
    
    Examples: Technical, Soft Skills, Languages, Tools, etc.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Category name")
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text=_("URL-friendly slug")
    )
    description = models.TextField(
        blank=True,
        help_text=_("Description of the category")
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        help_text=_("Parent category for nested structure")
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Icon identifier")
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text=_("Display order")
    )

    class Meta:
        db_table = "skill_categories"
        verbose_name = _("Skill Category")
        verbose_name_plural = _("Skill Categories")
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Skill(BaseModel):
    """
    Master skill model representing available skills.
    
    This is a reference table of all possible skills that users can have.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Skill name")
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text=_("URL-friendly slug")
    )
    description = models.TextField(
        blank=True,
        help_text=_("Description of the skill")
    )
    category = models.ForeignKey(
        SkillCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="skills",
        help_text=_("Category this skill belongs to")
    )
    aliases = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Alternative names for this skill")
    )
    related_skills = models.ManyToManyField(
        "self",
        blank=True,
        help_text=_("Related skills")
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether skill is active and available")
    )
    popularity_score = models.PositiveIntegerField(
        default=0,
        help_text=_("Popularity score based on usage")
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Icon identifier")
    )

    class Meta:
        db_table = "skills"
        verbose_name = _("Skill")
        verbose_name_plural = _("Skills")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["category", "name"]),
            models.Index(fields=["-popularity_score"]),
        ]

    def __str__(self):
        return self.name


class UserSkill(TimeStampedModel, SoftDeleteModel):
    """
    Model linking users to their skills with proficiency levels.
    """
    
    class ProficiencyLevel(models.IntegerChoices):
        BEGINNER = 1, _("Beginner")
        ELEMENTARY = 2, _("Elementary")
        INTERMEDIATE = 3, _("Intermediate")
        ADVANCED = 4, _("Advanced")
        EXPERT = 5, _("Expert")
    
    class SkillSource(models.TextChoices):
        SELF_REPORTED = "self_reported", _("Self-reported")
        RESUME_EXTRACTED = "resume_extracted", _("Resume Extracted")
        AI_INFERRED = "ai_inferred", _("AI Inferred")
        ASSESSMENT = "assessment", _("From Assessment")
        VERIFIED = "verified", _("Verified")
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="skills"
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="user_skills"
    )
    proficiency_level = models.PositiveSmallIntegerField(
        choices=ProficiencyLevel.choices,
        default=ProficiencyLevel.INTERMEDIATE,
        help_text=_("Proficiency level (1-5)")
    )
    years_of_experience = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Years of experience with this skill")
    )
    source = models.CharField(
        max_length=20,
        choices=SkillSource.choices,
        default=SkillSource.SELF_REPORTED,
        help_text=_("How this skill was added")
    )
    is_primary = models.BooleanField(
        default=False,
        help_text=_("Whether this is a primary skill")
    )
    last_used_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("When this skill was last used")
    )
    endorsements_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of endorsements")
    )
    is_verified = models.BooleanField(
        default=False,
        help_text=_("Whether skill has been verified")
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When skill was verified")
    )
    assessment_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Assessment score (0-100)")
    )
    confidence_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text=_("AI confidence score (0-1)")
    )
    notes = models.TextField(
        blank=True,
        help_text=_("Additional notes about the skill")
    )

    class Meta:
        db_table = "user_skills"
        verbose_name = _("User Skill")
        verbose_name_plural = _("User Skills")
        ordering = ["-is_primary", "-proficiency_level"]
        unique_together = ["user", "skill"]
        indexes = [
            models.Index(fields=["user", "-proficiency_level"]),
            models.Index(fields=["skill", "-proficiency_level"]),
            models.Index(fields=["source"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.skill.name} ({self.get_proficiency_level_display()})"


class InterestCategory(BaseModel):
    """
    Category for organizing interests.
    
    Examples: Career, Industry, Learning, Technology, etc.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Category name")
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text=_("URL-friendly slug")
    )
    description = models.TextField(
        blank=True,
        help_text=_("Description of the category")
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Icon identifier")
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text=_("Display order")
    )

    class Meta:
        db_table = "interest_categories"
        verbose_name = _("Interest Category")
        verbose_name_plural = _("Interest Categories")
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Interest(BaseModel):
    """
    Master interest model representing available interests.
    
    This is a reference table of all possible interests users can have.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Interest name")
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text=_("URL-friendly slug")
    )
    description = models.TextField(
        blank=True,
        help_text=_("Description of the interest")
    )
    category = models.ForeignKey(
        InterestCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interests",
        help_text=_("Category this interest belongs to")
    )
    related_skills = models.ManyToManyField(
        Skill,
        blank=True,
        related_name="related_interests",
        help_text=_("Skills related to this interest")
    )
    related_careers = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Related career paths")
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether interest is active and available")
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Icon identifier")
    )

    class Meta:
        db_table = "interests"
        verbose_name = _("Interest")
        verbose_name_plural = _("Interests")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["category", "name"]),
        ]

    def __str__(self):
        return self.name


class UserInterest(TimeStampedModel, SoftDeleteModel):
    """
    Model linking users to their interests.
    """
    
    class InterestLevel(models.IntegerChoices):
        CURIOUS = 1, _("Curious")
        INTERESTED = 2, _("Interested")
        PASSIONATE = 3, _("Passionate")
    
    class InterestSource(models.TextChoices):
        SELF_REPORTED = "self_reported", _("Self-reported")
        AI_INFERRED = "ai_inferred", _("AI Inferred")
        BEHAVIOR_BASED = "behavior_based", _("Behavior Based")
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interests"
    )
    interest = models.ForeignKey(
        Interest,
        on_delete=models.CASCADE,
        related_name="user_interests"
    )
    interest_level = models.PositiveSmallIntegerField(
        choices=InterestLevel.choices,
        default=InterestLevel.INTERESTED,
        help_text=_("Level of interest (1-3)")
    )
    source = models.CharField(
        max_length=20,
        choices=InterestSource.choices,
        default=InterestSource.SELF_REPORTED,
        help_text=_("How this interest was added")
    )
    is_primary = models.BooleanField(
        default=False,
        help_text=_("Whether this is a primary interest")
    )
    notes = models.TextField(
        blank=True,
        help_text=_("Additional notes about the interest")
    )

    class Meta:
        db_table = "user_interests"
        verbose_name = _("User Interest")
        verbose_name_plural = _("User Interests")
        ordering = ["-is_primary", "-interest_level"]
        unique_together = ["user", "interest"]
        indexes = [
            models.Index(fields=["user", "-interest_level"]),
            models.Index(fields=["interest"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.interest.name}"


class UserCertification(TimeStampedModel, SoftDeleteModel):
    """
    Model for storing user certifications and credentials.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="certifications"
    )
    name = models.CharField(
        max_length=255,
        help_text=_("Name of the certification")
    )
    issuing_organization = models.CharField(
        max_length=255,
        help_text=_("Organization that issued the certification")
    )
    credential_id = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Credential ID/number")
    )
    credential_url = models.URLField(
        blank=True,
        help_text=_("URL to verify credential")
    )
    issue_date = models.DateField(
        help_text=_("When certification was issued")
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("When certification expires (null if no expiry)")
    )
    does_not_expire = models.BooleanField(
        default=False,
        help_text=_("Whether certification has no expiry date")
    )
    description = models.TextField(
        blank=True,
        help_text=_("Description of the certification")
    )
    related_skills = models.ManyToManyField(
        Skill,
        blank=True,
        related_name="certifications",
        help_text=_("Skills related to this certification")
    )
    is_verified = models.BooleanField(
        default=False,
        help_text=_("Whether certification has been verified")
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When certification was verified")
    )
    document = models.FileField(
        upload_to="certifications/",
        blank=True,
        help_text=_("Certification document file")
    )

    class Meta:
        db_table = "user_certifications"
        verbose_name = _("User Certification")
        verbose_name_plural = _("User Certifications")
        ordering = ["-issue_date"]
        indexes = [
            models.Index(fields=["user", "-issue_date"]),
            models.Index(fields=["issuing_organization"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.name}"

    @property
    def is_expired(self) -> bool:
        """Check if certification has expired."""
        if self.does_not_expire:
            return False
        if not self.expiry_date:
            return False
        return self.expiry_date < timezone.now().date()


class UserProject(TimeStampedModel, SoftDeleteModel):
    """
    Model for storing user projects and portfolio items.
    """
    
    class ProjectStatus(models.TextChoices):
        COMPLETED = "completed", _("Completed")
        IN_PROGRESS = "in_progress", _("In Progress")
        ON_HOLD = "on_hold", _("On Hold")
        ARCHIVED = "archived", _("Archived")
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects"
    )
    title = models.CharField(
        max_length=255,
        help_text=_("Project title")
    )
    description = models.TextField(
        help_text=_("Project description")
    )
    short_description = models.CharField(
        max_length=500,
        blank=True,
        help_text=_("Brief summary of the project")
    )
    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.COMPLETED,
        help_text=_("Current status of the project")
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("When project started")
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("When project ended")
    )
    project_url = models.URLField(
        blank=True,
        help_text=_("URL to the project")
    )
    repository_url = models.URLField(
        blank=True,
        help_text=_("URL to source code repository")
    )
    technologies = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Technologies used in the project")
    )
    related_skills = models.ManyToManyField(
        Skill,
        blank=True,
        related_name="projects",
        help_text=_("Skills demonstrated in this project")
    )
    related_experience = models.ForeignKey(
        UserExperience,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        help_text=_("Associated work experience")
    )
    achievements = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Key achievements from the project")
    )
    images = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Project images/screenshots")
    )
    is_featured = models.BooleanField(
        default=False,
        help_text=_("Whether to feature this project")
    )
    is_public = models.BooleanField(
        default=True,
        help_text=_("Whether project is publicly visible")
    )
    view_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of times project was viewed")
    )

    class Meta:
        db_table = "user_projects"
        verbose_name = _("User Project")
        verbose_name_plural = _("User Projects")
        ordering = ["-is_featured", "-end_date", "-start_date"]
        indexes = [
            models.Index(fields=["user", "-end_date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["is_featured"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.title}"


class UserLanguage(TimeStampedModel, SoftDeleteModel):
    """
    Model for storing user language proficiencies.
    """
    
    class ProficiencyLevel(models.TextChoices):
        ELEMENTARY = "elementary", _("Elementary")
        LIMITED_WORKING = "limited_working", _("Limited Working")
        PROFESSIONAL_WORKING = "professional_working", _("Professional Working")
        FULL_PROFESSIONAL = "full_professional", _("Full Professional")
        NATIVE = "native", _("Native/Bilingual")
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="languages"
    )
    language_code = models.CharField(
        max_length=10,
        help_text=_("Language code (e.g., 'en', 'es')")
    )
    language_name = models.CharField(
        max_length=100,
        help_text=_("Language name (e.g., 'English', 'Spanish')")
    )
    proficiency = models.CharField(
        max_length=25,
        choices=ProficiencyLevel.choices,
        default=ProficiencyLevel.PROFESSIONAL_WORKING,
        help_text=_("Proficiency level")
    )
    is_native = models.BooleanField(
        default=False,
        help_text=_("Whether this is a native language")
    )
    is_verified = models.BooleanField(
        default=False,
        help_text=_("Whether proficiency has been verified")
    )

    class Meta:
        db_table = "user_languages"
        verbose_name = _("User Language")
        verbose_name_plural = _("User Languages")
        ordering = ["-is_native", "language_name"]
        unique_together = ["user", "language_code"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["language_code"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.language_name} ({self.get_proficiency_display()})"


class UserSocialLink(BaseModel):
    """
    Model for storing user social media and professional links.
    """
    
    class PlatformType(models.TextChoices):
        LINKEDIN = "linkedin", _("LinkedIn")
        GITHUB = "github", _("GitHub")
        TWITTER = "twitter", _("Twitter/X")
        PORTFOLIO = "portfolio", _("Portfolio")
        WEBSITE = "website", _("Personal Website")
        STACKOVERFLOW = "stackoverflow", _("Stack Overflow")
        MEDIUM = "medium", _("Medium")
        BEHANCE = "behance", _("Behance")
        DRIBBBLE = "dribbble", _("Dribbble")
        YOUTUBE = "youtube", _("YouTube")
        OTHER = "other", _("Other")
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_links"
    )
    platform = models.CharField(
        max_length=20,
        choices=PlatformType.choices,
        help_text=_("Social platform type")
    )
    url = models.URLField(
        help_text=_("Profile URL")
    )
    username = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Username on the platform")
    )
    is_primary = models.BooleanField(
        default=False,
        help_text=_("Whether this is the primary link for this platform")
    )
    is_verified = models.BooleanField(
        default=False,
        help_text=_("Whether link has been verified")
    )

    class Meta:
        db_table = "user_social_links"
        verbose_name = _("User Social Link")
        verbose_name_plural = _("User Social Links")
        ordering = ["platform"]
        indexes = [
            models.Index(fields=["user", "platform"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.get_platform_display()}"
