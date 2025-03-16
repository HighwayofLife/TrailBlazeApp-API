"""
HTML cleaning module using lxml for better performance.
"""

import logging
from typing import Optional
from lxml import html, etree
from bs4 import BeautifulSoup
import re
from .exceptions import DataExtractionError

logger = logging.getLogger(__name__)

class HtmlCleaner:
    """Cleans and processes HTML content."""
    
    def __init__(self):
        self.metrics = {
            'rows_found': 0,
            'cleaned_size': 0
        }
    
    def clean(self, html_content: str) -> str:
        """Clean HTML content and prepare for processing."""
        if not html_content:
            raise DataExtractionError("No HTML content provided")
        
        try:
            # First pass with lxml for faster processing
            root = html.fromstring(html_content)
            
            # Remove unnecessary elements
            for element in root.xpath('//script | //style | //header | //footer | //nav'):
                element.getparent().remove(element)
            
            # Find calendar rows using CSS selectors
            calendar_rows = root.cssselect('div.calendarRow')
            row_count = len(calendar_rows)
            
            logger.info(f"Found {row_count} calendar rows")
            self.metrics['rows_found'] = row_count
            
            if not row_count:
                raise DataExtractionError("No calendar rows found in the HTML")
            
            # Create a container for the rows
            container = etree.Element('div')
            container.set('id', 'calendar-content')
            
            # Append filtered rows to container
            for row in calendar_rows:
                # Remove any nested scripts or unnecessary elements
                for bad_elem in row.xpath('.//script | .//style'):
                    bad_elem.getparent().remove(bad_elem)
                container.append(row)
            
            # Convert back to string
            cleaned_html = etree.tostring(container, encoding='unicode', method='html')
            self.metrics['cleaned_size'] = len(cleaned_html)
            
            # Fallback to BeautifulSoup for any complex HTML issues
            # This helps handle malformed HTML that lxml might struggle with
            soup = BeautifulSoup(cleaned_html, 'lxml')
            final_html = str(soup)
            
            logger.debug(f"Cleaned HTML size: {len(final_html)} bytes")
            return final_html
            
        except etree.ParserError as e:
            logger.error(f"HTML parsing error: {e}")
            # Fallback to BeautifulSoup if lxml fails
            try:
                soup = BeautifulSoup(html_content, 'lxml')
                
                # Remove unnecessary elements
                for tag in ['script', 'style', 'header', 'footer', 'nav']:
                    for element in soup.find_all(tag):
                        element.decompose()
                
                # Focus on calendar rows
                calendar_rows = soup.find_all('div', class_='calendarRow')
                row_count = len(calendar_rows)
                logger.info(f"Found {row_count} calendar rows (using BeautifulSoup fallback)")
                self.metrics['rows_found'] = row_count
                
                if not calendar_rows:
                    raise DataExtractionError("No calendar rows found in the HTML")
                
                # Create a container for the rows
                container = soup.new_tag('div')
                container['id'] = 'calendar-content'
                
                for row in calendar_rows:
                    container.append(row)
                
                final_html = str(container)
                self.metrics['cleaned_size'] = len(final_html)
                return final_html
                
            except Exception as bs_error:
                raise DataExtractionError(f"HTML cleaning failed: {str(bs_error)}")
        
        except Exception as e:
            raise DataExtractionError(f"HTML cleaning failed: {str(e)}")
    
    def get_metrics(self) -> dict:
        """Get HTML cleaning metrics."""
        return self.metrics.copy()