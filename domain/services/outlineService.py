import re
from typing import List, Dict, Optional, Any, Tuple
import fitz
from domain.entities.document import Document


class ChapterSegment:
    def __init__(self, chapter_number: int, title: str, content: str, page: Optional[int] = None):
        self.chapter_number = chapter_number
        self.title = title
        self.content = content
        self.page = page
        self.chunk_ids: List[str] = []  

    def get_chapter_name(self) -> str:
        return f"Chapter {self.chapter_number}: {self.title}"


class OutlineService:
    
    # Patterns for arXiv and preprint identifiers
    ARXIV_PATTERNS = [
        r'arxiv:\s*\d+\.\d+',                    # "arXiv:2301.12345"
        r'arxiv\s+preprint',                     # "arXiv preprint"
        r'preprint\s+submitted',                 # "Preprint submitted to..."
        r'submitted\s+to\s+arxiv',               # "Submitted to arXiv"
        r'\d{4}\.\d{4,5}v?\d*',                  # arXiv ID pattern "2301.12345v2"
    ]
    
    # Patterns for license and copyright information
    LICENSE_PATTERNS = [
        r'licensed\s+under',                     # "Licensed under CC BY"
        r'creative\s+commons',                   # "Creative Commons"
        r'cc\s*by[\s\-]',                        # "CC BY", "CC BY-SA"
        r'copyright\s*©?\s*\d{4}',               # "Copyright © 2024"
        r'©\s*\d{4}',                            # "© 2024"
        r'all\s+rights\s+reserved',              # "All rights reserved"
        r'open\s+access',                        # "Open Access"
        r'under\s+review',                       # "Under review"
        r'peer[\s\-]?review',                    # "Peer review", "Peer-review"
    ]
    
    # Patterns for author/affiliation metadata
    AUTHOR_PATTERNS = [
        r'^[\w\.\-]+@[\w\.\-]+\.\w+$',           # Email addresses
        r'^\{[\w,\s]+\}@',                       # Multiple emails "{a,b}@domain"
        r'corresponding\s+author',               # "Corresponding author"
        r'equal\s+contribution',                 # "Equal contribution"
        r'^\*\s*(equal|these)',                  # "*Equal contribution" or "*These authors"
        r'^†',                                   # Dagger symbol for affiliations
        r'^\d+\s*(department|university|institute|lab)', # Numbered affiliations
    ]
    
    # Patterns for publication metadata
    PUBLICATION_PATTERNS = [
        r'doi:\s*10\.',                          # DOI identifier
        r'10\.\d{4,}/\S+',                       # DOI pattern
        r'accepted\s+(for|to)\s+(publication|journal)',
        r'published\s+(in|by)',
        r'journal\s+of\s+',
        r'proceedings\s+of\s+',
        r'conference\s+on\s+',
        r'workshop\s+on\s+',
        r'volume\s+\d+',
        r'pages?\s+\d+[\-–]\d+',
        r'issn[\s:]+\d{4}',
        r'isbn[\s:]+\d{10,13}',
    ]
    
    PAGE_NUMBER_PATTERNS = [
        r'^\s*\d+\s*$',                          # Just a page number "42"
        r'^\s*-\s*\d+\s*-\s*$',                  # "- 42 -"
        r'^\s*–\s*\d+\s*–\s*$',                  # "– 42 –" (en-dash)
        r'^\s*page\s+\d+\s*$',                   # "Page 42"
        r'^\s*p\.\s*\d+\s*$',                    # "p. 42"
        r'^\s*\d+\s+of\s+\d+\s*$',               # "42 of 100"
        r'^\s*\[\s*\d+\s*\]\s*$',                # "[42]"
    ]
    
    # Patterns for common running headers in academic papers
    RUNNING_HEADER_PATTERNS = [
        r'^preprint$',                           # "Preprint" header
        r'^draft$',                              # "Draft" header
        r'^manuscript$',                         # "Manuscript" header
        r'^working\s+paper$',                    # "Working Paper" header
        r'^technical\s+report$',                 # "Technical Report" header
    ]
    
    CHAPTER_PATTERNS = [
        # Academic paper sections (these are HIGH PRIORITY - checked first)
        # Abstract patterns - enhanced for more robust detection
        r'^abstract\s*$',                        # "ABSTRACT" or "Abstract"
        r'^abstract[\s:]+$',                     # "Abstract:" or "Abstract :"
        r'^abstract\s*[:\-–—]\s*$',              # "Abstract -", "Abstract—"
        r'^\d+\.?\s*abstract\s*$',               # "1. Abstract", "1 Abstract"
        r'^[IVXLCDM]+\.?\s*abstract\s*$',        # "I. Abstract", "I Abstract"
        
        # Summary patterns
        r'^summary\s*$',                         # "SUMMARY"
        r'^executive\s+summary\s*$',             # "EXECUTIVE SUMMARY"
        
        # Other academic sections
        r'^introduction\s*$',                    # "INTRODUCTION"
        r'^background\s*$',                      # "BACKGROUND"
        r'^related\s+work\s*$',                  # "RELATED WORK"
        r'^literature\s+review\s*$',             # "LITERATURE REVIEW"
        r'^prior\s+work\s*$',                    # "PRIOR WORK"
        r'^methodology?\s*$',                    # "METHOD" or "METHODOLOGY"
        r'^methods?\s*$',                        # "METHODS"
        r'^materials?\s+and\s+methods?\s*$',     # "MATERIALS AND METHODS"
        r'^approach\s*$',                        # "APPROACH"
        r'^proposed\s+(method|approach)\s*$',    # "PROPOSED METHOD"
        r'^experiments?\s*$',                    # "EXPERIMENT" or "EXPERIMENTS"
        r'^experimental\s+(setup|results?)\s*$', # "EXPERIMENTAL SETUP"
        r'^results?\s*$',                        # "RESULTS"
        r'^results?\s+and\s+discussion\s*$',     # "RESULTS AND DISCUSSION"
        r'^discussion\s*$',                      # "DISCUSSION"
        r'^analysis\s*$',                        # "ANALYSIS"
        r'^conclusions?\s*$',                    # "CONCLUSION" or "CONCLUSIONS"
        r'^concluding\s+remarks?\s*$',           # "CONCLUDING REMARKS"
        r'^future\s+work\s*$',                   # "FUTURE WORK"
        r'^limitations?\s*$',                    # "LIMITATIONS"
        r'^references?\s*$',                     # "REFERENCES"
        r'^bibliography\s*$',                    # "BIBLIOGRAPHY"
        r'^appendix\s*[a-z]?\s*$',               # "APPENDIX" or "APPENDIX A"
        r'^appendices\s*$',                      # "APPENDICES"
        r'^supplementary\s+materials?\s*$',      # "SUPPLEMENTARY MATERIALS"
        r'^acknowledg[e]?ments?\s*$',            # "ACKNOWLEDGEMENTS"
        
        # Numbered sections (academic style: "1 INTRODUCTION", "2. Methods")
        r'^\d+[\.\s]+[A-Z]',                     # "1 INTRODUCTION", "1. Introduction"
        r'^\d+\.\d+[\.\s]+[A-Z]',                # "1.1 Background", "2.1. Methods"
        
        # Traditional chapter patterns
        r'^chapter\s+\d+[:\.\s]',                # "Chapter 1:", "Chapter 1."
        r'^глава\s+\d+[:\.\s]',                  # Russian "Глава 1:"
        r'^part\s+\d+[:\.\s]',                   # "Part 1:"
        r'^section\s+\d+[:\.\s]',                # "Section 1:"
        r'^[IVXLCDM]+\.\s+',                     # Roman numerals "I. ", "II. "
    ]
    
    def __init__(self, max_chunk_per_section: int = 5, max_title_words: int = 10):
        self.max_chunk_per_section = max_chunk_per_section
        self.max_title_words = max_title_words
        
        self._compiled_chapter_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.CHAPTER_PATTERNS
        ]
        
        self._compiled_metadata_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in (
                self.ARXIV_PATTERNS + 
                self.LICENSE_PATTERNS + 
                self.AUTHOR_PATTERNS + 
                self.PUBLICATION_PATTERNS +
                self.PAGE_NUMBER_PATTERNS +
                self.RUNNING_HEADER_PATTERNS
            )
        ]

    def extract_chapters(
        self, 
        document: Document, 
        validate: bool = True
    ) -> List[ChapterSegment]:
        
        chapters = None
        
        content_chapters = self._extract_from_content(document)
        
        if content_chapters and len(content_chapters) >= 2:
            chapters = content_chapters
        else:
            pdf_chapters = self._extract_from_pdf_toc(document)
            if pdf_chapters:
                for chapter in pdf_chapters:
                    chapter.content = self._filter_metadata_from_content(chapter.content)
                chapters = pdf_chapters
            else:
                chapters = content_chapters
        
        if validate and chapters:
            is_valid, error_msg = self.validate_chapter_isolation(chapters)
            if not is_valid:
                raise ValueError(f"Chapter extraction validation failed: {error_msg}")
            
            is_valid, warning_msg = self.validate_no_content_loss(
                document.content, chapters, min_coverage_ratio=0.5
            )
        return chapters
    
    def _filter_metadata_from_content(self, content: str) -> str:
        if not content:
            return content
            
        lines = content.split('\n')
        filtered_lines = []
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                filtered_lines.append(line)
                continue
            
            if not self._is_metadata_line(stripped):
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def _is_metadata_line(self, text: str) -> bool:
        for pattern in self._compiled_metadata_patterns:
            if pattern.search(text):
                return True
        return False
    
    def _strip_header_metadata(self, content: str) -> Tuple[str, int]:
        if not content:
            return content, 0
        
        lines = content.split('\n')
        first_chapter_idx = 0
        
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            
            if self._is_chapter_heading(stripped):
                first_chapter_idx = idx
                break
        
        if first_chapter_idx > 0:
            return '\n'.join(lines[first_chapter_idx:]), first_chapter_idx
        
        return content, 0

    def _extract_from_pdf_toc(self, document: Document) -> Optional[List[ChapterSegment]]:
        if not fitz:
            return None
            
        try:
            pdf = fitz.open(document.metadata.source)
            toc = pdf.get_toc()
            
            if not toc:
                pdf.close()
                return None
            
            chapters = []
            total_pages = pdf.page_count
            
            for idx, item in enumerate(toc):
                level, title, start_page = item[0], item[1], item[2]
                
                if idx + 1 < len(toc):
                    end_page = toc[idx + 1][2]
                else:
                    end_page = total_pages + 1
                
                chapter_content = ""
                for page_num in range(start_page - 1, min(end_page - 1, total_pages)):
                    page = pdf.load_page(page_num)
                    chapter_content += page.get_text() + "\n"
                
                chapter = ChapterSegment(
                    chapter_number=idx + 1,
                    title=title.strip(),
                    content=chapter_content.strip(),
                    page=start_page
                )
                chapters.append(chapter)
            
            pdf.close()
            return chapters if chapters else None
            
        except Exception:
            return None

    def _extract_from_content(self, document: Document) -> List[ChapterSegment]:
        if not document.content:
            return []
        
        content = document.content
        lines = content.split('\n')
        
        chapter_starts: List[Dict[str, Any]] = []
        
        for line_idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            if self._is_chapter_heading(stripped):
                chapter_starts.append({
                    'line_idx': line_idx,
                    'title': stripped
                })
        
        if not chapter_starts:
            filtered_content = self._filter_metadata_from_content(content)
            if filtered_content.strip():
                return [ChapterSegment(
                    chapter_number=1,
                    title="Document Content",
                    content=filtered_content.strip()
                )]
            return []
        
        chapters: List[ChapterSegment] = []
        
        for idx, chapter_info in enumerate(chapter_starts):
            start_line = chapter_info['line_idx']
            title = chapter_info['title']
            
            if idx + 1 < len(chapter_starts):
                end_line = chapter_starts[idx + 1]['line_idx']
            else:
                end_line = len(lines)
            
            chapter_lines = lines[start_line:end_line]
            raw_chapter_content = '\n'.join(chapter_lines)
            
            clean_chapter_content = self._filter_metadata_from_content(raw_chapter_content)
            
            if clean_chapter_content.strip():
                chapter = ChapterSegment(
                    chapter_number=idx + 1,
                    title=self._clean_title(title),
                    content=clean_chapter_content.strip()
                )
                chapters.append(chapter)
        
        for i, ch in enumerate(chapters):
            ch.chapter_number = i + 1
        
        return chapters

    def _is_chapter_heading(self, text: str) -> bool:
        if self._looks_like_reference_entry(text):
            return False

        for pattern in self._compiled_chapter_patterns:
            if pattern.match(text):
                return True
        
        words = text.split()
        
        if len(words) > self.max_title_words:
            return False
        
        if text.rstrip().endswith(('.', ',', ';', '?', '!')):
            return False
        
        if text.isupper() and len(words) >= 1 and len(words) <= 5:
            if not self._is_metadata_line(text):
                return True
        
        return False

    def _looks_like_reference_entry(self, text: str) -> bool:
        if not re.match(r'^\d+[\.\s]+', text):
            return False

        lowered = text.lower()

        if re.search(r'\b(arxiv|doi:|proceedings|journal|conference)\b', lowered):
            return True

        if re.search(r'\b(19|20)\d{2}\b', text):
            return True

        if text.count(",") >= 2 or text.count(".") >= 3:
            return True

        return False

    def _clean_title(self, title: str) -> str:
        cleaned = re.sub(r'^\d+(\.\d+)*[\.\s]+', '', title)
        
        cleaned = re.sub(r'^(chapter|part|section)\s+\d+[:\.\s]*', '', cleaned, flags=re.IGNORECASE)
        
        if cleaned.isupper():
            cleaned = cleaned.title()
        
        return cleaned.strip() if cleaned.strip() else title

    def generate_outline(self, document: Document, chapters: Optional[List[ChapterSegment]] = None) -> List[Dict]:
        outline = []
        
        if chapters:
            for chapter in chapters:
                outline.append({
                    "chapter": chapter.get_chapter_name(),
                    "page": chapter.page,
                    "chunks": chapter.chunk_ids.copy()
                })
            return outline
        
        return self._generate_outline_from_chunks(document)

    def _generate_outline_from_chunks(self, document: Document) -> List[Dict]:
        if not document.chunks or document.chunks.count_chunks() == 0:
            return []

        chunks = document.chunks.get_chunks()
        outline = []
        chapter_number = 1
        chapter_chunks = []
        current_title = None

        for chunk in chunks:
            if hasattr(chunk.metadata, 'section') and chunk.metadata.section:
                section = chunk.metadata.section
                if section != current_title:
                    if chapter_chunks:
                        outline.append({
                            "chapter": f"Chapter {chapter_number}: {current_title or 'Untitled'}",
                            "chunks": chapter_chunks
                        })
                        chapter_number += 1
                        chapter_chunks = []
                    current_title = section
            
            chapter_chunks.append(chunk.chunk_id)

        if chapter_chunks:
            outline.append({
                "chapter": f"Chapter {chapter_number}: {current_title or 'Untitled'}",
                "chunks": chapter_chunks
            })

        return outline

    def validate_chapter_isolation(self, chapters: List[ChapterSegment]) -> Tuple[bool, Optional[str]]:
        if not chapters or len(chapters) < 2:
            return True, None
        
        chapter_signatures: Dict[int, set] = {}
        
        for chapter in chapters:
            sentences = re.split(r'[.!?]+', chapter.content)
            
            signatures = set()
            for sentence in sentences:
                cleaned = sentence.strip().lower()
                cleaned = ' '.join(cleaned.split())
                if len(cleaned) > 30:  
                    signatures.add(cleaned)
            
            chapter_signatures[chapter.chapter_number] = signatures
        
        chapter_nums = list(chapter_signatures.keys())
        for i, num1 in enumerate(chapter_nums):
            for num2 in chapter_nums[i+1:]:
                overlap = chapter_signatures[num1] & chapter_signatures[num2]
                if overlap:
                    ch1_title = next(c.title for c in chapters if c.chapter_number == num1)
                    ch2_title = next(c.title for c in chapters if c.chapter_number == num2)
                    sample = list(overlap)[0][:50] + "..."
                    return False, (
                        f"Content overlap detected between Chapter {num1} ({ch1_title}) "
                        f"and Chapter {num2} ({ch2_title}). "
                        f"Sample: '{sample}'"
                    )
        
        return True, None
    
    def validate_no_content_loss(
        self, 
        original_content: str, 
        chapters: List[ChapterSegment],
        min_coverage_ratio: float = 0.7
    ) -> Tuple[bool, Optional[str]]:
        if not original_content:
            return True, None
        
        original_words = len(original_content.split())
        
        chapter_words = sum(len(ch.content.split()) for ch in chapters)
        
        if original_words == 0:
            return True, None
        
        coverage_ratio = chapter_words / original_words
        
        if coverage_ratio > 1.1:
            return False, (
                f"Chapter word count ({chapter_words}) exceeds original ({original_words}). "
                f"This may indicate overlapping chapter boundaries."
            )
        
        if coverage_ratio < min_coverage_ratio:
            return False, (
                f"Low content coverage: {coverage_ratio:.1%} of original content. "
                f"Expected at least {min_coverage_ratio:.0%}. "
                f"Some content may have been incorrectly filtered as metadata."
            )
        
        return True, None
