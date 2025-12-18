"""
Management command to force update criteria that have identical descriptions
across different frameworks to make them framework-specific.
"""
from django.core.management.base import BaseCommand
from frameworks.models import Criterion
from frameworks.llm_comparison import LLMComparisonEngine
from django.db.models import Count
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Force update criteria with identical descriptions across frameworks to be framework-specific'

    def handle(self, *args, **options):
        self.stdout.write('Initializing LLM engine...')
        engine = LLMComparisonEngine()
        
        if engine.provider == 'none':
            self.stdout.write(
                self.style.ERROR('No LLM provider available. Please configure HuggingFace, Ollama, or OpenAI.')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'Using LLM provider: {engine.provider}')
        )
        
        # Find criteria with identical descriptions across frameworks
        self.stdout.write('\nFinding criteria with duplicate descriptions...')
        duplicate_descriptions = Criterion.objects.values('name', 'description').annotate(
            count=Count('id')
        ).filter(
            count__gt=1,
            description__isnull=False
        ).exclude(description='')
        
        total_to_update = 0
        criteria_to_update = []
        
        for dup in duplicate_descriptions:
            criteria = Criterion.objects.filter(
                name=dup['name'],
                description=dup['description']
            ).select_related('framework').prefetch_related('definitions')
            
            # Only update if description is generic (not framework-specific)
            if len(dup['description']) < 200:  # Generic descriptions are usually shorter
                for criterion in criteria:
                    criteria_to_update.append(criterion)
                    total_to_update += 1
        
        self.stdout.write(f'Found {total_to_update} criteria with duplicate/generic descriptions to update')
        
        if total_to_update == 0:
            self.stdout.write(self.style.SUCCESS('No duplicate descriptions found!'))
            return
        
        updated_count = 0
        error_count = 0
        
        # Group by criterion name for context
        criteria_by_name = {}
        for criterion in criteria_to_update:
            name = criterion.name.strip()
            if name not in criteria_by_name:
                criteria_by_name[name] = []
            criteria_by_name[name].append(criterion)
        
        for idx, criterion in enumerate(criteria_to_update, 1):
            criterion_name = criterion.name.strip()
            framework = criterion.framework
            
            self.stdout.write(f'\n[{idx}/{total_to_update}] Updating: {criterion_name} in {framework.name}')
            
            # Get context from other frameworks with same criterion
            other_frameworks_data = []
            if criterion_name in criteria_by_name:
                for other_criterion in criteria_by_name[criterion_name]:
                    if other_criterion.id != criterion.id:
                        other_desc = other_criterion.description.strip() if other_criterion.description else ''
                        if other_desc:
                            other_frameworks_data.append({
                                'framework_name': other_criterion.framework.name,
                                'description': other_desc[:150]
                            })
            
            # Get definitions
            definitions = [d.definition_text.strip() for d in criterion.definitions.all() if d.definition_text.strip()]
            
            # Build framework data
            fw_data = {
                'has_criterion': True,
                'description': criterion.description or '',
                'category': criterion.category or '',
                'definitions': definitions[:3]
            }
            
            # Get all framework data for context
            all_framework_data = []
            if criterion_name in criteria_by_name:
                for other_criterion in criteria_by_name[criterion_name]:
                    if other_criterion.id != criterion.id:
                        other_defs = [d.definition_text.strip() for d in other_criterion.definitions.all() if d.definition_text.strip()]
                        all_framework_data.append({
                            'has_criterion': True,
                            'description': other_criterion.description.strip() if other_criterion.description else '',
                            'category': other_criterion.category or '',
                            'definitions': other_defs[:2]
                        })
            
            try:
                # Generate enhanced description
                enhanced_desc = engine.generate_enhanced_description(
                    criterion_name,
                    fw_data,
                    framework,
                    all_framework_data
                )
                
                if enhanced_desc and len(enhanced_desc.strip()) > 30:
                    criterion.description = enhanced_desc.strip()
                    criterion.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Updated: {enhanced_desc[:80]}...')
                    )
                    updated_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(f'  → No valid description generated')
                    )
                    error_count += 1
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error: {str(e)}')
                )
                logger.error(f'Error updating {criterion_name} in {framework.name}: {e}', exc_info=True)
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Updated: {updated_count}, Errors: {error_count}'
            )
        )
