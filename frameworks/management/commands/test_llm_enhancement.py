"""
Management command to test and verify LLM enhancement functionality.
"""
from django.core.management.base import BaseCommand
from frameworks.models import Framework, Criterion
from frameworks.llm_comparison import LLMComparisonEngine, enhance_comparison_with_llm
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test and verify LLM enhancement functionality'

    def handle(self, *args, **options):
        self.stdout.write('='*60)
        self.stdout.write('Testing LLM Enhancement Functionality')
        self.stdout.write('='*60)
        
        # Test 1: Check LLM provider
        self.stdout.write('\n[Test 1] Checking LLM Provider...')
        engine = LLMComparisonEngine()
        self.stdout.write(f'  Provider detected: {engine.provider}')
        
        if engine.provider == 'none':
            self.stdout.write(
                self.style.ERROR('  ✗ No LLM provider available!')
            )
            self.stdout.write('\n  To fix this:')
            self.stdout.write('  1. For HuggingFace: Set HUGGINGFACE_API_KEY in settings.py')
            self.stdout.write('  2. For Ollama: Install and run: ollama pull llama3.2')
            self.stdout.write('  3. For OpenAI: Set OPENAI_API_KEY and USE_OPENAI=true')
            return
        else:
            self.stdout.write(
                self.style.SUCCESS(f'  ✓ LLM provider available: {engine.provider}')
            )
        
        # Test 2: Get test frameworks
        self.stdout.write('\n[Test 2] Getting test frameworks...')
        frameworks = Framework.objects.all()[:2]
        if frameworks.count() < 2:
            self.stdout.write(
                self.style.ERROR('  ✗ Need at least 2 frameworks in database')
            )
            return
        
        selected_frameworks = list(frameworks)
        self.stdout.write(
            self.style.SUCCESS(f'  ✓ Found {len(selected_frameworks)} frameworks:')
        )
        for fw in selected_frameworks:
            self.stdout.write(f'     - {fw.name} ({fw.criteria.count()} criteria)')
        
        # Test 3: Create test comparison data
        self.stdout.write('\n[Test 3] Creating test comparison data...')
        framework_ids = [fw.id for fw in selected_frameworks]
        criteria = Criterion.objects.filter(
            framework_id__in=framework_ids
        ).values_list('name', flat=True).distinct()[:5]
        
        comparison_data = []
        for criterion_name in criteria:
            criterion_rows = []
            for framework in selected_frameworks:
                criterion = Criterion.objects.filter(
                    framework=framework,
                    name__iexact=criterion_name
                ).select_related('framework').prefetch_related('definitions').first()
                
                if criterion:
                    definitions_list = []
                    for definition in criterion.definitions.all():
                        def_text = definition.definition_text.strip() if definition.definition_text else ''
                        if def_text:
                            definitions_list.append(def_text)
                    
                    criterion_rows.append({
                        'has_criterion': True,
                        'description': criterion.description or '',
                        'category': criterion.category or '',
                        'definitions': definitions_list[:2],
                    })
                else:
                    criterion_rows.append({
                        'has_criterion': False,
                    })
            
            comparison_data.append({
                'name': criterion_name,
                'framework_data': criterion_rows,
            })
        
        self.stdout.write(
            self.style.SUCCESS(f'  ✓ Created comparison data for {len(comparison_data)} criteria')
        )
        
        # Test 4: Test enhanced description generation
        self.stdout.write('\n[Test 4] Testing enhanced description generation...')
        if comparison_data:
            test_criterion = comparison_data[0]
            test_fw_data = test_criterion['framework_data'][0]
            if test_fw_data.get('has_criterion'):
                test_framework = selected_frameworks[0]
                try:
                    enhanced_desc = engine.generate_enhanced_description(
                        test_criterion['name'],
                        test_fw_data,
                        test_framework,
                        test_criterion['framework_data']
                    )
                    if enhanced_desc:
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ Generated enhanced description ({len(enhanced_desc)} chars)')
                        )
                        self.stdout.write(f'     Preview: {enhanced_desc[:100]}...')
                    else:
                        self.stdout.write(
                            self.style.WARNING('  ⚠ No description generated (may be normal if provider has issues)')
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Error generating description: {e}')
                    )
                    logger.error(f'Error in test: {e}', exc_info=True)
        
        # Test 5: Test full enhancement
        self.stdout.write('\n[Test 5] Testing full LLM enhancement...')
        try:
            result = enhance_comparison_with_llm(comparison_data, selected_frameworks)
            
            if result.get('enhanced'):
                self.stdout.write(
                    self.style.SUCCESS('  ✓ LLM enhancement completed successfully!')
                )
                self.stdout.write(f'     Provider: {result.get("provider", "unknown")}')
                self.stdout.write(f'     Semantic similarities: {len(result.get("semantic_similarities", {}))}')
                self.stdout.write(f'     Summaries: {len(result.get("summaries", {}))}')
                self.stdout.write(f'     Insights: {len(result.get("insights", {}))}')
                self.stdout.write(f'     Groups: {len(result.get("groups", {}))}')
                
                # Count enhanced descriptions
                enhanced_count = 0
                for criterion in result.get('comparison_data', []):
                    for fw_data in criterion.get('framework_data', []):
                        if fw_data.get('has_llm_enhancement'):
                            enhanced_count += 1
                self.stdout.write(f'     Enhanced descriptions: {enhanced_count}')
            else:
                error_msg = result.get('error', 'Unknown error')
                self.stdout.write(
                    self.style.ERROR(f'  ✗ LLM enhancement failed: {error_msg}')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ✗ Error in full enhancement: {e}')
            )
            logger.error(f'Error in full enhancement test: {e}', exc_info=True)
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write('Test Summary')
        self.stdout.write('='*60)
        self.stdout.write('\nIf all tests passed, LLM enhancement is working correctly!')
        self.stdout.write('If tests failed, check the error messages above for guidance.')
