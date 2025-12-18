"""
Management command to intelligently update criteria descriptions using LLM
and existing framework data for better comparison quality.
"""
from django.core.management.base import BaseCommand
from frameworks.models import Criterion, Framework, Definition
from frameworks.llm_comparison import LLMComparisonEngine
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Intelligently update criteria descriptions using LLM and existing framework data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--framework',
            type=str,
            help='Update criteria for a specific framework only',
        )
        parser.add_argument(
            '--criterion',
            type=str,
            help='Update a specific criterion across all frameworks',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        framework_filter = options.get('framework')
        criterion_filter = options.get('criterion')
        
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
        
        # Get criteria to update
        criteria_query = Criterion.objects.select_related('framework').prefetch_related('definitions')
        
        if framework_filter:
            criteria_query = criteria_query.filter(framework__name__icontains=framework_filter)
            self.stdout.write(f'Filtering by framework: {framework_filter}')
        
        if criterion_filter:
            criteria_query = criteria_query.filter(name__icontains=criterion_filter)
            self.stdout.write(f'Filtering by criterion: {criterion_filter}')
        
        criteria = list(criteria_query.all())
        total = len(criteria)
        
        if total == 0:
            self.stdout.write(self.style.WARNING('No criteria found to update.'))
            return
        
        self.stdout.write(f'Found {total} criteria to process...')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        # Group criteria by name to get context from other frameworks
        criteria_by_name = {}
        for criterion in criteria:
            name = criterion.name.strip()
            if name not in criteria_by_name:
                criteria_by_name[name] = []
            criteria_by_name[name].append(criterion)
        
        for idx, criterion in enumerate(criteria, 1):
            criterion_name = criterion.name.strip()
            framework = criterion.framework
            
            self.stdout.write(f'\n[{idx}/{total}] Processing: {criterion_name} in {framework.name}')
            
            # Check if description needs improvement
            current_desc = criterion.description.strip() if criterion.description else ''
            needs_update = (
                not current_desc or
                len(current_desc) < 30 or
                'Vision paper' in current_desc or
                'addressing challenges' in current_desc.lower() or
                'Introduces' in current_desc or
                'This paper' in current_desc or
                'We propose' in current_desc or
                'We introduce' in current_desc
            )
            
            if not needs_update and not options.get('force'):
                self.stdout.write(f'  → Skipping: Description already good ({len(current_desc)} chars)')
                skipped_count += 1
                continue
            
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
            
            # Get definitions for this criterion
            definitions = [d.definition_text.strip() for d in criterion.definitions.all() if d.definition_text.strip()]
            
            # Build framework data structure for LLM
            fw_data = {
                'has_criterion': True,
                'description': current_desc,
                'category': criterion.category or '',
                'definitions': definitions[:3]  # Limit to first 3 definitions
            }
            
            # Get all framework data for context (other frameworks with same criterion)
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
                # Generate enhanced description using LLM
                enhanced_desc = engine.generate_enhanced_description(
                    criterion_name,
                    fw_data,
                    framework,
                    all_framework_data
                )
                
                if enhanced_desc and len(enhanced_desc.strip()) > 20:
                    if dry_run:
                        self.stdout.write(
                            self.style.SUCCESS(f'  → Would update to: {enhanced_desc[:100]}...')
                        )
                    else:
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
                    skipped_count += 1
                    
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
                f'\nCompleted! Updated: {updated_count}, Skipped: {skipped_count}, Errors: {error_count}'
            )
        )
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\nThis was a DRY RUN - no changes were saved. Run without --dry-run to apply changes.')
            )
