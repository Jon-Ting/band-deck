// Band-Deck — frontend
document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('search-form');
    const searchButton = document.getElementById('search-button');
    const downloadButton = document.getElementById('download-button');
    const downloadFormatSelect = document.getElementById('download-format');
    // Legacy PPTX button label: surfaces a small notice that the format
    // is deprecated. The notice text is read by both keyboard and screen
    // readers so users see the migration suggestion regardless of input
    // modality.
    if (downloadFormatSelect) {
        const pptxOption = downloadFormatSelect.querySelector('option[value="pptx"]');
        if (pptxOption && !pptxOption.dataset.deprecationNoticeAttached) {
            pptxOption.dataset.deprecationNoticeAttached = 'true';
            pptxOption.title = 'PPTX is legacy; HTML is recommended.';
        }
    }
    const errorMessage = document.getElementById('error-message');
        const loadingIndicator = document.getElementById('loading');
        const arrangementEditorContainer = document.getElementById('arrangement-editor-container');
        const previewContainer = document.getElementById('preview-container');
    const previewTitle = document.getElementById('preview-title');
    const previewArtist = document.getElementById('preview-artist');
    const previewLyrics = document.getElementById('preview-lyrics');
    const saveSlideButton = document.getElementById('save-slide-button');
    const savedSlidesContainer = document.getElementById('saved-slides-container');
    const savedSlidesList = document.getElementById('saved-slides-list');
    const downloadAllButton = document.getElementById('download-all-button');
    const validationWarnings = document.getElementById('validation-warnings');
    const validationWarningsList = document.getElementById('validation-warnings-list');
    const validationErrors = document.getElementById('validation-errors');
    const validationErrorsList = document.getElementById('validation-errors-list');
    const overflowWarnings = document.getElementById('overflow-warnings');
    const overflowWarningsList = document.getElementById('overflow-warnings-list');
    const licensingReminders = document.getElementById('licensing-reminders');
    const licensingRemindersList = document.getElementById('licensing-reminders-list');
    const downloadFormatSelect = document.getElementById('download-format');

    /**
     * Wire up the dismiss buttons for the validation panels. Each panel can
     * be hidden independently without affecting the others.
     */
    function wireValidationDismissButtons() {
        const dismissPairs = [
            ['dismiss-warnings', validationWarnings],
            ['dismiss-overflow', overflowWarnings],
            ['dismiss-licensing', licensingReminders],
        ];
        dismissPairs.forEach(([id, panel]) => {
            if (!panel) { return; }
            const button = document.getElementById(id);
            if (button) {
                button.addEventListener('click', () => { panel.hidden = true; });
            }
        });
    }
    wireValidationDismissButtons();

    /**
     * Render the structured validation result returned by /api/validate.
     *
     * The endpoint returns errors, warnings, overflow, and licensing as
     * distinct arrays. Errors are rendered into a non-dismissible panel so
     * the user is forced to acknowledge them before saving; warnings,
     * overflow, and licensing reminders are dismissible alerts.
     */
    function renderValidationResult(result) {
        if (!result || typeof result !== 'object') { return; }

        const errors = Array.isArray(result.errors) ? result.errors : [];
        const warnings = Array.isArray(result.warnings) ? result.warnings : [];
        const overflow = Array.isArray(result.overflow) ? result.overflow : [];
        const licensing = Array.isArray(result.licensing_warnings) ? result.licensing_warnings : [];

        renderList(validationErrors, validationErrorsList, errors, 'error-blocker');
        renderList(validationWarnings, validationWarningsList, warnings, 'validation-warnings-item');
        renderList(licensingReminders, licensingRemindersList, licensing, 'licensing-reminder');

        if (overflowWarnings && overflowWarningsList) {
            if (overflow.length === 0) {
                overflowWarnings.hidden = true;
                overflowWarningsList.innerHTML = '';
            } else {
                overflowWarnings.hidden = false;
                overflowWarningsList.innerHTML = '';
                overflow.forEach(entry => {
                    const li = document.createElement('li');
                    const name = entry.section_name || '';
                    const est = entry.estimated_lines;
                    const max = entry.max_lines;
                    const suggestion = entry.suggestion || '';
                    const header = document.createElement('strong');
                    header.textContent = `${name}: ${est} lines (max ${max}).`;
                    li.appendChild(header);
                    if (suggestion) {
                        const body = document.createElement('span');
                        body.textContent = ' ' + suggestion;
                        li.appendChild(body);
                    }
                    overflowWarningsList.appendChild(li);
                });
            }
        }

        // Maintain backward compatibility for any caller still reading the
        // single ``validationWarnings`` container.
        if (validationWarnings && warnings.length === 0 && errors.length === 0) {
            validationWarnings.hidden = true;
        }
    }

    function renderList(panel, list, items, itemClass) {
        if (!panel || !list) { return; }
        if (!items || items.length === 0) {
            panel.hidden = true;
            list.innerHTML = '';
            return;
        }
        panel.hidden = false;
        list.innerHTML = '';
        items.forEach(item => {
            const li = document.createElement('li');
            if (typeof item === 'string') {
                li.textContent = item;
            } else {
                li.textContent = item.message || JSON.stringify(item);
            }
            if (itemClass) { li.className = itemClass; }
            list.appendChild(li);
        });
    }

    /**
     * Pop the structured validation warnings onto the live preview flow.
     * Returns a promise so the editor wait path can optionally await the
     * results before showing them.
     */
    async function refreshValidation(songData, style) {
        try {
            const response = await fetch('/api/validate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    song: songData,
                    style: style || 'practice',
                    check_placeholders: false,
                }),
            });
            if (!response.ok) { return; }
            const result = await response.json();
            renderValidationResult(result);
            return result;
        } catch (err) {
            console.error('Validation refresh failed:', err);
            return null;
        }
    }
    
    // Track current song data
    let currentSongData = null;
    let slidePreview = null;
    let songEditor = null;
    let arrangementEditor = null;

    // Initialize SlidePreview and SongEditor components
    function initializeComponents() {
        if (!slidePreview) {
            slidePreview = new SlidePreview('html-slide-preview');
        }
        if (!songEditor) {
            songEditor = new SongEditor('song-editor', {
                preview: slidePreview,
                endpoint: '/api/regenerate',
            });
        }
        if (!arrangementEditor) {
            arrangementEditor = new ArrangementEditor('arrangement-editor', {
                preview: slidePreview,
                endpoint: '/api/regenerate',
            });
        }
    }

    // Load saved slides on page load
    loadSavedSlides();

    // Handle download format selection
    if (downloadFormatSelect && downloadButton) {
        downloadFormatSelect.addEventListener('change', function() {
            const format = this.value;
            const formatLabels = {
                html: 'HTML Slide Deck',
                marp: 'Marp Markdown',
                yaml: 'YAML Source',
                pdf: 'PDF',
                pptx: 'PowerPoint (Legacy)',
            };
            downloadButton.textContent = `Download ${formatLabels[format] || format.toUpperCase()}`;
        });
    }

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
            
            const format = downloadFormatSelect.value;
            
            // Show loading state
            downloadButton.disabled = true;
            const originalText = downloadButton.textContent;
            downloadButton.textContent = 'Generating...';
            
            // Use the appropriate download endpoint based on format
            if (format === 'pptx') {
                // Legacy PowerPoint download
                const key = document.getElementById('key').value.trim();
                downloadPPTX(currentSongData.title, currentSongData.artist || '', key);
            } else {
                // New format downloads (HTML, Marp, YAML, PDF)
                downloadFormat(format);
            }
            
            // Reset button after a delay
            setTimeout(() => {
                downloadButton.disabled = false;
                downloadButton.textContent = originalText;
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
    
    // Function to display preview with HTML slides and editor
    function displayPreview(data) {
        initializeComponents();

        // Convert the search result format to YAML-like format for the new pipeline
        const yamlSongData = convertSearchResultToYAML(data);
        currentSongData = yamlSongData;

        // Request preview generation from backend
        generatePreview(yamlSongData);        // Show preview container
        previewContainer.style.display = 'block';
        if (arrangementEditorContainer) {
            arrangementEditorContainer.style.display = 'block';
        }

        // Scroll to preview
        previewContainer.scrollIntoView({ behavior: 'smooth' });
    }

    // Helper: convert search result to YAML-compatible format
    function convertSearchResultToYAML(searchResult) {
        // For now, create a minimal structure that works with the YAML pipeline
        // This will be replaced by actual /api/generate_yaml endpoint call later
        return {
            title: searchResult.title || '',
            authors: searchResult.artist ? [searchResult.artist] : [],
            target_key: searchResult.key || '',
            sections: searchResult.sections || {},
            arrangement: searchResult.arrangement || [],
            bpm: searchResult.bpm || null,
            time_signature: searchResult.time_signature || '',
            capo: searchResult.capo || '',
            ccli_number: searchResult.ccli_number || null,
            copyright: searchResult.copyright || '',
            practice_notes: searchResult.practice_notes || {},
        };
    }

    // Function to generate HTML preview via API
    function generatePreview(songData) {
        // Initialize components if not already done
        initializeComponents();
        
        fetch('/api/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                song: songData,
                style: 'practice',
            }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(result => {
            if (result.error) {
                showError(result.error);
                return;
            }

            // Load HTML content into SlidePreview
            if (result.html_content && slidePreview) {
                slidePreview.loadPreview(result.html_content, {
                    slideCount: result.slide_count,
                    warnings: result.warnings || [],
                });
            }

            // Set song data in SongEditor
            if (songEditor) {
                songEditor.setSongData(songData);
            }

            // Set song data in ArrangementEditor
            if (arrangementEditor) {
                arrangementEditor.setSongData(songData);
            }

            // Display validation warnings at the top level
            displayValidationWarnings(result.warnings || []);
            // Hit the /api/validate endpoint so the structured panels
            // (errors, overflow, licensing) reflect the most recent edit.
            refreshValidation(songData, 'practice');
        })
        .catch(error => {
            console.error('Preview generation failed:', error);
            showError('Failed to generate preview: ' + error.message);
        });
    }

    // Function to display validation warnings
    function displayValidationWarnings(warnings) {
        if (!validationWarnings || !validationWarningsList) {
            return;
        }
        
        if (!warnings || warnings.length === 0) {
            validationWarnings.hidden = true;
            return;
        }

        validationWarningsList.innerHTML = '';
        warnings.forEach(warning => {
            const li = document.createElement('li');
            li.textContent = warning;
            validationWarningsList.appendChild(li);
        });
        validationWarnings.hidden = false;
    }

    // Function to download specific format
    async function downloadFormat(format) {
        if (!currentSongData) {
            showError('No song data available');
            return;
        }

        try {
            if (format === 'html') {
                // Download HTML from preview
                if (slidePreview && slidePreview.htmlContent) {
                    const blob = new Blob([slidePreview.htmlContent], { type: 'text/html' });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `${currentSongData.title || 'song'}.html`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                } else {
                    showError('HTML preview not available');
                }
            } else if (format === 'yaml') {
                // Download YAML source
                const yamlContent = convertToYAMLString(currentSongData);
                const blob = new Blob([yamlContent], { type: 'text/yaml' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${currentSongData.title || 'song'}.yaml`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            } else if (format === 'marp' || format === 'pdf') {
                // Request server-side download for Marp and PDF
                const response = await fetch(`/api/download/${format}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        song: currentSongData,
                        style: songEditor?.style || 'practice',
                    }),
                });

                if (!response.ok) {
                    throw new Error(`Failed to generate ${format.toUpperCase()} file`);
                }

                // Download the file
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                const extension = format === 'marp' ? 'md' : format;
                a.download = `${currentSongData.title || 'song'}.${extension}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            } else {
                showError(`Download format "${format}" is not yet implemented.`);
            }
        } catch (error) {
            console.error('Download failed:', error);
            showError(`Failed to download ${format.toUpperCase()}: ${error.message}`);
        }
    }

    // Helper: convert song data to YAML string
    function convertToYAMLString(songData) {
        // Simple YAML serializer for song data
        let yaml = `title: ${songData.title || ''}\n`;
        if (songData.authors && songData.authors.length > 0) {
            yaml += 'authors:\n';
            songData.authors.forEach(author => {
                yaml += `  - ${author}\n`;
            });
        }
        if (songData.ccli_number) {
            yaml += `ccli_number: ${songData.ccli_number}\n`;
        }
        if (songData.copyright) {
            yaml += `copyright: "${songData.copyright}"\n`;
        }
        yaml += `target_key: ${songData.target_key || ''}\n`;
        if (songData.bpm) {
            yaml += `bpm: ${songData.bpm}\n`;
        }
        if (songData.time_signature) {
            yaml += `time_signature: ${songData.time_signature}\n`;
        }
        if (songData.capo) {
            yaml += `capo: ${songData.capo}\n`;
        }

        if (songData.arrangement && songData.arrangement.length > 0) {
            yaml += '\narrangement:\n';
            songData.arrangement.forEach(section => {
                yaml += `  - ${section}\n`;
            });
        }

        if (songData.sections) {
            yaml += '\nsections:\n';
            Object.entries(songData.sections).forEach(([name, section]) => {
                yaml += `  ${name}:\n`;
                yaml += `    type: ${section.type || 'verse'}\n`;
                if (section.lines && section.lines.length > 0) {
                    yaml += '    lines:\n';
                    section.lines.forEach(line => {
                        const chordpro = line.chordpro || line.raw || '';
                        yaml += `      - chordpro: "${chordpro.replace(/"/g, '\\"')}"\n`;
                    });
                }
            });
        }

        if (songData.practice_notes) {
            yaml += '\npractice_notes:\n';
            Object.entries(songData.practice_notes).forEach(([key, notes]) => {
                if (Array.isArray(notes) && notes.length > 0) {
                    yaml += `  ${key}:\n`;
                    notes.forEach(note => {
                        yaml += `    - "${note.replace(/"/g, '\\"')}"\n`;
                    });
                }
            });
        }

        return yaml;
    }
    
    // Function to download PowerPoint from backend (legacy)
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
