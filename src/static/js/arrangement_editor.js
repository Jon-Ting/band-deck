// Band-Deck Arrangement editor
//
// Provides a UI for editing the song arrangement order (with HTML5 drag-and-drop
// reorder), repeat counts per section, and intro / interlude / ending note
// fields. Edits debounce a single POST to /api/regenerate so the live preview
// updates as changes settle.

(function(root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.ArrangementEditor = factory();
    }
}(typeof window !== 'undefined' ? window : globalThis, function() {
    'use strict';

    /** Sections whose appearance is structural rather than song-bound. */
    var STRUCTURAL_KEYS = {
        intro: 'intro',
        interlude: 'interlude',
        outro: 'outro',
    };

    /** Step size for repeat counts (whole-number); helpers clamp/restrict. */
    var MIN_REPEAT = 1;
    var MAX_REPEAT = 9;

    class ArrangementEditor {
        constructor(containerOrId, options = {}) {
            this.document = options.document || document;
            this.Event = options.Event || this.document.defaultView?.Event || Event;
            this.container = this._resolveContainer(containerOrId);
            this.fetch = options.fetch || fetch.bind(globalThis);
            this.debounceMs = Number.isInteger(options.debounceMs) ? options.debounceMs : 500;
            this.timers = options.timers || {
                setTimeout: setTimeout.bind(globalThis),
                clearTimeout: clearTimeout.bind(globalThis),
            };
            this.endpoint = options.endpoint || '/api/regenerate';
            this.style = options.style || 'practice';
            this.preview = options.preview || null;

            this.songData = null;
            this.debounceTimer = null;
            this.regenerating = false;
            this.warnings = [];
            this.itemNodes = []; // visible arrangement rows keyed by `index`

            this._build();
        }

        setSongData(songData) {
            this.songData = this._clone(songData || {});
            this.style = this.songData.style || this.style;
            this._normaliseArrangement();
            this._renderList();
            this._renderNoteFields();
            this._setStatus('');
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
            this._setStatus('Regenerating…');
            this._setDisabled(true);

            try {
                const response = await this.fetch(this.endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        song: this.songData,
                        style: this.style,
                    }),
                });
                const result = await response.json();

                if (!response.ok) {
                    throw new Error(result.error || 'Failed to regenerate preview');
                }

                this.warnings = Array.isArray(result.warnings) ? result.warnings : [];
                this._renderWarnings();

                if (result.html_content && this.preview) {
                    const loadHtml = this.preview.loadHtml || this.preview.loadPreview;
                    if (loadHtml) {
                        loadHtml.call(this.preview, result.html_content, {
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
            this.root = this._element('div', 'arrangement-editor');

            const heading = this._element('h3', 'arrangement-editor__title');
            heading.textContent = 'Arrangement';
            this.root.appendChild(heading);

            const help = this._element('p', 'arrangement-editor__help');
            help.textContent =
                'Drag rows to reorder. Set a repeat count for the section that immediately follows; sections with repeats get rendered once per repeat. Use the note fields below to capture intro, interlude, and ending guidance.';
            this.root.appendChild(help);

            this.list = this._element('ol', 'arrangement-editor__list');
            this.list.setAttribute('aria-label', 'Song arrangement, draggable rows');
            this.root.appendChild(this.list);

            this.emptyState = this._element('div', 'arrangement-editor__empty');
            this.emptyState.textContent =
                'No arrangement yet. Add a section below or copy one from the song structure.';
            this.emptyState.hidden = true;
            this.root.appendChild(this.emptyState);

            this.notesContainer = this._element('div', 'arrangement-editor__notes');
            this.notesContainer.appendChild(this._sectionTitle('Section Notes'));
            this.fields = {};
            this.fields.intro = this._noteField(
                this.notesContainer, 'Intro Notes', 'intro'
            );
            this.fields.interlude = this._noteField(
                this.notesContainer, 'Interlude / Bridge Notes', 'interlude'
            );
            this.fields.outro = this._noteField(
                this.notesContainer, 'Ending / Outro Notes', 'outro'
            );
            this.root.appendChild(this.notesContainer);

            // Available insertions come from the song's section catalogue.
            this.adder = this._element('div', 'arrangement-editor__adder');
            const adderLabel = this._element('span', 'arrangement-editor__label');
            adderLabel.textContent = 'Add section:';
            this.adder.appendChild(adderLabel);
            this.adderSelect = this.document.createElement('select');
            this.adderSelect.setAttribute('aria-label', 'Add a section to the arrangement');
            this.adder.appendChild(this.adderSelect);
            this.adderButton = this._element('button', 'arrangement-editor__add');
            this.adderButton.type = 'button';
            this.adderButton.textContent = 'Add';
            this.adder.appendChild(this.adderButton);
            this.adderButton.addEventListener('click', () => this._onAdd());
            this.root.appendChild(this.adder);

            this.status = this._element('div', 'arrangement-editor__status');
            this.status.setAttribute('aria-live', 'polite');
            this.warningList = this._element('div', 'arrangement-editor__warnings');
            this.warningList.hidden = true;
            this.root.appendChild(this.status);
            this.root.appendChild(this.warningList);

            this.container.replaceChildren(this.root);
        }

        _renderList() {
            // Preserve focus on whichever repeat-count input was being edited,
            // so drag/insert/remove don't blow away the user's in-flight typing.
            const active = this.document.activeElement;
            const activeKey = active?.dataset?.repeatFor || null;

            const arrangement = Array.isArray(this.songData?.arrangement)
                ? this.songData.arrangement
                : [];
            this.itemNodes = [];

            const repeatCounts = this._repeatCounts();
            this.list.replaceChildren();
            this.emptyState.hidden = arrangement.length > 0;

            arrangement.forEach((sectionName, index) => {
                const row = this._buildRow(sectionName, index, repeatCounts[sectionName] || 0);
                this.list.appendChild(row);
                this.itemNodes.push(row);
            });

            this._renderAdderOptions();

            if (activeKey) {
                const restored = this.list.querySelector(
                    `[data-repeat-for="${activeKey}"]`
                );
                if (restored && typeof restored.focus === 'function') {
                    restored.focus();
                }
            }
        }

        _renderAdderOptions() {
            const catalogue = this.songData?.sections
                ? Object.keys(this.songData.sections).sort()
                : [];
            this.adderSelect.replaceChildren();

            if (!catalogue.length) {
                const option = this.document.createElement('option');
                option.value = '';
                option.textContent = 'No sections available';
                this.adderSelect.appendChild(option);
                this.adderSelect.disabled = true;
                this.adderButton.disabled = true;
                return;
            }

            this.adderSelect.disabled = false;
            this.adderButton.disabled = false;

            const placeholder = this.document.createElement('option');
            placeholder.value = '';
            placeholder.textContent = 'Select a section…';
            placeholder.disabled = true;
            placeholder.selected = true;
            this.adderSelect.appendChild(placeholder);

            catalogue.forEach((name) => {
                const option = this.document.createElement('option');
                option.value = name;
                option.textContent = name;
                this.adderSelect.appendChild(option);
            });
        }

        _buildRow(sectionName, index, repeatCount) {
            const row = this._element('li', 'arrangement-editor__row');
            row.setAttribute('data-section', sectionName);
            row.draggable = true;
            row.setAttribute('aria-label', `Arrangement row for ${sectionName}`);

            // Drag handle (visual affordance; the whole row is draggable).
            const handle = this._element('span', 'arrangement-editor__handle');
            handle.textContent = '⋮⋮';
            handle.setAttribute('aria-hidden', 'true');
            handle.title = 'Drag to reorder';
            row.appendChild(handle);

            // Section name (non-editable display).
            const name = this._element('span', 'arrangement-editor__name');
            name.textContent = sectionName;
            row.appendChild(name);

            // Repeat count controls.
            const repeatWrap = this._element('label', 'arrangement-editor__repeat');
            const repeatLabel = this._element('span', 'arrangement-editor__repeat-label');
            repeatLabel.textContent = 'Repeats after';
            const repeatInput = this.document.createElement('input');
            repeatInput.type = 'number';
            repeatInput.min = String(MIN_REPEAT);
            repeatInput.max = String(MAX_REPEAT);
            repeatInput.value = repeatCount > 0 ? String(repeatCount) : '';
            repeatInput.placeholder = '—';
            repeatInput.setAttribute('aria-label', `Repeat count for ${sectionName}`);
            repeatInput.setAttribute('data-repeat-for', sectionName);
            repeatInput.addEventListener('input', () => {
                this._onRepeatChange(sectionName, repeatInput.value);
            });
            repeatInput.addEventListener('change', () => {
                this._onRepeatChange(sectionName, repeatInput.value);
            });
            repeatWrap.appendChild(repeatLabel);
            repeatWrap.appendChild(repeatInput);
            row.appendChild(repeatWrap);

            // Remove button.
            const removeBtn = this._element(
                'button', 'arrangement-editor__remove'
            );
            removeBtn.type = 'button';
            removeBtn.textContent = 'Remove';
            removeBtn.setAttribute('aria-label', `Remove ${sectionName} from arrangement`);
            removeBtn.addEventListener('click', () => this._onRemove(sectionName));
            row.appendChild(removeBtn);

            // Wire DnD handlers on the row.
            row.addEventListener('dragstart', (e) => this._onDragStart(e, sectionName));
            row.addEventListener('dragover', (e) => this._onDragOver(e, sectionName));
            row.addEventListener('dragleave', () => row.classList.remove('is-drag-over'));
            row.addEventListener('drop', (e) => this._onDrop(e, sectionName));
            row.addEventListener('dragend', () => {
                row.classList.remove('is-drag-over');
                this.list.classList.remove('is-dragging');
                this._dragKey = null;
            });

            return row;
        }

        _onDragStart(event, sectionName) {
            this._dragKey = sectionName;
            this.list.classList.add('is-dragging');
            if (event.dataTransfer) {
                event.dataTransfer.effectAllowed = 'move';
                try { event.dataTransfer.setData('text/plain', sectionName); } catch (_) { /* some browsers throw */ }
            }
        }

        _onDragOver(event, _sectionName) {
            event.preventDefault();
            if (event.dataTransfer) {
                event.dataTransfer.dropEffect = 'move';
            }
            const row = event.currentTarget;
            if (row) row.classList.add('is-drag-over');
        }

        _onDrop(event, targetSectionName) {
            event.preventDefault();
            const draggedKey = this._dragKey
                || (event.dataTransfer ? event.dataTransfer.getData('text/plain') : null);
            if (!draggedKey || draggedKey === targetSectionName) {
                event.currentTarget.classList.remove('is-drag-over');
                return;
            }

            const arrangement = this._safeArrangement();
            const fromIdx = arrangement.indexOf(draggedKey);
            const toIdx = arrangement.indexOf(targetSectionName);
            if (fromIdx === -1 || toIdx === -1) {
                event.currentTarget.classList.remove('is-drag-over');
                return;
            }

            // Drop-on-row semantics: insert the dragged section immediately
            // before the target's slot. When dragging forward (fromIdx <
            // toIdx) we have to subtract one from toIdx after removing
            // fromIdx so the target's post-removal position is preserved.
            arrangement.splice(fromIdx, 1);
            const insertIdx = fromIdx < toIdx ? toIdx - 1 : toIdx;
            arrangement.splice(insertIdx, 0, draggedKey);
            this.songData.arrangement = arrangement;
            this._scheduleRegeneration();
            this._renderList();
        }

        _onAdd() {
            // Arrangements are ordered lists and are allowed to repeat sections
            // (e.g., "Verse 1, Chorus, Verse 1, Chorus"); always append.
            const name = this.adderSelect.value;
            if (!name) return;
            const arrangement = this._safeArrangement();
            arrangement.push(name);
            this.songData.arrangement = arrangement;
            this.adderSelect.value = '';
            this._scheduleRegeneration();
            this._renderList();
        }

        _onRemove(sectionName) {
            const arrangement = this._safeArrangement().filter(
                (name) => name !== sectionName
            );
            this.songData.arrangement = arrangement;
            this._clearRepeatFor(sectionName);
            this._scheduleRegeneration();
            this._renderList();
        }

        _onRepeatChange(sectionName, rawValue) {
            const value = Number(rawValue);
            if (!Number.isFinite(value) || value < MIN_REPEAT) {
                this._clearRepeatFor(sectionName);
                this._scheduleRegeneration();
                return;
            }
            const clamped = Math.max(MIN_REPEAT, Math.min(MAX_REPEAT, Math.trunc(value)));
            const counts = this._repeatCounts();
            counts[sectionName] = clamped;
            this.songData.section_repeats = counts;
            this._scheduleRegeneration();
        }

        _clearRepeatFor(sectionName) {
            const counts = this._repeatCounts();
            if (counts[sectionName]) {
                delete counts[sectionName];
            }
            this.songData.section_repeats = counts;
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

        _repeatCounts() {
            const existing = this.songData?.section_repeats || {};
            return { ...existing };
        }

        _safeArrangement() {
            return Array.isArray(this.songData?.arrangement)
                ? [...this.songData.arrangement]
                : [];
        }

        /** Coerce stored arrangement data into the canonical shape used by
         *  arrangement editing. Repeated/compound arrangements ("V1 x2, Chorus")
         *  are handled by the section_repeats map rather than duplicated rows. */
        _normaliseArrangement() {
            if (!this.songData) return;
            if (!Array.isArray(this.songData.arrangement)) {
                this.songData.arrangement = [];
            }
        }

        _renderNoteFields() {
            const notes = (this.songData?.practice_notes) || {};
            this.fields.intro.value = (notes[STRUCTURAL_KEYS.intro] || []).join('\n');
            this.fields.interlude.value = (notes[STRUCTURAL_KEYS.interlude] || []).join('\n');
            this.fields.outro.value = (notes[STRUCTURAL_KEYS.outro] || []).join('\n');
        }

        _onNoteEdit(kind, value) {
            const lines = String(value || '')
                .split(/\r?\n/)
                .map((line) => line.trim())
                .filter(Boolean);
            const notes = { ...(this.songData?.practice_notes || {}) };
            if (lines.length) {
                notes[STRUCTURAL_KEYS[kind]] = lines;
            } else {
                delete notes[STRUCTURAL_KEYS[kind]];
            }
            this.songData.practice_notes = notes;
            this._scheduleRegeneration();
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

        _setStatus(message, isError = false) {
            this.status.textContent = message;
            this.status.classList.toggle('is-error', isError);
        }

        _setDisabled(disabled) {
            Object.values(this.fields || {}).forEach((field) => {
                field.disabled = disabled;
            });
            this.itemNodes.forEach((row) => {
                row.querySelectorAll('input, button').forEach((control) => {
                    control.disabled = disabled;
                });
            });
            if (this.adderButton) this.adderButton.disabled = disabled;
            if (this.adderSelect) this.adderSelect.disabled = disabled;
        }

        _noteField(parent, labelText, kind) {
            const group = this._element('label', 'arrangement-editor__field');
            const label = this._element('span', 'arrangement-editor__label');
            label.textContent = labelText;
            const textarea = this.document.createElement('textarea');
            textarea.rows = 3;
            textarea.setAttribute('data-note-kind', kind);
            textarea.addEventListener('input', () => this._onNoteEdit(kind, textarea.value));
            textarea.addEventListener('blur', () => this.flushRegeneration());
            group.appendChild(label);
            group.appendChild(textarea);
            parent.appendChild(group);
            return textarea;
        }

        _sectionTitle(text) {
            const heading = this.document.createElement('h4');
            heading.className = 'arrangement-editor__section-title';
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
                throw new Error('ArrangementEditor container not found');
            }
            return container;
        }

        _clone(value) {
            return JSON.parse(JSON.stringify(value));
        }
    }

    return ArrangementEditor;
}));
