"""
Management command to improve criteria descriptions with framework-specific, human-written descriptions.
"""
from django.core.management.base import BaseCommand
from frameworks.models import Criterion, Framework, Definition
import logging

logger = logging.getLogger(__name__)

# Framework-specific, criterion-specific descriptions
CRITERIA_DESCRIPTIONS = {
    'Accuracy': {
        'default': 'Measures how correct and error-free the knowledge graph data is. This includes checking if facts are true and relationships are accurate.',
        'specific': {
            'From Genesis to Maturity: Managing Knowledge Graph Ecosystems Through Life Cycles': 'Ensures that knowledge graph entities and relationships accurately represent real-world facts without errors or inconsistencies.',
            'Harnessing Diverse Perspectives: A Multi-Agent Framework for Enhanced Error Detection in Knowledge Graphs (MAKGED)': 'Evaluates the correctness of triples through multi-agent consensus, detecting errors in entity relationships and attributes.',
        }
    },
    'Completeness': {
        'default': 'Assesses how much of the expected knowledge is present in the graph. It checks if all relevant entities, relationships, and attributes are included.',
        'specific': {
            'From Genesis to Maturity: Managing Knowledge Graph Ecosystems Through Life Cycles': 'Measures the extent to which all expected knowledge graph components are present and properly represented.',
        }
    },
    'Consistency': {
        'default': 'Checks if the knowledge graph follows consistent rules and patterns. It ensures there are no contradictory facts or conflicting relationships.',
        'specific': {
            'From Genesis to Maturity: Managing Knowledge Graph Ecosystems Through Life Cycles': 'Ensures that knowledge graph data follows consistent representation patterns and avoids contradictory information.',
        }
    },
    'Consistent Representation': {
        'default': 'Evaluates whether entities and relationships are represented in a uniform and standardized way across the knowledge graph.',
    },
    'Timeliness': {
        'default': 'Measures how up-to-date the knowledge graph is. It checks if the information reflects current knowledge and is regularly updated.',
        'specific': {
            'From Genesis to Maturity: Managing Knowledge Graph Ecosystems Through Life Cycles': 'Assesses whether the knowledge graph contains current information and is maintained with regular updates.',
        }
    },
    'Reliability': {
        'default': 'Evaluates how trustworthy and dependable the knowledge graph is as a source of information.',
        'specific': {
            'From Genesis to Maturity: Managing Knowledge Graph Ecosystems Through Life Cycles': 'Measures the trustworthiness and dependability of knowledge graph data for decision-making and applications.',
        }
    },
    'Availability': {
        'default': 'Checks if the knowledge graph is accessible when needed and can be reliably accessed by users and applications.',
    },
    'Accessibility': {
        'default': 'Measures how easy it is for users to access and use the knowledge graph, including interface quality and documentation.',
    },
    'Security': {
        'default': 'Assesses how well the knowledge graph is protected against unauthorized access, data breaches, and security threats.',
        'specific': {
            'From Genesis to Maturity: Managing Knowledge Graph Ecosystems Through Life Cycles': 'Evaluates protection mechanisms against unauthorized access and ensures data security in knowledge graph systems.',
        }
    },
    'Scalability': {
        'default': 'Measures the ability of the knowledge graph to handle growth in size and complexity without performance degradation.',
        'specific': {
            'From Genesis to Maturity: Managing Knowledge Graph Ecosystems Through Life Cycles': 'Assesses the knowledge graph system\'s capacity to scale with increasing data volume and complexity.',
        }
    },
    'Reputation': {
        'default': 'Evaluates the credibility and standing of the knowledge graph based on its sources and track record.',
        'specific': {
            'From Genesis to Maturity: Managing Knowledge Graph Ecosystems Through Life Cycles': 'Measures the credibility and trustworthiness of knowledge graph sources and their historical reliability.',
        }
    },
    'Objectivity': {
        'default': 'Checks if the knowledge graph presents information in an unbiased and neutral manner, free from subjective interpretations.',
        'specific': {
            'Harnessing Diverse Perspectives: A Multi-Agent Framework for Enhanced Error Detection in Knowledge Graphs (MAKGED)': 'Ensures knowledge graph content is free from bias through multi-agent consensus and diverse perspective validation.',
        }
    },
    'Objectivity (Consensus)': {
        'default': 'Measures objectivity through consensus among multiple agents or validators, ensuring unbiased representation.',
    },
    'Believability': {
        'default': 'Assesses how credible and believable the information in the knowledge graph appears to users.',
    },
    'Credibility': {
        'default': 'Evaluates the trustworthiness and reliability of the knowledge graph based on source quality and verification.',
    },
    'Conciseness': {
        'default': 'Measures how efficiently information is represented without unnecessary redundancy or verbosity.',
    },
    'Concise Representation': {
        'default': 'Evaluates whether knowledge graph entities and relationships are represented in a compact and efficient manner.',
    },
    'Appropriate Amount': {
        'default': 'Checks if the knowledge graph contains the right amount of information - not too little, not too much.',
    },
    'Compliance': {
        'default': 'Assesses whether the knowledge graph adheres to relevant standards, regulations, and best practices.',
    },
    'Confidentiality': {
        'default': 'Measures how well sensitive information is protected and kept confidential in the knowledge graph.',
    },
    'Currentness': {
        'default': 'Evaluates how current and up-to-date the information in the knowledge graph is.',
    },
    'Cost Effectiveness': {
        'default': 'Assesses the value provided by the knowledge graph relative to the costs of creating and maintaining it.',
    },
    'Value added': {
        'default': 'Measures the additional value that the knowledge graph provides beyond basic data storage.',
    },
}


class Command(BaseCommand):
    help = 'Improve criteria descriptions with framework-specific, human-written descriptions'

    def handle(self, *args, **options):
        self.stdout.write('Starting to improve criteria descriptions...')
        
        updated_count = 0
        skipped_count = 0
        
        for criterion in Criterion.objects.all():
            criterion_name = criterion.name.strip()
            framework_name = criterion.framework.name.strip()
            
            # Get description from our dictionary
            if criterion_name in CRITERIA_DESCRIPTIONS:
                desc_data = CRITERIA_DESCRIPTIONS[criterion_name]
                
                # Try framework-specific description first
                if 'specific' in desc_data and framework_name in desc_data['specific']:
                    new_description = desc_data['specific'][framework_name]
                elif 'default' in desc_data:
                    new_description = desc_data['default']
                else:
                    skipped_count += 1
                    continue
                
                # Only update if current description is empty, too short, or seems generic
                current_desc = criterion.description.strip() if criterion.description else ''
                should_update = (
                    not current_desc or 
                    len(current_desc) < 50 or
                    'Vision paper' in current_desc or
                    'addressing challenges' in current_desc.lower() or
                    'Introduces' in current_desc
                )
                
                if should_update:
                    criterion.description = new_description
                    criterion.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Updated: {criterion_name} in {framework_name}'
                        )
                    )
                else:
                    skipped_count += 1
            else:
                skipped_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Updated {updated_count} criteria, skipped {skipped_count} criteria.'
            )
        )
