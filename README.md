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

**Legacy command**: The old `import_docx` command still works for backward compatibility, but `import_document` is recommended as it supports both formats.

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

1. Navigate to "Compare" in the navigation menu
2. Select two or more frameworks using checkboxes
3. Click "Compare" to see a side-by-side comparison table

### Search Criteria

1. Navigate to "Search Criteria"
2. Enter a criterion name (e.g., "Completeness")
3. View results showing which frameworks include that criterion

### Compare Definitions

1. Navigate to "Definitions"
2. Select a criterion from the dropdown
3. View all definitions of that criterion across different frameworks

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
│           ├── import_docx.py      # Legacy DOCX-only import (backward compatibility)
│           └── import_document.py # Enhanced import supporting DOCX and PDF
├── manage.py           # Django management script
├── requirements.txt    # Python dependencies
└── db.sqlite3         # SQLite database (created after migration)
```

## Database Models

- **Framework**: Represents a Knowledge Graph quality framework from literature
  - Fields: name, authors, year, title, description, source

- **Criterion**: Represents a quality criterion/metric in a framework
  - Fields: name, framework (FK), description, category, order

- **Definition**: Represents a definition of a criterion
  - Fields: criterion (FK), definition_text, notes

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

## License

This project is open source and available for academic and research purposes.
