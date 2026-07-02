import unittest
from unittest.mock import patch, MagicMock
import requests
from bs4 import BeautifulSoup
from src.utils.search import search_song
from src.utils.pptx_generator import format_worship_together_url

class TestSearchFunctionality(unittest.TestCase):
    def test_url_formatting(self):
        """Test the URL formatting function with various inputs"""
        test_cases = [
            {
                'song': 'Goodness of God',
                'artist': 'Bethel',
                'expected': 'https://www.worshiptogether.com/songs/goodness-of-god-bethel/'
            },
            {
                'song': 'What A Beautiful Name',
                'artist': 'Hillsong Worship',
                'expected': 'https://www.worshiptogether.com/songs/what-a-beautiful-name-hillsong-worship/'
            },
            {
                'song': '10,000 Reasons',
                'artist': 'Matt Redman',
                'expected': 'https://www.worshiptogether.com/songs/10000-reasons-matt-redman/'
            }
        ]
        
        for case in test_cases:
            result = format_worship_together_url(case['song'], case['artist'])
            self.assertEqual(result, case['expected'])

    @patch('requests.get')
    def test_successful_song_search(self, mock_get):
        """Test successful song search with mocked response"""
        # Mock HTML content
        mock_html = """
        <html>
            <body>
                <h1>Goodness of God</h1>
                <div class="artist">Bethel Music</div>
                <div class="lyrics">
                    Verse 1
                    I love You Lord
                    For Your mercy never fails me
                </div>
            </body>
        </html>
        """
        
        # Configure mock response
        mock_response = MagicMock()
        mock_response.text = mock_html
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Test the search function
        result = search_song('Goodness of God', 'Bethel')
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], 'Goodness of God')
        self.assertEqual(result['artist'], 'Bethel Music')
        self.assertIn('Verse 1', result['content'])
        self.assertIn('I love You Lord', result['content'])

    @patch('requests.get')
    def test_failed_song_search(self, mock_get):
        """Test failed song search with mocked error response"""
        # Configure mock to raise an exception
        mock_get.side_effect = requests.RequestException("Failed to connect")
        
        # Test the search function
        result = search_song('Nonexistent Song', 'Unknown Artist')
        
        # Verify the result is None
        self.assertIsNone(result)

    @patch('requests.get')
    def test_missing_elements(self, mock_get):
        """Test search with missing HTML elements"""
        # Mock HTML content with missing elements
        mock_html = """
        <html>
            <body>
                <h1>Goodness of God</h1>
                <!-- Missing artist and lyrics -->
            </body>
        </html>
        """
        
        # Configure mock response
        mock_response = MagicMock()
        mock_response.text = mock_html
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Test the search function
        result = search_song('Goodness of God', 'Bethel')
        
        # Verify the result is None due to missing elements
        self.assertIsNone(result)

    @patch('requests.get')
    def test_lyrics_extraction(self, mock_get):
        """Test lyrics extraction with Worship Together HTML structure"""
        # Mock HTML content with Worship Together structure
        mock_html = """
        <html>
            <body>
                <h1>Goodness of God</h1>
                <div class="song-artist">Bethel Music</div>
                <div class="song-content">
                    <div class="section">
                        <h3>Verse 1</h3>
                        <p>I love You Lord</p>
                        <p>For Your mercy never fails me</p>
                        <p>All my days, I've been held in Your hands</p>
                        <p>From the moment that I wake up</p>
                        <p>Until I lay my head</p>
                        <p>Oh, I will sing of the goodness of God</p>
                    </div>
                    <div class="section">
                        <h3>Chorus</h3>
                        <p>All my life You have been faithful</p>
                        <p>All my life You have been so, so good</p>
                        <p>With every breath that I am able</p>
                        <p>Oh, I will sing of the goodness of God</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Configure mock response
        mock_response = MagicMock()
        mock_response.text = mock_html
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Test the search function
        result = search_song('Goodness of God', 'Bethel')
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], 'Goodness of God')
        self.assertEqual(result['artist'], 'Bethel Music')
        
        # Verify the content structure
        content = result['content']
        self.assertIn('[Verse 1]', content)
        self.assertIn('[Chorus]', content)
        self.assertIn('I love You Lord', content)
        self.assertIn('All my life You have been faithful', content)
        
        # Verify section separation
        sections = content.split('\n\n')
        self.assertTrue(any('Verse 1' in section for section in sections))
        self.assertTrue(any('Chorus' in section for section in sections))

if __name__ == '__main__':
    unittest.main() 