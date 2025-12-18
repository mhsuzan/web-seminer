# Knowledge Graph Quality Frameworks Comparison Tool

A Django web application for comparing and analyzing Knowledge Graph quality frameworks and criteria catalogs from literature.

## Features

- **Framework Comparison**: Compare multiple frameworks side-by-side in table format
- **Criteria Search**: Search for specific criteria across all frameworks
- **Definition Comparison**: Compare different definitions of the same criterion across frameworks
- **Framework Browsing**: Browse all available frameworks with detailed information

## Questions This Tool Answers

- What are the similarities and differences between frameworks (e.g., Chen et al. 2019 vs Li et al. 2023)?
- Which frameworks include a specific criterion (e.g., "Completeness")?
- What are the different definitions of a criterion according to different catalogs?

## Installation

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up the database**:
   ```bash
   python manage.py migrate
   ```

3. **Create a superuser** (optional, for admin access):
   ```bash
   python manage.py createsuperuser
   ```

## Importing Data

To import frameworks data from a Word document (.docx) or PDF file (.pdf):

```bash
# Import from DOCX file
python manage.py import_document path/to/your/document.docx

# Import from PDF file
python manage.py import_document path/to/your/document.pdf
```

For a dry run (preview without saving):
```bash
python manage.py import_document path/to/your/document.pdf --dry-run
```

**Note**: The import script automatically detects the file type and supports both DOCX and PDF formats. It uses pattern matching to extract data from documents. You may need to customize the parsing logic in `frameworks/management/commands/import_document.py` based on your specific document format.

**Improved Features**:
- **Duplicate Detection**: The import script now intelligently detects and merges duplicate frameworks based on normalized names, years, and titles
- **Data Merging**: When updating existing frameworks, the script merges data intelligently, keeping the most complete information
- **Criteria Deduplication**: Automatically prevents duplicate criteria within the same framework
- **Definition Deduplication**: Removes near-duplicate definitions to keep data clean

**Legacy command**: The old `import_docx` command still works for backward compatibility, but `import_document` is recommended as it supports both formats.

### Cleaning Up Duplicate Data

If you have existing duplicate data in your database, you can clean it up using the cleanup command:

```bash
# Preview what would be cleaned (dry run)
python manage.py cleanup_duplicates --dry-run

# Actually clean up duplicates
python manage.py cleanup_duplicates
```

This command will:
- Merge duplicate frameworks (keeping the most complete one)
- Merge duplicate criteria within frameworks
- Remove duplicate definitions

### Manual Data Entry

You can also add data manually through the Django admin interface:
1. Start the development server: `python manage.py runserver`
2. Navigate to `http://localhost:8000/admin/`
3. Log in with your superuser credentials
4. Add frameworks, criteria, and definitions through the admin interface

## Running the Application

Start the development server:
```bash
python manage.py runserver
```

Then open your browser to `http://localhost:8000/`

## Usage

### Compare Frameworks

1. Navigate to "Compare Frameworks" in the navigation menu
2. Select two or more frameworks using checkboxes
3. Click "Compare Frameworks" to see a side-by-side comparison table
4. The comparison shows:
   - Framework details (year, title, description, objectives, methodology, etc.)
   - Criteria comparison with framework-specific descriptions
   - Similarities (criteria present in all frameworks)
   - Differences (criteria present in some but not all frameworks)
5. **Enable AI Enhancement**: Click "🤖 Enable AI Enhancement" for:
   - Semantic similarity detection
   - AI-generated comparison summaries
   - Framework-specific enhanced descriptions
   - Related criteria grouping

### Search Criteria

1. Navigate to "Search Criteria"
2. Enter a criterion name (e.g., "Completeness")
3. View results showing:
   - Which frameworks include that criterion
   - Framework-specific descriptions
   - Definitions for each framework
   - Links to view full framework details

### Compare Definitions

1. Navigate to "Criterion Definitions"
2. Select a criterion from the dropdown
3. View all definitions of that criterion across different frameworks
4. Compare how different frameworks define the same criterion

### Browse Frameworks

1. Navigate to "Frameworks" to see all available frameworks
2. Click on any framework to view:
   - Complete framework details
   - All criteria with descriptions and definitions
   - Link to compare with other frameworks
3. Use the "Edit" button to update framework information

### Source Management

1. Navigate to "Sources" to view frameworks grouped by publication source
2. Click on a source to see all frameworks from that publication
3. Use bulk update to change source names for multiple frameworks
4. Edit individual framework sources from the framework detail page

## Project Structure

```
seminer/
├── kg_quality/          # Django project settings
├── frameworks/          # Main application
│   ├── models.py       # Database models (Framework, Criterion, Definition)
│   ├── views.py        # View functions
│   ├── urls.py         # URL routing
│   ├── admin.py        # Admin interface configuration
│   ├── templates/      # HTML templates
│   └── management/     # Management commands
│       └── commands/
│           ├── import_docx.py        # Legacy DOCX-only import (backward compatibility)
│           ├── import_document.py    # Enhanced import supporting DOCX and PDF
│           └── cleanup_duplicates.py # Clean up duplicate frameworks, criteria, and definitions
├── manage.py           # Django management script
├── requirements.txt    # Python dependencies
└── db.sqlite3         # SQLite database (created after migration)
```

## Database Models

- **Framework**: Represents a Knowledge Graph quality framework from literature
  - Fields: name, authors, year, title, description, objectives, methodology, algorithm_used, top_model, accuracy, advantages, drawbacks, source
  - Unique constraint: name (with intelligent duplicate detection during import)

- **Criterion**: Represents a quality criterion/metric in a framework
  - Fields: name, framework (FK), description, category, order
  - Unique constraint: (framework, name) - prevents duplicate criteria within a framework

- **Definition**: Represents a definition of a criterion
  - Fields: criterion (FK), definition_text, notes
  - Duplicate detection: Similar definitions are automatically detected and merged

## Customization

The import script (`import_document.py`) uses pattern matching to extract data from Word documents and PDF files. You may need to customize:

1. **Framework detection patterns**: Modify regex patterns in `parse_text_content()` or `parse_docx()` to match your document's format
2. **Table parsing**: Adjust `parse_table()` or `parse_pdf_table()` to handle your specific table structure
3. **Criterion extraction**: Update criterion detection patterns based on how criteria are named in your document
4. **PDF parsing**: The script uses `pdfplumber` (preferred) and falls back to `PyPDF2` for PDF files

## API Endpoints

- `/api/frameworks/` - JSON list of all frameworks
- `/api/criteria/?q=<query>` - JSON search results for criteria

## Technologies Used

- Django 6.0+
- SQLite (default database)
- python-docx (for Word document parsing)
- pdfplumber & PyPDF2 (for PDF document parsing)
- HTML/CSS (for frontend)
- LLM Integration (OpenAI, Ollama, or Sentence Transformers) for AI-powered criteria comparison

## AI-Enhanced Comparison

The framework comparison feature now supports AI-powered enhancements:
- **Semantic Similarity Detection**: Finds criteria that are conceptually similar even if named differently
- **Intelligent Summaries**: Generates concise comparisons of how different frameworks define the same criterion
- **Framework-Specific Descriptions**: AI-generated descriptions tailored to each framework's approach
- **Related Criteria Grouping**: Groups criteria that belong to the same conceptual category

See [LLM_SETUP.md](LLM_SETUP.md) for setup instructions.

### Updating Criteria Descriptions Intelligently

The system includes management commands to intelligently update criteria descriptions using LLM:

```bash
# Update all criteria descriptions using LLM (framework-specific)
python manage.py update_criteria_intelligently

# Update specific criterion across all frameworks
python manage.py update_criteria_intelligently --criterion "Accuracy"

# Update criteria for a specific framework
python manage.py update_criteria_intelligently --framework "Framework Name"

# Preview changes without saving (dry run)
python manage.py update_criteria_intelligently --dry-run

# Force update criteria with duplicate/generic descriptions
python manage.py force_update_duplicate_descriptions

# Test LLM enhancement functionality
python manage.py test_llm_enhancement
```

## License

This project is open source and available for academic and research purposes.
