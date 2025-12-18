from django.contrib import admin
from .models import Framework, Criterion, Definition


@admin.register(Framework)
class FrameworkAdmin(admin.ModelAdmin):
    list_display = ['name', 'authors', 'year', 'title', 'created_at']
    list_filter = ['year', 'created_at']
    search_fields = ['name', 'authors', 'title', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Criterion)
class CriterionAdmin(admin.ModelAdmin):
    list_display = ['name', 'framework', 'category', 'order']
    list_filter = ['framework', 'category']
    search_fields = ['name', 'description', 'framework__name']
    ordering = ['framework', 'order', 'name']


@admin.register(Definition)
class DefinitionAdmin(admin.ModelAdmin):
    list_display = ['criterion', 'definition_text_preview', 'created_at']
    list_filter = ['criterion__framework', 'created_at']
    search_fields = ['definition_text', 'criterion__name', 'notes']
    
    def definition_text_preview(self, obj):
        return obj.definition_text[:100] + "..." if len(obj.definition_text) > 100 else obj.definition_text
    definition_text_preview.short_description = 'Definition Preview'
