import bibtexparser
from bibtexparser.bparser import BibTexParser
import argparse
from pylatexenc.latex2text import LatexNodes2Text

# Initialize the LaTeX to text converter
latex_converter = LatexNodes2Text()

def clean_latex(text):
    """
    Clean LaTeX-specific formatting using pylatexenc,
    which properly handles LaTeX commands and special characters.
    """
    if not text:
        return ""

    # Convert LaTeX to plain text
    text = latex_converter.latex_to_text(text)

    # Fix any remaining double dashes to single dash for page ranges
    text = text.replace('--', '-')

    return text

def format_authors(authors_str, max_authors=3):
    """Format authors with et al. if needed, handling LaTeX-formatted names."""
    if not authors_str:
        return "Unknown Author"

    # Clean any LaTeX formatting in author names
    authors_str = clean_latex(authors_str)

    # Split by 'and' - pylatexenc already handles LaTeX 'and' commands
    authors = [author.strip() for author in authors_str.split(' and ')]

    # Remove empty entries
    authors = [author for author in authors if author]

    # Handle case where no authors were found
    if not authors:
        return "Unknown Author"

    # Format with et al. if needed
    if len(authors) <= max_authors:
        return ', '.join(authors)
    else:
        return f"{', '.join(authors[:max_authors-1])}, et al."

def extract_arxiv_info(entry):
    """Check if an entry is an arXiv preprint and extract information."""
    is_preprint = False
    arxiv_id = None

    # Fields that might contain arXiv information
    arxiv_fields = ['journal', 'note', 'publisher', 'howpublished', 'url', 'doi']

    for field in arxiv_fields:
        if field in entry and entry[field]:
            field_text = clean_latex(entry[field]).lower()

            if 'arxiv' in field_text or 'preprint' in field_text:
                is_preprint = True

                # Try to extract arXiv ID using common patterns
                import re
                patterns = [
                    r'arxiv:(\d+\.\d+)',
                    r'arxiv/(\d+\.\d+)',
                    r'abs/(\d+\.\d+)'
                ]

                for pattern in patterns:
                    match = re.search(pattern, field_text, re.IGNORECASE)
                    if match:
                        arxiv_id = match.group(1)
                        break

    return is_preprint, arxiv_id

def format_version_info(entry):
    """Format version information for software entries."""
    version_info = ""

    if 'version' in entry:
        version_info += f"v{entry['version']}"

    return version_info

def bibtex_to_plain(bib_file, max_authors=3, include_abstract=False, include_url=False):
    """Convert BibTeX to a condensed plain text format using proper LaTeX parsing."""
    with open(bib_file, 'r', encoding='utf-8') as bibtex_file:
        # Configure the parser to handle non-standard entry types
        parser = BibTexParser(common_strings=True)
        parser.ignore_nonstandard_types = False  # This is the key fix!

        bib_database = bibtexparser.load(bibtex_file, parser)

    plain_entries = []

    for entry in bib_database.entries:
        # Start with authors and year
        entry_text = ""

        # Handle authors
        if 'author' in entry:
            entry_text += format_authors(entry['author'], max_authors) + ". "
        else:
            # Handle edge cases like committee reports
            if 'editor' in entry:
                entry_text += format_authors(entry['editor'], max_authors) + " (Eds.). "
            else:
                # Try to extract organization from different fields
                org = None
                for field in ['organization', 'institution', 'publisher']:
                    if field in entry:
                        org = entry[field]
                        break

                if org:
                    entry_text += f"{clean_latex(org)}. "
                else:
                    entry_text += "Unknown Author. "

        # Add year
        if 'year' in entry:
            entry_text += f"({entry['year']}) "
        else:
            entry_text += "(Unknown Year) "

        # Add title
        if 'title' in entry:
            entry_text += f"{clean_latex(entry['title'])}. "
        else:
            entry_text += "Untitled. "

        # Handle different entry types
        entry_type = entry['ENTRYTYPE'].lower()

        # Standard types
        if entry_type == 'article':
            if 'journal' in entry:
                entry_text += f"{clean_latex(entry['journal'])}"
                if 'volume' in entry:
                    entry_text += f", {entry['volume']}"
                if 'number' in entry:
                    entry_text += f"({entry['number']})"
                if 'pages' in entry:
                    entry_text += f", {entry['pages']}"
                entry_text += ". "

        elif entry_type in ['inproceedings', 'conference', 'proceedings']:
            if 'booktitle' in entry:
                entry_text += f"In: {clean_latex(entry['booktitle'])}. "
            else:
                entry_text += "In: Unknown Proceedings. "

        elif entry_type == 'techreport':
            if 'institution' in entry:
                entry_text += f"Technical Report, {clean_latex(entry['institution'])}. "
            else:
                entry_text += "Technical Report. "

        elif entry_type == 'unpublished':
            if 'note' in entry:
                entry_text += f"{clean_latex(entry['note'])}. "
            else:
                entry_text += "Unpublished. "

        elif entry_type in ['book', 'incollection']:
            if 'publisher' in entry:
                entry_text += f"{clean_latex(entry['publisher'])}. "

            if 'address' in entry:
                entry_text += f"{clean_latex(entry['address'])}. "

        # Non-standard types
        elif entry_type == 'software':
            # Handle software entries
            version = format_version_info(entry)
            if version:
                entry_text += f"[Software] {version}. "
            else:
                entry_text += "[Software]. "

            if 'url' in entry or 'doi' in entry:
                if 'url' in entry:
                    entry_text += f"Available at: {clean_latex(entry['url'])}. "
                elif 'doi' in entry:
                    entry_text += f"DOI: {clean_latex(entry['doi'])}. "

            if 'note' in entry:
                entry_text += f"{clean_latex(entry['note'])}. "

        elif entry_type == 'dataset':
            entry_text += "[Dataset]. "
            if 'publisher' in entry:
                entry_text += f"{clean_latex(entry['publisher'])}. "

        elif entry_type == 'online':
            entry_text += "[Online]. "
            if 'url' in entry:
                entry_text += f"Available at: {clean_latex(entry['url'])}. "
            if 'note' in entry:
                entry_text += f"{clean_latex(entry['note'])}. "

        # Fallback for any other non-standard type
        else:
            # Capitalize the entry type for display
            display_type = entry_type.capitalize()
            entry_text += f"[{display_type}]. "

            # Add whatever additional information we can find
            for field in ['publisher', 'institution', 'organization', 'howpublished', 'note']:
                if field in entry:
                    entry_text += f"{clean_latex(entry[field])}. "
                    break

        # Check if it's a preprint
        is_preprint, arxiv_id = extract_arxiv_info(entry)

        if is_preprint:
            entry_text += "[Preprint] "
            if arxiv_id:
                entry_text += f"arXiv:{arxiv_id} "

        # Add URL if requested and not already included
        if include_url and 'url' not in entry_text:
            if 'url' in entry:
                entry_text += f"URL: {clean_latex(entry['url'])} "
            elif 'doi' in entry:
                entry_text += f"DOI: {clean_latex(entry['doi'])} "

        # Add abstract if requested
        if include_abstract and 'abstract' in entry:
            entry_text += f"Abstract: {clean_latex(entry['abstract'])}"

        plain_entries.append(entry_text.strip())

    return "\n\n".join(plain_entries)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert BibTeX to plain text for LLMs')
    parser.add_argument('input', help='Input BibTeX file')
    parser.add_argument('--output', help='Output plain text file (optional)')
    parser.add_argument('--max-authors', type=int, default=3, help='Maximum number of authors before using et al.')
    parser.add_argument('--include-abstract', action='store_true', help='Include abstracts in the output')
    parser.add_argument('--include-url', action='store_true', help='Include URLs in the output')
    parser.add_argument('--sorting', choices=['none', 'year', 'author'], default='none',
                       help='Sort entries by year, first author, or leave as is (default: none)')

    args = parser.parse_args()

    result = bibtex_to_plain(args.input,
                             max_authors=args.max_authors,
                             include_abstract=args.include_abstract,
                             include_url=args.include_url)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"Converted bibliography written to {args.output}")
    else:
        print(result)
