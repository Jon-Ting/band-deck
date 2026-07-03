(function(root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.SongEditor = factory();
    }
}(typeof window !== 'undefined' ? window : globalThis, function() {
    'use strict';

    class SongEditor {
        constructor(containerOrId, options = {}) {
            this.document = options.document || document;
            this.Event = options.Event || this.document.defaultView?.Event || Event;
            this.container = this._resolveContainer(containerOrId);
            this.fetch = options.fetch || fetch.bind(globalThis);
            this.preview = options.preview || null;
            this.debounceMs = Number.isInteger(options.debounceMs) ? options.debounceMs : 500;
            this.timers = options.timers || {
                setTimeout: setTimeout.bind(globalThis),
                clearTimeout: clearTimeout.bind(globalThis),
            };
            this.endpoint = options.endpoint || '/api/regenerate';
            this.songData = null;
            this.debounceTimer = null;
            this.regenerating = false;
            this.warnings = [];
            this.fields = {};
            this.sectionFields = {};
            this.style = options.style || 'practice';
            this.options = {
                show_metadata: true,
                show_song_map: true,
                font_size: 28,
                ...(options.previewOptions || {}),
            };

            this._build();
        }

        setSongData(songData) {
            this.songData = this._clone(songData || {});
            this.style = this.songData.style || this.style;
            this._populateFields();
            this._renderSectionFields();
            this._setStatus('');
        }

        onFieldEdit(field, value) {
            this._updateField(field, value);
            this._scheduleRegeneration();
        }

        onBlur() {
            return this.flushRegeneration();
        }

        async flushRegeneration() {
            this._clearDebounce();
            return this.regeneratePreview();
        }

        async regeneratePreview() {
            if (!this.songData || this.regenerating) {
                return null;
            }

            this.regenerating = true;
            this._setStatus('Regenerating...');
            this._setDisabled(true);

            try {
                const response = await this.fetch(this.endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        song: this.songData,
                        style: this.style,
                        options: this.options,
                    }),
                });
                const result = await response.json();

                if (!response.ok) {
                    throw new Error(result.error || 'Failed to regenerate preview');
                }

                this.warnings = Array.isArray(result.warnings) ? result.warnings : [];
                this._renderWarnings();

                if (result.html_content && this.preview) {
                    const loadPreview = this.preview.loadHtml || this.preview.loadPreview;
                    if (loadPreview) {
                        loadPreview.call(this.preview, result.html_content, {
                            slideCount: result.slide_count,
                            warnings: this.warnings,
                        });
                    }
                }

                this._setStatus('Preview updated');
                return result;
            } catch (error) {
                this._setStatus(error.message || 'Failed to regenerate preview', true);
                throw error;
            } finally {
                this.regenerating = false;
                this._setDisabled(false);
            }
        }

        _build() {
            this.root = this._element('div', 'song-editor');
            const form = this._element('form', 'song-editor__form');
            form.addEventListener('submit', (event) => {
                event.preventDefault();
                this.flushRegeneration();
            });

            form.appendChild(this._sectionTitle('Song Details'));
            this.fields.title = this._field(form, 'Title', 'title');
            this.fields.target_key = this._field(form, 'Target Key', 'target_key');
            this.fields.capo = this._field(form, 'Capo', 'capo');
            this.fields.bpm = this._field(form, 'BPM', 'bpm', 'number');
            this.fields.time_signature = this._field(form, 'Time Signature', 'time_signature');

            form.appendChild(this._sectionTitle('Display'));
            this.fields.style = this._selectField(form, 'Style', 'style', [
                ['practice', 'Practice'],
                ['performance', 'Performance'],
                ['simple', 'Simple'],
            ]);
            this.fields.font_size = this._field(form, 'Font Size', 'font_size', 'number');
            this.fields.show_song_map = this._checkboxField(form, 'Show Song Map', 'show_song_map');
            this.fields.show_metadata = this._checkboxField(form, 'Show Metadata', 'show_metadata');

            form.appendChild(this._sectionTitle('Arrangement'));
            this.fields.arrangement = this._textareaField(
                form,
                'Arrangement',
                'arrangement',
                'One section name per line',
            );

            form.appendChild(this._sectionTitle('Practice Notes'));
            this.fields.practice_notes_general = this._textareaField(
                form,
                'General Notes',
                'practice_notes_general',
                'One note per line',
            );

            this.sectionsContainer = this._element('div', 'song-editor__sections');
            form.appendChild(this._sectionTitle('Lyrics and Chords'));
            form.appendChild(this.sectionsContainer);

            this.status = this._element('div', 'song-editor__status');
            this.status.setAttribute('aria-live', 'polite');
            this.warningList = this._element('div', 'song-editor__warnings');
            this.warningList.hidden = true;

            this.root.appendChild(form);
            this.root.appendChild(this.status);
            this.root.appendChild(this.warningList);
            this.container.replaceChildren(this.root);
        }

        _field(parent, labelText, name, type = 'text') {
            const input = this.document.createElement('input');
            input.type = type;
            return this._wrapControl(parent, labelText, name, input);
        }

        _textareaField(parent, labelText, name, placeholder = '') {
            const textarea = this.document.createElement('textarea');
            textarea.rows = 4;
            textarea.placeholder = placeholder;
            return this._wrapControl(parent, labelText, name, textarea);
        }

        _selectField(parent, labelText, name, options) {
            const select = this.document.createElement('select');
            options.forEach(([value, text]) => {
                const option = this.document.createElement('option');
                option.value = value;
                option.textContent = text;
                select.appendChild(option);
            });
            return this._wrapControl(parent, labelText, name, select);
        }

        _checkboxField(parent, labelText, name) {
            const checkbox = this.document.createElement('input');
            checkbox.type = 'checkbox';
            return this._wrapControl(parent, labelText, name, checkbox);
        }

        _wrapControl(parent, labelText, name, control) {
            const group = this._element('label', 'song-editor__field');
            const label = this._element('span', 'song-editor__label');
            label.textContent = labelText;
            control.name = name;
            control.setAttribute('data-field', name);
            this._bindControl(control);
            group.appendChild(label);
            group.appendChild(control);
            parent.appendChild(group);
            return control;
        }

        _bindControl(control) {
            control.addEventListener('input', () => {
                this.onFieldEdit(control.dataset.field, this._controlValue(control));
            });
            control.addEventListener('change', () => {
                this.onFieldEdit(control.dataset.field, this._controlValue(control));
            });
            control.addEventListener('blur', () => {
                this.onBlur();
            });
            control.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault?.();
                    this.flushRegeneration();
                }
            });
        }

        _populateFields() {
            if (!this.songData) {
                return;
            }

            this.fields.title.value = this.songData.title || '';
            this.fields.target_key.value = this.songData.target_key || '';
            this.fields.capo.value = this.songData.capo || '';
            this.fields.bpm.value = this.songData.bpm == null ? '' : String(this.songData.bpm);
            this.fields.time_signature.value = this.songData.time_signature || '';
            this.fields.style.value = this.style;
            this.fields.font_size.value = String(this.options.font_size);
            this.fields.show_song_map.checked = Boolean(this.options.show_song_map);
            this.fields.show_metadata.checked = Boolean(this.options.show_metadata);
            this.fields.arrangement.value = (this.songData.arrangement || []).join('\n');
            this.fields.practice_notes_general.value = (
                this.songData.practice_notes?.general || []
            ).join('\n');
        }

        _renderSectionFields() {
            this.sectionFields = {};
            this.sectionsContainer.replaceChildren();
            const sections = this.songData?.sections || {};

            Object.entries(sections).forEach(([sectionName, section]) => {
                const textarea = this.document.createElement('textarea');
                textarea.rows = 5;
                textarea.value = this._sectionToChordPro(section);
                textarea.setAttribute('data-field', `section:${sectionName}`);
                textarea.setAttribute('aria-label', `${sectionName} lyrics and chords`);
                this._bindControl(textarea);

                const group = this._element('label', 'song-editor__field song-editor__field--wide');
                const label = this._element('span', 'song-editor__label');
                label.textContent = sectionName;
                group.appendChild(label);
                group.appendChild(textarea);
                this.sectionsContainer.appendChild(group);
                this.sectionFields[sectionName] = textarea;
            });
        }

        _updateField(field, value) {
            if (!this.songData || !field) {
                return;
            }

            if (field.startsWith('section:')) {
                this._updateSection(field.slice('section:'.length), value);
                return;
            }

            if (field === 'style') {
                this.style = value || 'practice';
                this.songData.style = this.style;
            } else if (field === 'font_size') {
                this.options.font_size = Number(value) || 28;
            } else if (field === 'show_song_map' || field === 'show_metadata') {
                this.options[field] = Boolean(value);
            } else if (field === 'arrangement') {
                this.songData.arrangement = this._lines(value);
            } else if (field === 'practice_notes_general') {
                this.songData.practice_notes = {
                    ...(this.songData.practice_notes || {}),
                    general: this._lines(value),
                };
            } else if (field === 'bpm') {
                this.songData.bpm = value === '' ? null : Number(value);
            } else {
                this.songData[field] = value;
            }
        }

        _updateSection(sectionName, value) {
            const section = this.songData.sections?.[sectionName];
            if (!section) {
                return;
            }
            section.lines = String(value || '')
                .split(/\r?\n/)
                .map((line) => ({ chordpro: line }));
        }

        _scheduleRegeneration() {
            this._clearDebounce();
            this.debounceTimer = this.timers.setTimeout(() => {
                this.debounceTimer = null;
                this.regeneratePreview();
            }, this.debounceMs);
        }

        _clearDebounce() {
            if (this.debounceTimer !== null) {
                this.timers.clearTimeout(this.debounceTimer);
                this.debounceTimer = null;
            }
        }

        _controlValue(control) {
            if (control.type === 'checkbox') {
                return control.checked;
            }
            return control.value;
        }

        _lines(value) {
            return String(value || '')
                .split(/\r?\n|,/)
                .map((line) => line.trim())
                .filter(Boolean);
        }

        _sectionToChordPro(section) {
            return (section.lines || [])
                .map((line) => {
                    if (typeof line === 'string') {
                        return line;
                    }
                    if (line.chordpro || line.raw) {
                        return line.chordpro || line.raw;
                    }
                    return this._lineToChordPro(line);
                })
                .join('\n');
        }

        _lineToChordPro(line) {
            const text = String(line?.text || '');
            const chords = Array.isArray(line?.chords) ? [...line.chords] : [];
            chords.sort((a, b) => Number(b.position || 0) - Number(a.position || 0));

            let result = text;
            chords.forEach((chordInfo) => {
                const position = Math.max(0, Math.min(Number(chordInfo.position || 0), result.length));
                const chord = chordInfo.chord || '';
                result = `${result.slice(0, position)}[${chord}]${result.slice(position)}`;
            });
            return result;
        }

        _renderWarnings() {
            this.warningList.hidden = this.warnings.length === 0;
            if (!this.warnings.length) {
                this.warningList.replaceChildren();
                return;
            }

            const list = this.document.createElement('ul');
            this.warnings.forEach((warning) => {
                const item = this.document.createElement('li');
                item.textContent = warning;
                list.appendChild(item);
            });
            this.warningList.replaceChildren(list);
        }

        _setDisabled(disabled) {
            [
                ...Object.values(this.fields),
                ...Object.values(this.sectionFields),
            ].forEach((field) => {
                field.disabled = disabled;
            });
        }

        _setStatus(message, isError = false) {
            this.status.textContent = message;
            this.status.classList.toggle('is-error', isError);
        }

        _sectionTitle(text) {
            const heading = this.document.createElement('h3');
            heading.className = 'song-editor__section-title';
            heading.textContent = text;
            return heading;
        }

        _element(tagName, className) {
            const element = this.document.createElement(tagName);
            element.className = className;
            return element;
        }

        _resolveContainer(containerOrId) {
            const container = typeof containerOrId === 'string'
                ? this.document.getElementById(containerOrId)
                : containerOrId;

            if (!container) {
                throw new Error('SongEditor container not found');
            }
            return container;
        }

        _clone(value) {
            return JSON.parse(JSON.stringify(value));
        }
    }

    return SongEditor;
}));
