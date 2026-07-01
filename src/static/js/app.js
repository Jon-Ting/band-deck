// Band-Deck — frontend
document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('search-form');
    const searchButton = document.getElementById('search-button');
    const downloadButton = document.getElementById('download-button');
    const errorMessage = document.getElementById('error-message');
    const loadingIndicator = document.getElementById('loading');
    const previewContainer = document.getElementById('preview-container');
    const previewTitle = document.getElementById('preview-title');
    const previewArtist = document.getElementById('preview-artist');
    const previewLyrics = document.getElementById('preview-lyrics');
    const saveSlideButton = document.getElementById('save-slide-button');
    const savedSlidesContainer = document.getElementById('saved-slides-container');
    const savedSlidesList = document.getElementById('saved-slides-list');
    const downloadAllButton = document.getElementById('download-all-button');
    
    // Track current song data
    let currentSongData = null;

    // Load saved slides on page load
    loadSavedSlides();

    // Handle form submission
    searchForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Get form values
        const songName = document.getElementById('song-name').value.trim();
        const artistName = document.getElementById('artist-name').value.trim();
        const key = document.getElementById('key').value.trim();
        
        if (!songName) {
            showError('Please enter a song name');
            return;
        }
        
        // Hide error message if previously shown
        errorMessage.style.display = 'none';
        
        // Hide preview if previously shown
        previewContainer.style.display = 'none';
        
        // Show loading indicator
        loadingIndicator.style.display = 'block';
        
        // Disable search button during request
        searchButton.disabled = true;
        searchButton.innerHTML = 'Searching...';
        
        // Make API request to backend
        fetchSongData(songName, artistName, key);
    });
    
    // Handle download button click
    if (downloadButton) {
        downloadButton.addEventListener('click', function() {
            if (!currentSongData) {
                showError('No song data available for download');
                return;
            }
            
            // Show loading state
            downloadButton.disabled = true;
            downloadButton.innerHTML = 'Generating...';
            
            // Use the same key as in the search
            const key = document.getElementById('key').value.trim();
            downloadPPTX(currentSongData.title, currentSongData.artist || '', key);
            
            // Reset button after a delay
            setTimeout(() => {
                downloadButton.disabled = false;
                downloadButton.innerHTML = 'Download PowerPoint';
            }, 2000);
        });
    }
    
    // Function to fetch song data from backend
    function fetchSongData(songName, artistName, key) {
        // Create query parameters
        const params = new URLSearchParams();
        params.append('song', songName);
        if (artistName) {
            params.append('artist', artistName);
        }
        if (key) {
            params.append('key', key);
        }
        
        // Make API request
        fetch(`/api/search?${params.toString()}`)
            .then(response => {
                if (!response.ok) {
                    if (response.status === 404) {
                        throw new Error('Song not found');
                    } else {
                        throw new Error('Server error');
                    }
                }
                return response.json();
            })
            .then(data => {
                // Hide loading indicator
                loadingIndicator.style.display = 'none';
                
                // Enable search button
                searchButton.disabled = false;
                searchButton.innerHTML = 'Generate Slide';
                
                // Store current song data
                currentSongData = data;
                
                // Display preview
                displayPreview(data);
            })
            .catch(error => {
                // Hide loading indicator
                loadingIndicator.style.display = 'none';
                
                // Enable search button
                searchButton.disabled = false;
                searchButton.innerHTML = 'Generate Slide';
                
                // Show appropriate error message
                if (error.message === 'Song not found') {
                    showError(`We couldn't find "${songName}" ${artistName ? `by ${artistName}` : ''}. Please check the spelling or try another song.`);
                } else {
                    showError('Sorry, something went wrong. Please try again later.');
                }
                
                console.error('Error:', error);
            });
    }
    
    // Function to display preview (only PowerPoint preview)
    function displayPreview(data) {
        // Set slide preview title
        document.getElementById('slide-title').textContent = data.title || 'Unknown Title';
        
        // Format and display lyrics with chords in slide preview
        if (data.content) {
            const slideContent = document.getElementById('slide-content');
            slideContent.textContent = data.content;
        } else {
            document.getElementById('slide-content').textContent = 'No lyrics content available for preview.';
        }
        
        // Show PowerPoint generation details if available
        if (data.pptx_preview) {
            console.log("\n" + "=".repeat(50));
            console.log("PowerPoint Generation Preview:");
            console.log(`Title: ${data.pptx_preview.title}`);
            console.log(`Artist: ${data.pptx_preview.artist || 'Not specified'}`);
            console.log(`Key: ${data.pptx_preview.key || 'Not specified'}`);
            console.log("\nSections:");
            data.pptx_preview.sections.forEach((section, index) => {
                console.log(`\nSection ${index + 1}:`);
                console.log(`Header: ${section.header}`);
                console.log("Content:");
                console.log(section.content);
            });
            console.log("=".repeat(50) + "\n");
        }
        
        // Update download button text to reflect PowerPoint format
        downloadButton.innerHTML = 'Download PowerPoint';
        
        // Show preview container
        previewContainer.style.display = 'block';
        
        // Scroll to preview
        previewContainer.scrollIntoView({ behavior: 'smooth' });
    }
    
    // Function to download PowerPoint from backend
    function downloadPPTX(songName, artistName, key) {
        console.log("\n" + "=".repeat(50));
        console.log("Starting PowerPoint generation...");
        console.log(`Song: ${songName}`);
        console.log(`Artist: ${artistName || 'Not specified'}`);
        console.log(`Key: ${key || 'Not specified'}`);
        console.log("=".repeat(50) + "\n");
        
        const params = new URLSearchParams();
        params.append('song', songName);
        if (artistName) params.append('artist', artistName);
        if (key) params.append('key', key);
        
        // Open in new tab to see console output
        const downloadWindow = window.open(`/api/download?${params.toString()}`);
        
        // Check if download started
        setTimeout(() => {
            if (downloadWindow) {
                console.log("PowerPoint generation completed!");
                console.log("=".repeat(50) + "\n");
            }
        }, 2000);
    }
    
    // Function to show error message
    function showError(message) {
        errorMessage.innerHTML = `<p>${message}</p>`;
        errorMessage.style.display = 'block';
        errorMessage.scrollIntoView({ behavior: 'smooth' });
    }

    // Save Slide button handler
    if (saveSlideButton) {
        saveSlideButton.addEventListener('click', function() {
            if (!currentSongData) {
                showError('No song data available to save');
                return;
            }
            fetch('/api/save_slide', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(currentSongData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showError(data.error);
                } else {
                    showSuccess('Slide saved!');
                    loadSavedSlides();
                }
            })
            .catch(() => showError('Failed to save slide.'));
        });
    }

    // Download All button handler
    if (downloadAllButton) {
        downloadAllButton.addEventListener('click', function() {
            window.open('/api/compile_slides');
        });
    }

    // Load and render saved slides
    function loadSavedSlides() {
        fetch('/api/saved_slides')
            .then(response => response.json())
            .then(data => renderSavedSlides(data))
            .catch(() => {
                savedSlidesList.innerHTML = '<p>Could not load saved slides.</p>';
            });
    }

    function renderSavedSlides(slides) {
        if (!slides.length) {
            savedSlidesList.innerHTML = '<p>No saved slides yet.</p>';
            return;
        }
        let html = '<table class="saved-slides-table"><thead><tr><th>Title</th><th>Artist</th><th>Key</th><th>Actions</th></tr></thead><tbody>';
        slides.forEach(slide => {
            html += `<tr>
                <td>${slide.title || ''}</td>
                <td>${slide.artist || ''}</td>
                <td>${slide.key || ''}</td>
                <td>
                    <button class="download-saved-slide" data-id="${slide.id}">Download</button>
                    <button class="delete-saved-slide" data-id="${slide.id}">Delete</button>
                </td>
            </tr>`;
        });
        html += '</tbody></table>';
        savedSlidesList.innerHTML = html;
        // Add event listeners for download and delete
        document.querySelectorAll('.download-saved-slide').forEach(btn => {
            btn.addEventListener('click', function() {
                const id = this.getAttribute('data-id');
                window.open(`/api/saved_slide/${id}`);
            });
        });
        document.querySelectorAll('.delete-saved-slide').forEach(btn => {
            btn.addEventListener('click', function() {
                const id = this.getAttribute('data-id');
                fetch(`/api/saved_slide/${id}`, { method: 'DELETE' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            showSuccess('Slide deleted.');
                            loadSavedSlides();
                        } else {
                            showError(data.error || 'Failed to delete slide.');
                        }
                    })
                    .catch(() => showError('Failed to delete slide.'));
            });
        });
    }

    // Show success message
    function showSuccess(message) {
        let msg = document.getElementById('success-message');
        if (!msg) {
            msg = document.createElement('div');
            msg.id = 'success-message';
            msg.className = 'success-message';
            document.body.prepend(msg);
        }
        msg.innerHTML = `<p>${message}</p>`;
        msg.style.display = 'block';
        setTimeout(() => { msg.style.display = 'none'; }, 2000);
    }

    // Cleanup Temporary Files button handler
    const cleanupButton = document.getElementById('cleanup-temp-files-button');
    if (cleanupButton) {
        cleanupButton.addEventListener('click', function() {
            cleanupButton.disabled = true;
            cleanupButton.innerHTML = 'Cleaning...';
            fetch('/api/clear_temp_files', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showSuccess('Temporary files cleaned up!');
                        loadSavedSlides();
                    } else {
                        showError(data.error || 'Failed to clean up temporary files.');
                    }
                })
                .catch(() => showError('Failed to clean up temporary files.'))
                .finally(() => {
                    cleanupButton.disabled = false;
                    cleanupButton.innerHTML = 'Cleanup Temporary Files';
                });
        });
    }
});
