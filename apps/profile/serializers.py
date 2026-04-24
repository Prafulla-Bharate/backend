"""
Profile Serializers
==================
Serializers for profile-related data.
"""

from rest_framework import serializers

from apps.profile.models import (
    UserEducation,
    UserExperience,
    Skill,
    UserSkill,
    UserInterest,
    UserCertification,
    UserProject,
    UserLanguage,
    UserSocialLink,
)


# ============================================================================
# Education Serializers
# ============================================================================

class UserEducationSerializer(serializers.ModelSerializer):
    """Serializer for user education records."""
    
    degree_type_display = serializers.CharField(
        source="get_degree_type_display",
        read_only=True
    )
    
    class Meta:
        model = UserEducation
        fields = [
            "id",
            "institution_name",
            "degree_type",
            "degree_type_display",
            "degree_name",
            "field_of_study",
            "start_date",
            "end_date",
            "is_current",
            "gpa",
            "gpa_scale",
            "description",
            "achievements",
            "location",
            "institution_url",
            "is_verified",
            "verified_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_verified", "verified_at", "created_at", "updated_at"]
    
    def validate(self, attrs):
        """Validate education dates."""
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        is_current = attrs.get("is_current", False)
        
        if not is_current and end_date and start_date:
            if end_date < start_date:
                raise serializers.ValidationError({
                    "end_date": "End date must be after start date."
                })
        
        return attrs
    
    def create(self, validated_data):
        """Create education with current user."""
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class UserEducationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for education listing."""
    
    degree_type_display = serializers.CharField(
        source="get_degree_type_display",
        read_only=True
    )
    
    class Meta:
        model = UserEducation
        fields = [
            "id",
            "institution_name",
            "degree_type",
            "degree_type_display",
            "degree_name",
            "field_of_study",
            "start_date",
            "end_date",
            "is_current",
            "is_verified",
        ]


# ============================================================================
# Experience Serializers
# ============================================================================

class UserExperienceSerializer(serializers.ModelSerializer):
    """Serializer for user experience records."""
    
    employment_type_display = serializers.CharField(
        source="get_employment_type_display",
        read_only=True
    )
    work_location_type_display = serializers.CharField(
        source="get_work_location_type_display",
        read_only=True
    )
    duration_months = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = UserExperience
        fields = [
            "id",
            "company_name",
            "job_title",
            "employment_type",
            "employment_type_display",
            "location",
            "work_location_type",
            "work_location_type_display",
            "start_date",
            "end_date",
            "is_current",
            "description",
            "responsibilities",
            "achievements",
            "technologies",
            "company_url",
            "company_industry",
            "company_size",
            "is_verified",
            "verified_at",
            "extracted_skills",
            "normalized_title",
            "duration_months",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "is_verified", "verified_at", "extracted_skills",
            "normalized_title", "duration_months", "created_at", "updated_at"
        ]
    
    def validate(self, attrs):
        """Validate experience dates."""
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        is_current = attrs.get("is_current", False)
        
        if not is_current and end_date and start_date:
            if end_date < start_date:
                raise serializers.ValidationError({
                    "end_date": "End date must be after start date."
                })
        
        return attrs
    
    def create(self, validated_data):
        """Create experience with current user."""
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class UserExperienceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for experience listing."""
    
    employment_type_display = serializers.CharField(
        source="get_employment_type_display",
        read_only=True
    )
    duration_months = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = UserExperience
        fields = [
            "id",
            "company_name",
            "job_title",
            "employment_type",
            "employment_type_display",
            "location",
            "start_date",
            "end_date",
            "is_current",
            "is_verified",
            "duration_months",
        ]


class SkillListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for skill listing."""
    
    class Meta:
        model = Skill
        fields = ["id", "name", "slug", "category", "icon"]


class UserSkillListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for user skill listing."""
    
    skill_name = serializers.CharField(source="skill.name", read_only=True)
    proficiency_level_display = serializers.CharField(
        source="get_proficiency_level_display",
        read_only=True
    )
    
    class Meta:
        model = UserSkill
        fields = [
            "id",
            "skill",
            "skill_name",
            "proficiency_level",
            "proficiency_level_display",
            "is_primary",
            "is_verified",
        ]


# ============================================================================
# Certification Serializers
# ============================================================================

class UserCertificationSerializer(serializers.ModelSerializer):
    """Serializer for user certifications."""
    
    is_expired = serializers.BooleanField(read_only=True)
    related_skills = SkillListSerializer(many=True, read_only=True)
    related_skill_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = UserCertification
        fields = [
            "id",
            "name",
            "issuing_organization",
            "credential_id",
            "credential_url",
            "issue_date",
            "expiry_date",
            "does_not_expire",
            "description",
            "related_skills",
            "related_skill_ids",
            "is_verified",
            "verified_at",
            "document",
            "is_expired",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_verified", "verified_at", "is_expired", "created_at", "updated_at"]

    name = serializers.CharField(required=True)
    issuing_organization = serializers.CharField(required=False, allow_blank=True)
    credential_id = serializers.CharField(required=False, allow_blank=True)
    credential_url = serializers.URLField(required=False, allow_blank=True)
    issue_date = serializers.DateField(required=False, allow_null=True)
    expiry_date = serializers.DateField(required=False, allow_null=True)
    does_not_expire = serializers.BooleanField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    document = serializers.FileField(required=False, allow_null=True)
    
    def create(self, validated_data):
        """Create certification with current user."""
        related_skill_ids = validated_data.pop("related_skill_ids", [])
        validated_data["user"] = self.context["request"].user
        certification = super().create(validated_data)
        
        if related_skill_ids:
            skills = Skill.objects.filter(id__in=related_skill_ids)
            certification.related_skills.set(skills)
        
        return certification
    
    def update(self, instance, validated_data):
        """Update certification with skills."""
        related_skill_ids = validated_data.pop("related_skill_ids", None)
        instance = super().update(instance, validated_data)
        
        if related_skill_ids is not None:
            skills = Skill.objects.filter(id__in=related_skill_ids)
            instance.related_skills.set(skills)
        
        return instance


# ============================================================================
# Project Serializers
# ============================================================================

class UserProjectSerializer(serializers.ModelSerializer):
    """Serializer for user projects."""
    
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True
    )
    related_skills = SkillListSerializer(many=True, read_only=True)
    related_skill_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = UserProject
        fields = [
            "id",
            "title",
            "description",
            "short_description",
            "status",
            "status_display",
            "start_date",
            "end_date",
            "project_url",
            "repository_url",
            "technologies",
            "related_skills",
            "related_skill_ids",
            "related_experience",
            "achievements",
            "images",
            "is_featured",
            "is_public",
            "view_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "view_count", "created_at", "updated_at"]

    title = serializers.CharField(required=True)
    description = serializers.CharField(required=False, allow_blank=True)
    short_description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.CharField(required=False, allow_blank=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    project_url = serializers.URLField(required=False, allow_blank=True)
    repository_url = serializers.URLField(required=False, allow_blank=True)
    technologies = serializers.JSONField(required=False)
    related_experience = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=UserExperience.objects.all())
    achievements = serializers.JSONField(required=False)
    images = serializers.JSONField(required=False)
    is_featured = serializers.BooleanField(required=False)
    is_public = serializers.BooleanField(required=False)
    
    def create(self, validated_data):
        """Create project with current user."""
        related_skill_ids = validated_data.pop("related_skill_ids", [])
        validated_data["user"] = self.context["request"].user
        project = super().create(validated_data)
        
        if related_skill_ids:
            skills = Skill.objects.filter(id__in=related_skill_ids)
            project.related_skills.set(skills)
        
        return project
    
    def update(self, instance, validated_data):
        """Update project with skills."""
        related_skill_ids = validated_data.pop("related_skill_ids", None)
        instance = super().update(instance, validated_data)
        
        if related_skill_ids is not None:
            skills = Skill.objects.filter(id__in=related_skill_ids)
            instance.related_skills.set(skills)
        
        return instance


# ============================================================================
# Language Serializers
# ============================================================================

class UserLanguageSerializer(serializers.ModelSerializer):
    """Serializer for user languages."""
    
    proficiency_display = serializers.CharField(
        source="get_proficiency_display",
        read_only=True
    )
    
    class Meta:
        model = UserLanguage
        fields = [
            "id",
            "language_code",
            "language_name",
            "proficiency",
            "proficiency_display",
            "is_native",
            "is_verified",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_verified", "created_at", "updated_at"]

    language_code = serializers.CharField(required=True)
    language_name = serializers.CharField(required=True)
    proficiency = serializers.CharField(required=False, allow_blank=True)
    is_native = serializers.BooleanField(required=False)
    
    def create(self, validated_data):
        """Create language with current user."""
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


# ============================================================================
# Social Link Serializers
# ============================================================================

class UserSocialLinkSerializer(serializers.ModelSerializer):
    """Serializer for user social links."""
    
    platform_display = serializers.CharField(
        source="get_platform_display",
        read_only=True
    )
    
    class Meta:
        model = UserSocialLink
        fields = [
            "id",
            "platform",
            "platform_display",
            "url",
            "username",
            "is_primary",
            "is_verified",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_verified", "created_at", "updated_at"]

    platform = serializers.CharField(required=True)
    url = serializers.URLField(required=True)
    username = serializers.CharField(required=False, allow_blank=True)
    is_primary = serializers.BooleanField(required=False)
    
    def create(self, validated_data):
        """Create social link with current user."""
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class ProfileCompletenessSerializer(serializers.Serializer):
    """Serializer for profile completeness score."""
    
    overall_score = serializers.IntegerField(
        min_value=0,
        max_value=100,
        help_text="Overall profile completeness percentage"
    )
    sections = serializers.DictField(
        help_text="Completeness score for each section"
    )
    missing_sections = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of sections that need attention"
    )
    suggestions = serializers.ListField(
        child=serializers.CharField(),
        help_text="Suggestions to improve profile"
    )


# ============================================================================
# User Profile Serializers (for /api/profile/ endpoint)
# ============================================================================

class UserProfileSerializer(serializers.Serializer):
    """
    Serializer for the main /api/profile/ endpoint.
    Matches the API contract expected by frontend.
    """
    
    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(max_length=100, required=True)
    last_name = serializers.CharField(max_length=100, required=True)
    phone = serializers.CharField(max_length=20, allow_blank=True, required=False)
    location = serializers.CharField(max_length=255, allow_blank=True, required=False)
    bio = serializers.CharField(allow_blank=True, required=False)
    linkedin_url = serializers.URLField(allow_blank=True, required=False)
    github_url = serializers.URLField(allow_blank=True, required=False)
    portfolio_url = serializers.URLField(allow_blank=True, required=False)
    experience_level = serializers.CharField(max_length=50, allow_blank=True, required=False)
    profile_picture_url = serializers.SerializerMethodField()
    is_profile_complete = serializers.BooleanField(read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    # Write-only input fields
    skills = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)
    interests = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)
    education = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)
    experience = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)
    certifications = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)
    projects = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)
    languages = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)
    social_links = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)
    # Read-only output fields
    skills_out = serializers.SerializerMethodField(read_only=True)
    interests_out = serializers.SerializerMethodField(read_only=True)
    education_out = serializers.SerializerMethodField(read_only=True)
    experience_out = serializers.SerializerMethodField(read_only=True)
    certifications_out = serializers.SerializerMethodField(read_only=True)
    projects_out = serializers.SerializerMethodField(read_only=True)
    languages_out = serializers.SerializerMethodField(read_only=True)
    social_links_out = serializers.SerializerMethodField(read_only=True)

    def get_skills_out(self, obj):
        skills = UserSkill.objects.filter(user=obj).select_related("skill")
        return UserSkillListSerializer(skills, many=True).data

    def get_interests_out(self, obj):
        """Return interests as a flat list of name strings for frontend compatibility."""
        interests = UserInterest.objects.filter(user=obj).select_related("interest")
        return [ui.interest.name for ui in interests]

    def get_education_out(self, obj):
        educations = UserEducation.objects.filter(user=obj)
        return UserEducationSerializer(educations, many=True).data

    def get_experience_out(self, obj):
        experiences = UserExperience.objects.filter(user=obj)
        return UserExperienceSerializer(experiences, many=True).data

    def get_certifications_out(self, obj):
        certifications = UserCertification.objects.filter(user=obj)
        return UserCertificationSerializer(certifications, many=True).data

    def get_projects_out(self, obj):
        projects = UserProject.objects.filter(user=obj)
        return UserProjectSerializer(projects, many=True).data

    def get_languages_out(self, obj):
        languages = UserLanguage.objects.filter(user=obj)
        return UserLanguageSerializer(languages, many=True).data

    def get_social_links_out(self, obj):
        social_links = UserSocialLink.objects.filter(user=obj)
        return UserSocialLinkSerializer(social_links, many=True).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Remap output fields to match frontend contract
        data['skills'] = data.pop('skills_out', [])
        data['interests'] = data.pop('interests_out', [])
        data['education'] = data.pop('education_out', [])
        data['experience'] = data.pop('experience_out', [])
        data['certifications'] = data.pop('certifications_out', [])
        data['projects'] = data.pop('projects_out', [])
        data['languages'] = data.pop('languages_out', [])
        data['social_links'] = data.pop('social_links_out', [])
        return data

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_profile_picture_url(self, obj):
        """Get profile picture URL if available."""
        return None

    def update(self, instance, validated_data):
        """Update user profile fields and related profile data (skills, interests, education, experience)."""
        import logging
        logger = logging.getLogger("profile.update")
        request = self.context.get("request")
        logger.info("[UserProfileSerializer.update] validated_data: %s", validated_data)

        # Update core user fields
        for field in ["first_name", "last_name", "phone", "location", "bio",
                      "linkedin_url", "github_url", "portfolio_url", "experience_level"]:
            if field in validated_data:
                logger.info("Updating field %s: %s", field, validated_data[field])
                setattr(instance, field, validated_data[field])
        instance.save()
        logger.info("Saved core user fields for user %s", instance.pk)

        # --- Handle skills ---
        skills = validated_data.get("skills")
        logger.info("Skills in validated_data: %s", skills)
        if skills is not None and request is not None:
            from apps.profile.models import Skill, UserSkill
            from django.utils.text import slugify
            UserSkill.objects.filter(user=instance).delete()
            for skill_name in skills:
                slug = slugify(skill_name)
                skill_obj, _ = Skill.objects.get_or_create(slug=slug, defaults={"name": skill_name})
                UserSkill.objects.create(user=instance, skill=skill_obj)
            logger.info("Saved %d skills for user %s", len(skills), instance.pk)

        # --- Handle interests ---
        interests = validated_data.get("interests")
        logger.info("Interests in validated_data: %s", interests)
        if interests is not None and request is not None:
            from apps.profile.models import Interest, UserInterest
            from django.utils.text import slugify
            UserInterest.objects.filter(user=instance).delete()
            seen_interest_slugs = set()
            for interest_name in interests:
                cleaned_name = str(interest_name).strip()
                if not cleaned_name:
                    continue

                slug = slugify(cleaned_name)
                if not slug or slug in seen_interest_slugs:
                    continue
                seen_interest_slugs.add(slug)

                interest_obj, _ = Interest.objects.get_or_create(
                    slug=slug,
                    defaults={"name": cleaned_name}
                )
                UserInterest.objects.create(user=instance, interest=interest_obj)
            logger.info("Saved %d interests for user %s", len(seen_interest_slugs), instance.pk)

        # --- Handle education ---
        education = validated_data.get("education")
        logger.info("Education in validated_data: %s", education)
        if education is not None and request is not None:
            from apps.profile.models import UserEducation
            UserEducation.objects.filter(user=instance).delete()
            for edu in education:
                edu["user"] = instance
                serializer = UserEducationSerializer(data=edu, context={"request": request})
                if not serializer.is_valid():
                    logger.error("Education serializer invalid: %s", serializer.errors)
                serializer.is_valid(raise_exception=True)
                serializer.save()
            logger.info("Saved %d education records for user %s", len(education), instance.pk)

        # --- Handle experience ---
        experience = validated_data.get("experience")
        logger.info("Experience in validated_data: %s", experience)
        if experience is not None and request is not None:
            from apps.profile.models import UserExperience
            UserExperience.objects.filter(user=instance).delete()
            for exp in experience:
                exp["user"] = instance
                serializer = UserExperienceSerializer(data=exp, context={"request": request})
                if not serializer.is_valid():
                    logger.error("Experience serializer invalid: %s", serializer.errors)
                serializer.is_valid(raise_exception=True)
                serializer.save()
            logger.info("Saved %d experience records for user %s", len(experience), instance.pk)

        # --- Handle certifications ---
        certifications_data = validated_data.get("certifications")
        logger.info("Certifications in validated_data: %s", certifications_data)
        if certifications_data is not None and request is not None:
            from apps.profile.models import UserCertification
            UserCertification.objects.filter(user=instance).delete()
            for cert in certifications_data:
                cert = {k: v for k, v in cert.items() if k not in (
                    "id", "is_verified", "verified_at", "is_expired",
                    "created_at", "updated_at", "related_skills"
                )}
                cert["user"] = instance
                s = UserCertificationSerializer(data=cert, context={"request": request})
                if s.is_valid():
                    s.save()
                else:
                    logger.error("Certification serializer invalid: %s", s.errors)
            logger.info("Saved %d certifications for user %s", len(certifications_data), instance.pk)

        # --- Handle languages ---
        languages_data = validated_data.get("languages")
        logger.info("Languages in validated_data: %s", languages_data)
        if languages_data is not None and request is not None:
            from apps.profile.models import UserLanguage
            UserLanguage.objects.filter(user=instance).delete()
            for lang in languages_data:
                lang = {k: v for k, v in lang.items() if k not in (
                    "id", "is_verified", "created_at", "updated_at", "proficiency_display"
                )}
                # Ensure language_code is set (required field)
                if not lang.get("language_code") and lang.get("language_name"):
                    lang["language_code"] = lang["language_name"].lower().replace(" ", "_")[:10]
                lang["user"] = instance
                s = UserLanguageSerializer(data=lang, context={"request": request})
                if s.is_valid():
                    s.save()
                else:
                    logger.error("Language serializer invalid: %s", s.errors)
            logger.info("Saved %d languages for user %s", len(languages_data), instance.pk)

        # --- Handle projects ---
        projects_data = validated_data.get("projects")
        logger.info("Projects in validated_data: %s", projects_data)
        if projects_data is not None and request is not None:
            from apps.profile.models import UserProject
            UserProject.objects.filter(user=instance).delete()
            for proj in projects_data:
                proj = {k: v for k, v in proj.items() if k not in (
                    "id", "view_count", "created_at", "updated_at",
                    "related_skills", "status_display"
                )}
                proj["user"] = instance
                s = UserProjectSerializer(data=proj, context={"request": request})
                if s.is_valid():
                    s.save()
                else:
                    logger.error("Project serializer invalid: %s", s.errors)
            logger.info("Saved %d projects for user %s", len(projects_data), instance.pk)

        # --- Handle social_links ---
        social_links_data = validated_data.get("social_links")
        logger.info("Social links in validated_data: %s", social_links_data)
        if social_links_data is not None and request is not None:
            from apps.profile.models import UserSocialLink
            UserSocialLink.objects.filter(user=instance).delete()
            for link in social_links_data:
                link = {k: v for k, v in link.items() if k not in (
                    "id", "is_verified", "created_at", "updated_at", "platform_display"
                )}
                link["user"] = instance
                s = UserSocialLinkSerializer(data=link, context={"request": request})
                if s.is_valid():
                    s.save()
                else:
                    logger.error("Social link serializer invalid: %s", s.errors)
            logger.info("Saved %d social links for user %s", len(social_links_data), instance.pk)

        return instance


class ProfilePictureSerializer(serializers.Serializer):
    """Serializer for profile picture upload."""
    
    picture = serializers.ImageField(write_only=True)
    profile_picture_url = serializers.SerializerMethodField()
    
    def get_profile_picture_url(self, obj):
        """Return the uploaded picture URL."""
        # This will be implemented when file storage is configured
        return None
    
    def update(self, instance, validated_data):
        """Handle picture upload."""
        # For now, just return the instance
        # Full implementation requires file storage configuration
        return instance
