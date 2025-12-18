"""
Management command to import Knowledge Graph quality frameworks data from Word documents or PDF files.

Usage:
    python manage.py import_document path/to/document.docx
    python manage.py import_document path/to/document.pdf

The document should contain tables or structured data with framework information.
Supports both .docx and .pdf formats.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import os
import re
from frameworks.models import Framework, Criterion, Definition

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False


class Command(BaseCommand):
    help = 'Import Knowledge Graph quality frameworks from a Word document (.docx) or PDF file (.pdf)'

    def add_arguments(self, parser):
        parser.add_argument('document_file', type=str, help='Path to the document (.docx or .pdf)')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without actually saving data to database',
        )

    def detect_file_type(self, file_path):
        """Detect the actual file type by reading file header"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(8)
                # DOCX files start with PK (ZIP signature)
                if header.startswith(b'PK'):
                    return 'docx'
                # PDF files start with %PDF
                elif header.startswith(b'%PDF'):
                    return 'pdf'
        except:
            pass
        return None

    def handle(self, *args, **options):
        document_path = options['document_file']
        dry_run = options['dry_run']

        if not os.path.exists(document_path):
            raise CommandError(f'File not found: {document_path}')

        file_ext = os.path.splitext(document_path)[1].lower()
        
        # Detect actual file type (in case file extension doesn't match)
        actual_type = self.detect_file_type(document_path)
        
        try:
            if file_ext == '.docx' or actual_type == 'docx':
                if not DOCX_AVAILABLE:
                    raise CommandError('python-docx is not installed. Install it with: pip install python-docx')
                doc = Document(document_path)
                self.stdout.write(self.style.SUCCESS(f'Opened DOCX document: {document_path}'))
                frameworks_data = self.parse_docx(doc)
            elif file_ext == '.pdf' or actual_type == 'pdf':
                if not PDFPLUMBER_AVAILABLE and not PYPDF2_AVAILABLE:
                    raise CommandError('PDF library is not installed. Install with: pip install pdfplumber PyPDF2')
                self.stdout.write(self.style.SUCCESS(f'Opened PDF document: {document_path}'))
                frameworks_data = self.parse_pdf(document_path)
            else:
                # Try DOCX first if extension is unknown
                if DOCX_AVAILABLE:
                    try:
                        doc = Document(document_path)
                        self.stdout.write(self.style.SUCCESS(f'Detected DOCX format: {document_path}'))
                        frameworks_data = self.parse_docx(doc)
                    except:
                        raise CommandError(f'Unsupported file format: {file_ext}. Supported formats: .docx, .pdf')
                else:
                    raise CommandError(f'Unsupported file format: {file_ext}. Supported formats: .docx, .pdf')
            
            if dry_run:
                self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be saved'))
            
            self.stdout.write(self.style.SUCCESS(f'Found {len(frameworks_data)} frameworks'))
            
            if not dry_run:
                with transaction.atomic():
                    imported_count = self.import_frameworks(frameworks_data)
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully imported {imported_count} frameworks')
                    )
            else:
                self.stdout.write('Would import:')
                for fw_data in frameworks_data:
                    self.stdout.write(f"  - {fw_data.get('name', 'Unknown')}")
                    
        except Exception as e:
            raise CommandError(f'Error importing document: {str(e)}')

    def parse_docx(self, doc):
        """Parse DOCX document to extract framework data"""
        frameworks_data = []
        
        # Parse tables first (more reliable for structured data)
        # This document uses tables, so we prioritize table parsing
        for table in doc.tables:
            frameworks_from_table = self.parse_table(table)
            frameworks_data.extend(frameworks_from_table)
        
        # Only parse paragraphs if no tables found
        if not doc.tables:
            current_framework = None
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                
                # Skip document headers
                if text.lower().startswith(('comprehensive', 'the following', 'table present', 'literature review')):
                    continue
                
                # Try to detect framework headers
                framework_match = re.search(r'([A-Z][a-z]+(?:\s+et\s+al\.)?)\s*(\d{4})?', text, re.IGNORECASE)
                if framework_match:
                    if current_framework:
                        frameworks_data.append(current_framework)
                    
                    authors = framework_match.group(1)
                    year = int(framework_match.group(2)) if framework_match.group(2) else None
                    
                    current_framework = {
                        'name': f"{authors} {year}" if year else authors,
                        'authors': authors,
                        'year': year,
                        'title': '',
                        'description': '',
                        'source': '',
                        'criteria': [],
                    }
                elif current_framework:
                    # Try to detect criteria
                    criterion_patterns = [
                        r'(Completeness|Accuracy|Consistency|Conciseness|Timeliness|Relevancy|Interoperability|Availability|Usability)',
                        r'Criterion[:\s]+([A-Z][a-z]+)',
                    ]
                    
                    for pattern in criterion_patterns:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            criterion_name = match.group(1) if match.groups() else match.group(0)
                            current_framework['criteria'].append({
                                'name': criterion_name.strip(),
                                'description': text,
                                'category': '',
                                'definitions': [text] if len(text) > 50 else [],
                            })
                            break
            
            if current_framework:
                frameworks_data.append(current_framework)
        
        return frameworks_data

    def parse_pdf(self, pdf_path):
        """Parse PDF document to extract framework data"""
        frameworks_data = []
        
        # Try pdfplumber first (better for tables)
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    all_text = []
                    tables_data = []
                    
                    for page in pdf.pages:
                        # Extract text
                        text = page.extract_text()
                        if text:
                            all_text.append(text)
                        
                        # Extract tables
                        tables = page.extract_tables()
                        if tables:
                            tables_data.extend(tables)
                    
                    # Parse text content
                    full_text = '\n'.join(all_text)
                    frameworks_from_text = self.parse_text_content(full_text)
                    frameworks_data.extend(frameworks_from_text)
                    
                    # Parse tables
                    for table in tables_data:
                        frameworks_from_table = self.parse_pdf_table(table)
                        frameworks_data.extend(frameworks_from_table)
                    
                    return frameworks_data
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'pdfplumber parsing failed: {e}, trying PyPDF2'))
        
        # Fallback to PyPDF2
        if PYPDF2_AVAILABLE:
            try:
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    all_text = []
                    
                    for page_num, page in enumerate(pdf_reader.pages):
                        try:
                            text = page.extract_text()
                            if text:
                                all_text.append(text)
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f'Error extracting text from page {page_num + 1}: {e}'))
                            continue
                    
                    full_text = '\n'.join(all_text)
                    if not full_text.strip():
                        raise CommandError('No text could be extracted from PDF. The PDF might be image-based or corrupted.')
                    frameworks_data = self.parse_text_content(full_text)
                    return frameworks_data
            except Exception as e:
                raise CommandError(f'Failed to parse PDF with PyPDF2: {e}')
        
        raise CommandError('No PDF parsing library available')

    def parse_text_content(self, text):
        """Parse text content to extract framework data"""
        frameworks_data = []
        current_framework = None
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to detect framework headers
            # Pattern: "Author et al. (Year)" or "Author (Year)" or "Framework Name"
            framework_patterns = [
                r'([A-Z][a-z]+(?:\s+et\s+al\.)?)\s*\(?(\d{4})\)?',
                r'Framework[:\s]+([A-Z][^\(]+)',
                r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(\d{4})',
            ]
            
            for pattern in framework_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    if current_framework:
                        frameworks_data.append(current_framework)
                    
                    authors = match.group(1).strip() if match.groups() else match.group(0)
                    year = int(match.group(2)) if len(match.groups()) > 1 and match.group(2) else None
                    
                    current_framework = {
                        'name': f"{authors} {year}" if year else authors,
                        'authors': authors,
                        'year': year,
                        'title': '',
                        'description': '',
                        'source': '',
                        'criteria': [],
                    }
                    break
            
            # Try to detect criteria
            if current_framework:
                criterion_patterns = [
                    r'^\s*[-•]\s*(Completeness|Accuracy|Consistency|Conciseness|Timeliness|Relevancy|Interoperability|Availability|Usability|Correctness|Currency|Coverage)',
                    r'(Completeness|Accuracy|Consistency|Conciseness|Timeliness|Relevancy|Interoperability|Availability|Usability|Correctness|Currency|Coverage)[:\s]+',
                    r'Criterion[:\s]+([A-Z][a-z]+)',
                    r'^\s*\d+\.\s*([A-Z][a-z]+)',
                ]
                
                for pattern in criterion_patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        criterion_name = match.group(1) if match.groups() else match.group(0)
                        # Get description (rest of the line or next lines)
                        description = line.replace(match.group(0), '').strip()
                        
                        current_framework['criteria'].append({
                            'name': criterion_name.strip(),
                            'description': description,
                            'category': '',
                            'definitions': [description] if description else [],
                        })
                        break
        
        if current_framework:
            frameworks_data.append(current_framework)
        
        return frameworks_data

    def parse_pdf_table(self, table):
        """Parse PDF table to extract framework data"""
        frameworks_data = []
        
        if not table or len(table) == 0:
            return frameworks_data
        
        # Try to detect header row
        header_row = table[0] if len(table) > 0 else []
        headers = [str(cell).strip() if cell else '' for cell in header_row]
        
        # Look for common column names
        framework_col = None
        criterion_col = None
        definition_col = None
        
        for i, header in enumerate(headers):
            header_lower = str(header).lower()
            if 'framework' in header_lower or 'author' in header_lower or 'source' in header_lower:
                framework_col = i
            elif 'criterion' in header_lower or 'metric' in header_lower or 'dimension' in header_lower:
                criterion_col = i
            elif 'definition' in header_lower or 'description' in header_lower:
                definition_col = i
        
        # Group rows by framework
        current_framework = None
        for row in table[1:]:  # Skip header
            if not row:
                continue
            
            cells = [str(cell).strip() if cell else '' for cell in row]
            
            if framework_col is not None and framework_col < len(cells):
                framework_name = cells[framework_col]
                if framework_name:
                    if current_framework:
                        frameworks_data.append(current_framework)
                    
                    # Extract year from framework name if present
                    year_match = re.search(r'(\d{4})', framework_name)
                    year = int(year_match.group(1)) if year_match else None
                    
                    current_framework = {
                        'name': framework_name,
                        'authors': framework_name.split()[0] if framework_name else '',
                        'year': year,
                        'title': '',
                        'description': '',
                        'source': '',
                        'criteria': [],
                    }
            
            if current_framework and criterion_col is not None and criterion_col < len(cells):
                criterion_name = cells[criterion_col] if criterion_col < len(cells) else ''
                definition_text = cells[definition_col] if definition_col is not None and definition_col < len(cells) else ''
                
                if criterion_name:
                    current_framework['criteria'].append({
                        'name': criterion_name,
                        'description': definition_text,
                        'category': '',
                        'definitions': [definition_text] if definition_text else [],
                    })
        
        if current_framework:
            frameworks_data.append(current_framework)
        
        return frameworks_data

    def parse_table(self, table):
        """Parse DOCX table to extract framework data"""
        frameworks_data = []
        
        if not table.rows or len(table.rows) < 2:
            return frameworks_data
        
        # Get header row
        header_row = table.rows[0]
        headers = [cell.text.strip().lower() for cell in header_row.cells]
        
        # Find column indices for our specific table structure
        title_col = None
        year_col = None
        dimensions_col = None
        abstract_col = None
        objectives_col = None
        methodology_col = None
        algorithm_col = None
        top_model_col = None
        accuracy_col = None
        advantages_col = None
        drawbacks_col = None
        reference_col = None
        
        for i, header in enumerate(headers):
            if 'title' in header:
                title_col = i
            elif 'year' in header or 'published' in header:
                year_col = i
            elif 'dimension' in header:
                dimensions_col = i
            elif 'abstract' in header:
                abstract_col = i
            elif 'objective' in header:
                objectives_col = i
            elif 'methodology' in header:
                methodology_col = i
            elif 'algorithm' in header:
                algorithm_col = i
            elif 'top model' in header or 'topmodel' in header.replace(' ', '').lower():
                top_model_col = i
            elif 'accuracy' in header:
                accuracy_col = i
            elif 'advantage' in header:
                advantages_col = i
            elif 'drawback' in header:
                drawbacks_col = i
            elif 'reference' in header:
                reference_col = i
        
        # Parse each data row
        for row in table.rows[1:]:  # Skip header
            cells = [cell.text.strip() for cell in row.cells]
            
            # Extract framework information
            title = cells[title_col] if title_col is not None and title_col < len(cells) else ''
            year_str = cells[year_col] if year_col is not None and year_col < len(cells) else ''
            dimensions = cells[dimensions_col] if dimensions_col is not None and dimensions_col < len(cells) else ''
            abstract = cells[abstract_col] if abstract_col is not None and abstract_col < len(cells) else ''
            objectives = cells[objectives_col] if objectives_col is not None and objectives_col < len(cells) else ''
            methodology = cells[methodology_col] if methodology_col is not None and methodology_col < len(cells) else ''
            algorithm_used = cells[algorithm_col] if algorithm_col is not None and algorithm_col < len(cells) else ''
            top_model = cells[top_model_col] if top_model_col is not None and top_model_col < len(cells) else ''
            accuracy = cells[accuracy_col] if accuracy_col is not None and accuracy_col < len(cells) else ''
            advantages = cells[advantages_col] if advantages_col is not None and advantages_col < len(cells) else ''
            drawbacks = cells[drawbacks_col] if drawbacks_col is not None and drawbacks_col < len(cells) else ''
            reference = cells[reference_col] if reference_col is not None and reference_col < len(cells) else ''
            
            # Skip if title is too short or looks like a document header
            if not title or len(title) < 10 or title.lower().startswith(('comprehensive', 'the following', 'table present', 'the')):
                continue
            
            # Extract year
            year = None
            if year_str:
                year_match = re.search(r'(\d{4})', year_str)
                if year_match:
                    try:
                        year = int(year_match.group(1))
                    except ValueError:
                        pass
            
            # If no year found in year column, try to extract from title
            if not year:
                year_match = re.search(r'\((\d{4})\)', title)
                if year_match:
                    try:
                        year = int(year_match.group(1))
                    except ValueError:
                        pass
            
            # Extract authors from title or reference
            # Since reference column just says "Read", we'll try to extract from title
            # or leave empty if title doesn't contain author info
            authors = ''
            
            # Try reference column first (though it usually just says "Read")
            if reference and reference.lower() != 'read':
                author_match = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+et\s+al\.)?)', reference)
                if author_match:
                    authors = author_match.group(1).strip()
            
            # If no authors from reference, try title patterns
            if not authors and title:
                # Look for common author patterns in titles
                # Pattern: "Author et al. - Title" or "Author: Title"
                title_clean = re.sub(r'\s*\(?\d{4}\)?', '', title)
                
                # Check if title starts with what looks like an author name (short, capitalized words)
                parts = re.split(r'[:\-–]', title_clean, 1)
                if parts and len(parts) > 0:
                    first_part = parts[0].strip()
                    words = first_part.split()
                    # If first part is short (likely author), use it
                    if len(words) <= 4 and len(first_part) < 50:
                        # Check if it looks like an author name (starts with capital, has 2-4 words)
                        if all(w[0].isupper() if w else False for w in words[:2]):
                            authors = first_part
                
                # If still no authors, leave empty (will be stored as empty string)
            
            # Parse dimensions/criteria
            criteria = []
            if dimensions:
                # Normalize the dimensions string - replace newlines with spaces first
                dimensions_normalized = re.sub(r'\s+', ' ', dimensions)
                
                # Handle special cases where words are split (e.g., "Syntactic\nValidity" -> "Syntactic Validity")
                # Join words that might have been split: "Syntactic Validity", "Semantic Accuracy", etc.
                dimensions_normalized = re.sub(r'\b(Syntactic|Semantic|Representational)\s+([A-Z][a-z]+)', r'\1 \2', dimensions_normalized)
                
                # Split by comma or semicolon
                dim_list = re.split(r'[,;]+', dimensions_normalized)
                
                seen_dimensions = set()  # Avoid duplicates
                
                for dim in dim_list:
                    dim = dim.strip()
                    # Filter out very short strings and common non-dimension words
                    if dim and len(dim) > 2 and dim.lower() not in ['n/a', 'na', 'read', 'and', 'or', 'the']:
                        # Clean up common prefixes that might be split across lines
                        dim = re.sub(r'^(Syntactic|Semantic|Representational)[\s-]+', '', dim, flags=re.IGNORECASE)
                        # Remove trailing periods and dashes
                        dim = dim.rstrip('.-').strip()
                        
                        # Skip if it's just a single letter, number, or common words
                        if dim and len(dim) > 2 and not re.match(r'^[\d\s]+$', dim):
                            # Capitalize first letter
                            dim = dim[0].upper() + dim[1:] if len(dim) > 1 else dim
                            
                            # Avoid duplicates (case-insensitive)
                            dim_lower = dim.lower()
                            if dim_lower not in seen_dimensions:
                                seen_dimensions.add(dim_lower)
                                criteria.append({
                                    'name': dim,
                                    'description': f"Quality dimension from {title}",
                                    'category': '',
                                    'definitions': [f"Quality dimension from {title} ({year})"] if year else [f"Quality dimension from {title}"],
                                })
            
            # Create framework entry
            framework_data = {
                'name': title,
                'authors': authors,
                'year': year,
                'title': title,
                'description': abstract if abstract else '',
                'objectives': objectives if objectives else '',
                'methodology': methodology if methodology else '',
                'algorithm_used': algorithm_used if algorithm_used else '',
                'top_model': top_model if top_model else '',
                'accuracy': accuracy if accuracy else '',
                'advantages': advantages if advantages else '',
                'drawbacks': drawbacks if drawbacks else '',
                'source': reference if reference else '',
                'criteria': criteria,
            }
            
            frameworks_data.append(framework_data)
        
        return frameworks_data

    def import_frameworks(self, frameworks_data):
        """Import frameworks data into the database"""
        imported_count = 0
        
        for fw_data in frameworks_data:
            # Create or get framework
            framework, created = Framework.objects.get_or_create(
                name=fw_data['name'],
                defaults={
                    'authors': fw_data.get('authors', ''),
                    'year': fw_data.get('year'),
                    'title': fw_data.get('title', ''),
                    'description': fw_data.get('description', ''),
                    'objectives': fw_data.get('objectives', ''),
                    'methodology': fw_data.get('methodology', ''),
                    'algorithm_used': fw_data.get('algorithm_used', ''),
                    'top_model': fw_data.get('top_model', ''),
                    'accuracy': fw_data.get('accuracy', ''),
                    'advantages': fw_data.get('advantages', ''),
                    'drawbacks': fw_data.get('drawbacks', ''),
                    'source': fw_data.get('source', ''),
                }
            )
            
            # Update existing framework if it was already there
            if not created:
                framework.authors = fw_data.get('authors', '')
                framework.year = fw_data.get('year')
                framework.title = fw_data.get('title', '')
                framework.description = fw_data.get('description', '')
                framework.objectives = fw_data.get('objectives', '')
                framework.methodology = fw_data.get('methodology', '')
                framework.algorithm_used = fw_data.get('algorithm_used', '')
                framework.top_model = fw_data.get('top_model', '')
                framework.accuracy = fw_data.get('accuracy', '')
                framework.advantages = fw_data.get('advantages', '')
                framework.drawbacks = fw_data.get('drawbacks', '')
                framework.source = fw_data.get('source', '')
                framework.save()
            
            if created:
                imported_count += 1
                self.stdout.write(f'Created framework: {framework.name}')
            
            # Import criteria
            for idx, criterion_data in enumerate(fw_data.get('criteria', [])):
                criterion, _ = Criterion.objects.get_or_create(
                    framework=framework,
                    name=criterion_data['name'],
                    defaults={
                        'description': criterion_data.get('description', ''),
                        'category': criterion_data.get('category', ''),
                        'order': idx,
                    }
                )
                
                # Import definitions
                for definition_text in criterion_data.get('definitions', []):
                    if definition_text.strip():
                        Definition.objects.get_or_create(
                            criterion=criterion,
                            definition_text=definition_text.strip(),
                            defaults={
                                'notes': '',
                            }
                        )
        
        return imported_count
