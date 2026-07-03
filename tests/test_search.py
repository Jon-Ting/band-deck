import unittest
from unittest.mock import patch, MagicMock
import requests
from src.utils.search import search_song, format_worship_together_url

class TestSearchFunctionality(unittest.TestCase):
    def test_url_formatting(self):
        """Test the URL formatting function with various inputs"""
        test_cases = [
            {
                'song': 'Amazing Grace',
                'artist': 'Traditional',
                'expected': 'https://www.worshiptogether.com/songs/amazing-grace-traditional/'
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
        # Mock HTML content with Worship Together chord-pro-line structure
        mock_html = """
        <html>
            <body>
                <h1>Amazing Grace</h1>
                <div class="chord-pro-line">
                    <div class="chord-pro-segment">
                        <div class="chord-pro-note">G</div>
                        <div class="chord-pro-lyric">Verse 1</div>
                    </div>
                </div>
                <div class="chord-pro-line">
                    <div class="chord-pro-segment">
                        <div class="chord-pro-note">G</div>
                        <div class="chord-pro-lyric">I love You Lord</div>
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
        result = search_song('Amazing Grace', 'Traditional')
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], 'Amazing Grace')
        self.assertEqual(result['artist'], 'Traditional')
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
                <h1>Amazing Grace</h1>
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
        result = search_song('Amazing Grace', 'Traditional')
        
        # The function returns the title even when other elements are missing
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], 'Amazing Grace')
        self.assertEqual(result['artist'], 'Traditional')

    @patch('requests.get')
    def test_lyrics_extraction(self, mock_get):
        """Test lyrics extraction with Worship Together chord-pro-line structure"""
        # Mock HTML content with Worship Together chord-pro-line segments
        mock_html = """
        <html>
            <body>
                <h1>Amazing Grace</h1>
                <div class="chord-pro-line">
                    <div class="chord-pro-segment">
                        <div class="chord-pro-note"></div>
                        <div class="chord-pro-lyric">Verse 1</div>
                    </div>
                </div>
                <div class="chord-pro-line">
                    <div class="chord-pro-segment">
                        <div class="chord-pro-note">G</div>
                        <div class="chord-pro-lyric">I love You Lord</div>
                    </div>
                </div>
                <div class="chord-pro-line">
                    <div class="chord-pro-segment">
                        <div class="chord-pro-note">D</div>
                        <div class="chord-pro-lyric">For Your mercy never fails me</div>
                    </div>
                </div>
                <div class="chord-pro-line">
                    <div class="chord-pro-segment">
                        <div class="chord-pro-note"></div>
                        <div class="chord-pro-lyric">Chorus</div>
                    </div>
                </div>
                <div class="chord-pro-line">
                    <div class="chord-pro-segment">
                        <div class="chord-pro-note">G</div>
                        <div class="chord-pro-lyric">All my life You have been faithful</div>
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
        result = search_song('Amazing Grace', 'Traditional')
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], 'Amazing Grace')
        self.assertEqual(result['artist'], 'Traditional')
        
        # Verify the content structure
        content = result['content']
        self.assertIn('Verse 1', content)
        self.assertIn('Chorus', content)
        self.assertIn('I love You Lord', content)
        self.assertIn('All my life You have been faithful', content)
        
        # Verify section separation
        sections = content.split('\n\n')
        self.assertTrue(any('Verse 1' in section for section in sections))
        self.assertTrue(any('Chorus' in section for section in sections))

if __name__ == '__main__':
    unittest.main() 
