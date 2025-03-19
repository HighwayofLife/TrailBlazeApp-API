"""HTML chunking module for intelligent content splitting."""

import logging
from typing import List, Dict, Any
import cssselect
from lxml import html, etree
from bs4 import BeautifulSoup

from ..config import ScraperBaseSettings
from ..exceptions import ChunkingError

logger = logging.getLogger(__name__)

class HtmlChunker:
    """Handles intelligent HTML chunking."""

    def __init__(self, settings: ScraperBaseSettings):
        self.settings = settings
        self.metrics = {
            'chunks_created': 0,
            'avg_chunk_size': 0,
            'chunk_size_adjustments': 0,
            'total_rows': 0
        }

    def create_chunks(self, html_content: str) -> List[str]:
        """Split HTML content into manageable chunks based on calendar rows."""
        try:
            # Try using lxml first
            parser = etree.HTMLParser(remove_comments=True, remove_pis=True)
            root = html.document_fromstring(html_content, parser=parser)

            # Find all calendar rows
            calendar_rows = root.cssselect('div.calendarRow')
            total_rows = len(calendar_rows)
            self.metrics['total_rows'] = total_rows

            if not total_rows:
                raise ChunkingError("No calendar rows found in the HTML")

            chunks = []
            current_chunk = []
            current_size = 0
            chunk_size = self.settings.initial_chunk_size

            for row in calendar_rows:
                row_html = etree.tostring(row, encoding='unicode', method='html')
                row_size = len(row_html)

                # Adjust chunk size if we see consistently large rows
                if row_size > chunk_size * 0.5:  # If a row is more than 50% of chunk size
                    new_size = int(row_size * 1.5)  # Add 50% buffer
                    chunk_size = min(
                        max(new_size, self.settings.min_chunk_size),
                        self.settings.max_chunk_size
                    )
                    self.metrics['chunk_size_adjustments'] += 1
                    logger.debug(f"Adjusted chunk size to {chunk_size} bytes")

                if current_size + row_size > chunk_size and current_chunk:
                    # Create a new chunk with proper HTML structure
                    chunk_html = self._wrap_chunk(current_chunk)
                    chunks.append(chunk_html)
                    current_chunk = []
                    current_size = 0

                current_chunk.append(row_html)
                current_size += row_size

            # Add the final chunk
            if current_chunk:
                chunk_html = self._wrap_chunk(current_chunk)
                chunks.append(chunk_html)

            # Update metrics
            self.metrics['chunks_created'] = len(chunks)
            total_size = sum(len(chunk) for chunk in chunks)
            self.metrics['avg_chunk_size'] = total_size // len(chunks) if chunks else 0

            logger.info(
                f"Created {len(chunks)} chunks from {total_rows} rows. "
                f"Average chunk size: {self.metrics['avg_chunk_size']} bytes"
            )

            return chunks

        except (etree.ParserError, etree.XMLSyntaxError) as e:
            logger.warning(f"lxml parsing failed, falling back to BeautifulSoup: {e}")
            return self._create_chunks_bs4(html_content)

    def _create_chunks_bs4(self, html_content: str) -> List[str]:
        """Fallback chunking using BeautifulSoup."""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            calendar_rows = soup.find_all('div', class_='calendarRow')
            total_rows = len(calendar_rows)
            self.metrics['total_rows'] = total_rows

            if not total_rows:
                raise ChunkingError("No calendar rows found in the HTML")

            chunks = []
            current_chunk = []
            current_size = 0
            chunk_size = self.settings.initial_chunk_size

            for row in calendar_rows:
                row_html = str(row)
                row_size = len(row_html)

                # Same chunk size adjustment logic
                if row_size > chunk_size * 0.5:
                    new_size = int(row_size * 1.5)
                    chunk_size = min(
                        max(new_size, self.settings.min_chunk_size),
                        self.settings.max_chunk_size
                    )
                    self.metrics['chunk_size_adjustments'] += 1

                if current_size + row_size > chunk_size and current_chunk:
                    chunk_html = self._wrap_chunk(current_chunk)
                    chunks.append(chunk_html)
                    current_chunk = []
                    current_size = 0

                current_chunk.append(row_html)
                current_size += row_size

            # Add the final chunk
            if current_chunk:
                chunk_html = self._wrap_chunk(current_chunk)
                chunks.append(chunk_html)

            # Update metrics
            self.metrics['chunks_created'] = len(chunks)
            total_size = sum(len(chunk) for chunk in chunks)
            self.metrics['avg_chunk_size'] = total_size // len(chunks) if chunks else 0

            return chunks

        except Exception as e:
            raise ChunkingError(f"HTML chunking failed: {str(e)}")

    def _wrap_chunk(self, chunk_rows: List[str]) -> str:
        """Wrap chunk rows in proper HTML structure."""
        return f'<div class="calendar-content">{"".join(chunk_rows)}</div>'

    def get_metrics(self) -> Dict[str, Any]:
        """Get chunking metrics."""
        return self.metrics.copy()
