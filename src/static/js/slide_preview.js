(function(root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.SlidePreview = factory();
    }
}(typeof window !== 'undefined' ? window : globalThis, function() {
    'use strict';

    const SLIDE_SELECTOR = [
        'section',
        '.bespoke-slide',
        '[data-marpit-pagination]',
        'svg[data-marpit-svg]',
    ].join(',');

    class SlidePreview {
        constructor(containerOrId, options = {}) {
            this.document = options.document || document;
            this.CustomEvent = options.CustomEvent
                || this.document.defaultView?.CustomEvent
                || (typeof CustomEvent !== 'undefined' ? CustomEvent : Event);
            this.container = this._resolveContainer(containerOrId);
            this.currentSlide = 0;
            this.totalSlides = 0;
            this.htmlContent = '';
            this.presenterMode = false;
            this.fullscreenMode = false;
            this.warnings = [];

            this._build();
            this._bindEvents();
            this._updateControls();
        }

        loadHtml(htmlContent, options = {}) {
            this.htmlContent = String(htmlContent || '');
            this.currentSlide = 0;
            this.totalSlides = this._resolveSlideCount(options);
            this.warnings = Array.isArray(options.warnings) ? options.warnings : [];
            this.iframe.onload = () => this._syncIframeSlide();
            this.iframe.srcdoc = this.htmlContent;
            this._renderWarnings();
            this._updateControls();
        }

        loadPreview(htmlContent, options = {}) {
            this.loadHtml(htmlContent, options);
        }

        next() {
            this.goToSlide(this.currentSlide + 1);
        }

        previous() {
            this.goToSlide(this.currentSlide - 1);
        }

        navigate(direction) {
            if (direction === 'next' || direction > 0) {
                this.next();
            } else if (direction === 'previous' || direction < 0) {
                this.previous();
            }
        }

        goToSlide(index) {
            const maxSlide = Math.max(this.totalSlides - 1, 0);
            const requestedSlide = Number.isFinite(index) ? index : 0;
            const nextSlide = Math.min(Math.max(requestedSlide, 0), maxSlide);

            if (nextSlide === this.currentSlide && this.totalSlides > 0) {
                this._syncIframeSlide();
                return;
            }

            this.currentSlide = nextSlide;
            this._syncIframeSlide();
            this._dispatch('slidepreview:navigate', {
                currentSlide: this.currentSlide,
                totalSlides: this.totalSlides,
            });
        }

        togglePresenterMode(force) {
            this.presenterMode = force === undefined ? !this.presenterMode : Boolean(force);
            this.root.classList.toggle('is-presenter-mode', this.presenterMode);
            this.presenterButton.setAttribute('aria-pressed', String(this.presenterMode));
            this.presenterButton.textContent = this.presenterMode ? 'Presenter On' : 'Presenter';
            this.iframe.dataset.presenterMode = String(this.presenterMode);

            const iframeDocument = this._iframeDocument();
            if (iframeDocument?.body?.classList) {
                iframeDocument.body.classList.toggle('band-deck-presenter-mode', this.presenterMode);
            }

            this._postMessage({
                type: 'band-deck:presenter-mode',
                enabled: this.presenterMode,
            });
            this._dispatch('slidepreview:presenter-mode', { enabled: this.presenterMode });
            return this.presenterMode;
        }

        async toggleFullscreen(force) {
            const shouldEnable = force === undefined ? !this.fullscreenMode : Boolean(force);

            if (shouldEnable) {
                if (this.container.requestFullscreen) {
                    await this.container.requestFullscreen();
                }
                this.fullscreenMode = true;
            } else {
                if (this.document.fullscreenElement && this.document.exitFullscreen) {
                    await this.document.exitFullscreen();
                }
                this.fullscreenMode = false;
            }

            this.root.classList.toggle('is-fullscreen', this.fullscreenMode);
            this.fullscreenButton.setAttribute('aria-pressed', String(this.fullscreenMode));
            this.fullscreenButton.textContent = this.fullscreenMode ? 'Exit Fullscreen' : 'Fullscreen';
            this._dispatch('slidepreview:fullscreen', { enabled: this.fullscreenMode });
            return this.fullscreenMode;
        }

        _build() {
            this.root = this._element('div', 'html-slide-preview');
            this.toolbar = this._element('div', 'html-slide-preview__toolbar');
            this.toolbar.setAttribute('role', 'toolbar');
            this.toolbar.setAttribute('aria-label', 'Slide preview controls');

            this.previousButton = this._button('Previous', 'Previous slide');
            this.statusLabel = this._element('span', 'html-slide-preview__status');
            this.statusLabel.setAttribute('aria-live', 'polite');
            this.nextButton = this._button('Next', 'Next slide');
            this.presenterButton = this._button('Presenter', 'Toggle presenter mode');
            this.presenterButton.setAttribute('aria-pressed', 'false');
            this.fullscreenButton = this._button('Fullscreen', 'Toggle fullscreen preview');
            this.fullscreenButton.setAttribute('aria-pressed', 'false');

            this.toolbar.appendChild(this.previousButton);
            this.toolbar.appendChild(this.statusLabel);
            this.toolbar.appendChild(this.nextButton);
            this.toolbar.appendChild(this.presenterButton);
            this.toolbar.appendChild(this.fullscreenButton);

            this.stage = this._element('div', 'html-slide-preview__stage');
            this.iframe = this.document.createElement('iframe');
            this.iframe.className = 'html-slide-preview__iframe';
            this.iframe.setAttribute('title', 'HTML slide deck preview');
            this.iframe.setAttribute('sandbox', 'allow-same-origin allow-scripts allow-popups allow-forms');
            this.stage.appendChild(this.iframe);

            this.warningList = this._element('div', 'html-slide-preview__warnings');
            this.warningList.hidden = true;

            this.root.appendChild(this.toolbar);
            this.root.appendChild(this.stage);
            this.root.appendChild(this.warningList);
            this.container.replaceChildren(this.root);
        }

        _bindEvents() {
            this.previousButton.addEventListener('click', () => this.previous());
            this.nextButton.addEventListener('click', () => this.next());
            this.presenterButton.addEventListener('click', () => this.togglePresenterMode());
            this.fullscreenButton.addEventListener('click', () => this.toggleFullscreen());
            this.root.addEventListener('keydown', (event) => this._handleKeydown(event));
            this.root.setAttribute('tabindex', '0');
        }

        _handleKeydown(event) {
            const key = event.key;
            if (['ArrowRight', 'PageDown', ' '].includes(key)) {
                event.preventDefault?.();
                this.next();
            } else if (['ArrowLeft', 'PageUp'].includes(key)) {
                event.preventDefault?.();
                this.previous();
            } else if (key === 'f' || key === 'F') {
                event.preventDefault?.();
                this.toggleFullscreen();
            } else if (key === 'p' || key === 'P') {
                event.preventDefault?.();
                this.togglePresenterMode();
            }
        }

        _syncIframeSlide() {
            this._applySlideVisibility();
            this._postMessage({
                type: 'band-deck:navigate',
                slide: this.currentSlide,
            });
            this._updateControls();
        }

        _applySlideVisibility() {
            const iframeDocument = this._iframeDocument();
            const slides = this._iframeSlides(iframeDocument);
            if (!slides.length) {
                return;
            }

            this.totalSlides = Math.max(this.totalSlides, slides.length);
            slides.forEach((slide, index) => {
                const isActive = index === this.currentSlide;
                slide.hidden = !isActive;
                slide.setAttribute?.('aria-hidden', String(!isActive));
                if (slide.style) {
                    slide.style.display = isActive ? '' : 'none';
                }
                if (slide.dataset) {
                    slide.dataset.bandDeckActive = String(isActive);
                }
                slide.classList.toggle('bespoke-marp-active', isActive);
            });
        }

        _iframeSlides(iframeDocument) {
            if (!iframeDocument?.querySelectorAll) {
                return [];
            }
            return Array.from(iframeDocument.querySelectorAll(SLIDE_SELECTOR));
        }

        _iframeDocument() {
            return this.iframe.contentDocument || this.iframe.contentWindow?.document || null;
        }

        _resolveSlideCount(options) {
            if (Number.isInteger(options.slideCount) && options.slideCount > 0) {
                return options.slideCount;
            }
            return this.extractSlideCount(this.htmlContent);
        }

        extractSlideCount(htmlContent) {
            if (!htmlContent) {
                return 0;
            }

            const parser = this.document.defaultView?.DOMParser || globalThis.DOMParser;
            if (parser) {
                const parsed = new parser().parseFromString(htmlContent, 'text/html');
                const count = parsed.querySelectorAll(SLIDE_SELECTOR).length;
                if (count > 0) {
                    return count;
                }
            }

            const sectionMatches = htmlContent.match(/<section\b/gi);
            if (sectionMatches?.length) {
                return sectionMatches.length;
            }

            const paginationMatches = htmlContent.match(/data-marpit-pagination=/gi);
            return paginationMatches?.length || 0;
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

        _updateControls() {
            const hasSlides = this.totalSlides > 0;
            const current = hasSlides ? this.currentSlide + 1 : 0;
            this.statusLabel.textContent = `${current} / ${this.totalSlides}`;
            this.previousButton.disabled = !hasSlides || this.currentSlide <= 0;
            this.nextButton.disabled = !hasSlides || this.currentSlide >= this.totalSlides - 1;
        }

        _postMessage(message) {
            this.iframe.contentWindow?.postMessage?.(message, '*');
        }

        _dispatch(type, detail) {
            this.container.dispatchEvent(new this.CustomEvent(type, { detail }));
        }

        _resolveContainer(containerOrId) {
            const container = typeof containerOrId === 'string'
                ? this.document.getElementById(containerOrId)
                : containerOrId;

            if (!container) {
                throw new Error('SlidePreview container not found');
            }
            return container;
        }

        _element(tagName, className) {
            const element = this.document.createElement(tagName);
            element.className = className;
            return element;
        }

        _button(text, label) {
            const button = this._element('button', 'html-slide-preview__button');
            button.type = 'button';
            button.textContent = text;
            button.setAttribute('aria-label', label);
            return button;
        }
    }

    return SlidePreview;
}));
