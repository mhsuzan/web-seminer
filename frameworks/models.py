from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Framework(models.Model):
    """Represents a Knowledge Graph quality framework from literature"""
    name = models.CharField(max_length=200, help_text="Name of the framework (e.g., 'Chen et al. 2019')")
    authors = models.CharField(max_length=500, blank=True, help_text="Authors of the framework")
    year = models.IntegerField(
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
        null=True,
        blank=True,
        help_text="Publication year"
    )
    title = models.CharField(max_length=500, blank=True, help_text="Title of the paper")
    description = models.TextField(blank=True, help_text="Description of the framework")
    source = models.CharField(max_length=500, blank=True, help_text="Source/venue of publication")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year', 'name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['year']),
        ]

    def __str__(self):
        return f"{self.name} ({self.year})" if self.year else self.name


class Criterion(models.Model):
    """Represents a quality criterion/metric in a framework"""
    name = models.CharField(max_length=200, db_index=True, help_text="Name of the criterion (e.g., 'Completeness')")
    framework = models.ForeignKey(Framework, on_delete=models.CASCADE, related_name='criteria')
    description = models.TextField(blank=True, help_text="Description of the criterion")
    category = models.CharField(max_length=100, blank=True, help_text="Category/group of the criterion")
    order = models.IntegerField(default=0, help_text="Order within the framework")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['framework', 'order', 'name']
        unique_together = [['framework', 'name']]
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['framework', 'name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.framework.name})"


class Definition(models.Model):
    """Represents a definition of a criterion, which may vary across frameworks"""
    criterion = models.ForeignKey(Criterion, on_delete=models.CASCADE, related_name='definitions')
    definition_text = models.TextField(help_text="The definition text")
    notes = models.TextField(blank=True, help_text="Additional notes or context")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['criterion', 'id']

    def __str__(self):
        return f"Definition for {self.criterion.name}"
