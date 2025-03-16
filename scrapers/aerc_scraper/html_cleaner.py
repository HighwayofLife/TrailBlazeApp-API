"""HTML cleaning module with optimized performance."""

import logging
import time
from typing import List
from lxml import html, etree
from bs4 import BeautifulSoup
import cssselect
from ..exceptions import DataExtractionError

logger = logging.getLogger(__name__)

class HtmlCleaner:
    """Cleans and processes HTML content."""
    
    def __init__(self):
        self.metrics = {
            'rows_found': 0,
            'cleaned_size': 0,
            'cleaning_time': 0,
            'lxml_fallbacks': 0
        }
    
    def clean(self, html_content: str) -> str:
        """Clean HTML content using lxml with BeautifulSoup fallback."""
        if not html_content:
            raise DataExtractionError("No HTML content provided")
        
        start_time = time.time()
        
        try:
            # Try lxml first for better performance
            parser = etree.HTMLParser(remove_comments=True, remove_pis=True)
            root = html.document_fromstring(html_content, parser=parser)
            
            # Remove unwanted elements
            unwanted_selectors = [
                'script', 'style', 'link', 'meta',  # Resource elements
                'header', 'footer', 'nav',          # Layout elements
                'iframe', 'form', 'button',         # Interactive elements
                '.unwanted', '#unwanted',           # Custom unwanted classes/ids
                '[style*="display: none"]'          # Hidden elements
            ]
            
            for selector in unwanted_selectors:
                try:
                    for element in root.cssselect(selector):
                        element.getparent().remove(element)
                except cssselect.parser.SelectorSyntaxError:
                    continue
            
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
            
            # Process and append each row
            for row in calendar_rows:
                # Clean the row
                row = self._clean_element(row)
                container.append(row)
            
            # Convert back to string
            cleaned_html = etree.tostring(container, encoding='unicode', method='html')
            
            self.metrics['cleaned_size'] = len(cleaned_html)
            self.metrics['cleaning_time'] = time.time() - start_time
            
            return cleaned_html
            
        except (etree.ParserError, etree.XMLSyntaxError) as e:
            logger.warning(f"lxml parsing failed, falling back to BeautifulSoup: {e}")
            self.metrics['lxml_fallbacks'] += 1
            
            # BeautifulSoup fallback
            return self._clean_with_beautifulsoup(html_content, start_time)
    
    def _clean_with_beautifulsoup(self, html_content: str, start_time: float) -> str:
        """Clean HTML using BeautifulSoup as a fallback."""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Remove unwanted elements
            for tag in ['script', 'style', 'link', 'meta', 'header', 'footer', 'nav']:
                for element in soup.find_all(tag):
                    element.decompose()
            
            # Remove elements with unwanted classes or hidden styles
            for element in soup.find_all(class_='unwanted'):
                element.decompose()
            for element in soup.find_all(style=lambda x: x and 'display: none' in x):
                element.decompose()
            
            # Find calendar rows
            calendar_rows = soup.find_all('div', class_='calendarRow')
            row_count = len(calendar_rows)
            logger.info(f"Found {row_count} calendar rows (using BeautifulSoup)")
            self.metrics['rows_found'] = row_count
            
            if not row_count:
                raise DataExtractionError("No calendar rows found in the HTML")
            
            # Create container
            container = soup.new_tag('div', id='calendar-content')
            
            # Process and append each row
            for row in calendar_rows:
                # Clean the row
                row = self._clean_element_bs4(row)
                container.append(row)
            
            cleaned_html = str(container)
            self.metrics['cleaned_size'] = len(cleaned_html)
            self.metrics['cleaning_time'] = time.time() - start_time
            
            return cleaned_html
            
        except Exception as e:
            raise DataExtractionError(f"HTML cleaning failed: {str(e)}")
    
    def _clean_element(self, element: etree.Element) -> etree.Element:
        """Clean an individual lxml element."""
        # Remove empty class attributes
        if 'class' in element.attrib and not element.attrib['class'].strip():
            del element.attrib['class']
        
        # Remove style attributes
        if 'style' in element.attrib:
            del element.attrib['style']
        
        # Remove data-* attributes
        for attr in list(element.attrib.keys()):
            if attr.startswith('data-'):
                del element.attrib[attr]
        
        # Recursively clean children
        for child in element:
            self._clean_element(child)
        
        return element
    
    def _clean_element_bs4(self, element: BeautifulSoup) -> BeautifulSoup:
        """Clean an individual BeautifulSoup element."""
        # Remove empty class attributes
        if element.get('class'):
            classes = [c for c in element['class'] if c.strip()]
            if classes:
                element['class'] = classes
            else:
                del element['class']
        
        # Remove style attributes
        if element.get('style'):
            del element['style']
        
        # Remove data-* attributes
        for attr in list(element.attrs.keys()):
            if attr.startswith('data-'):
                del element[attr]
        
        # Recursively clean children
        for child in element.children:
            if hasattr(child, 'attrs'):
                self._clean_element_bs4(child)
        
        return element
    
    def get_metrics(self) -> dict:
        """Get HTML cleaning metrics."""
        return self.metrics.copy()