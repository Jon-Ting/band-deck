const assert = require('node:assert/strict');
const test = require('node:test');

const SlidePreview = require('../src/static/js/slide_preview.js');

class FakeClassList {
  constructor() {
    this.values = new Set();
  }

  add(...names) {
    names.forEach((name) => this.values.add(name));
  }

  remove(...names) {
    names.forEach((name) => this.values.delete(name));
  }

  contains(name) {
    return this.values.has(name);
  }

  toggle(name, force) {
    if (force === undefined) {
      if (this.values.has(name)) {
        this.values.delete(name);
        return false;
      }
      this.values.add(name);
      return true;
    }
    if (force) {
      this.values.add(name);
      return true;
    }
    this.values.delete(name);
    return false;
  }
}

class FakeElement {
  constructor(tagName, ownerDocument) {
    this.tagName = tagName.toUpperCase();
    this.ownerDocument = ownerDocument;
    this.children = [];
    this.attributes = {};
    this.dataset = {};
    this.style = {};
    this.classList = new FakeClassList();
    this.eventListeners = {};
    this.hidden = false;
    this.disabled = false;
    this.textContent = '';
  }

  appendChild(child) {
    this.children.push(child);
    child.parentNode = this;
    return child;
  }

  replaceChildren(...children) {
    this.children = [];
    children.forEach((child) => this.appendChild(child));
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  getAttribute(name) {
    return this.attributes[name];
  }

  addEventListener(type, callback) {
    this.eventListeners[type] = this.eventListeners[type] || [];
    this.eventListeners[type].push(callback);
  }

  dispatchEvent(event) {
    (this.eventListeners[event.type] || []).forEach((callback) => callback(event));
  }

  requestFullscreen() {
    this.ownerDocument.fullscreenElement = this;
    return Promise.resolve();
  }
}

class FakeIframe extends FakeElement {
  constructor(ownerDocument) {
    super('iframe', ownerDocument);
    this.contentWindow = {
      messages: [],
      postMessage: (message, targetOrigin) => {
        this.contentWindow.messages.push({ message, targetOrigin });
      },
    };
    this.contentDocument = null;
    this.srcdoc = '';
    this.onload = null;
  }
}

class FakeDocument {
  constructor() {
    this.elementsById = {};
    this.fullscreenElement = null;
    this.body = new FakeElement('body', this);
  }

  createElement(tagName) {
    if (tagName === 'iframe') {
      return new FakeIframe(this);
    }
    return new FakeElement(tagName, this);
  }

  getElementById(id) {
    return this.elementsById[id] || null;
  }

  exitFullscreen() {
    this.fullscreenElement = null;
    return Promise.resolve();
  }
}

class FakeEvent {
  constructor(type, init = {}) {
    this.type = type;
    this.detail = init.detail;
  }
}

function makePreview() {
  const fakeDocument = new FakeDocument();
  const container = new FakeElement('div', fakeDocument);
  fakeDocument.elementsById.preview = container;
  const preview = new SlidePreview('preview', {
    document: fakeDocument,
    CustomEvent: FakeEvent,
  });
  return { fakeDocument, container, preview };
}

function attachSlideDocument(preview, slideCount) {
  const slides = Array.from({ length: slideCount }, () => new FakeElement('section', preview.document));
  preview.iframe.contentDocument = {
    body: new FakeElement('body', preview.document),
    querySelectorAll: () => slides,
  };
  preview.iframe.onload();
  return slides;
}

test('loadHtml renders iframe preview with slide navigation state', () => {
  const { preview } = makePreview();

  preview.loadHtml('<html><body><section>A</section><section>B</section><section>C</section></body></html>');
  const slides = attachSlideDocument(preview, 3);

  assert.equal(preview.iframe.srcdoc.includes('<section>A</section>'), true);
  assert.equal(preview.totalSlides, 3);
  assert.equal(preview.currentSlide, 0);
  assert.equal(preview.statusLabel.textContent, '1 / 3');
  assert.equal(preview.previousButton.disabled, true);
  assert.equal(preview.nextButton.disabled, false);
  assert.equal(slides[0].hidden, false);
  assert.equal(slides[1].hidden, true);
  assert.equal(slides[2].hidden, true);
});

test('next and previous navigate iframe slides and clamp to bounds', () => {
  const { preview } = makePreview();

  preview.loadHtml('<section>One</section><section>Two</section>', { slideCount: 2 });
  const slides = attachSlideDocument(preview, 2);

  preview.next();
  preview.next();

  assert.equal(preview.currentSlide, 1);
  assert.equal(preview.statusLabel.textContent, '2 / 2');
  assert.equal(preview.nextButton.disabled, true);
  assert.equal(slides[0].hidden, true);
  assert.equal(slides[1].hidden, false);
  assert.equal(slides[1].classList.contains('bespoke-marp-active'), true);
  assert.equal(slides[0].classList.contains('bespoke-marp-active'), false);
  assert.deepEqual(preview.iframe.contentWindow.messages.at(-1).message, {
    type: 'band-deck:navigate',
    slide: 1,
  });

  preview.previous();

  assert.equal(preview.currentSlide, 0);
  assert.equal(preview.previousButton.disabled, true);
  assert.equal(slides[0].hidden, false);
  assert.equal(slides[0].classList.contains('bespoke-marp-active'), true);
  assert.equal(slides[1].classList.contains('bespoke-marp-active'), false);
  assert.equal(slides[1].hidden, true);
});

test('_applySlideVisibility mirrors Marp bespoke-marp-active class on the active slide', () => {
  const { preview } = makePreview();

  preview.loadHtml(
    '<svg data-marpit-svg=""><section>A</section></svg>' +
      '<svg data-marpit-svg=""><section>B</section></svg>' +
      '<svg data-marpit-svg=""><section>C</section></svg>',
    { slideCount: 3 },
  );
  const slides = attachSlideDocument(preview, 3);

  // Initial state: first slide is active per Marp's default theme rules.
  assert.equal(slides[0].classList.contains('bespoke-marp-active'), true);
  assert.equal(slides[1].classList.contains('bespoke-marp-active'), false);
  assert.equal(slides[2].classList.contains('bespoke-marp-active'), false);

  preview.goToSlide(2);

  assert.equal(slides[0].classList.contains('bespoke-marp-active'), false);
  assert.equal(slides[1].classList.contains('bespoke-marp-active'), false);
  assert.equal(slides[2].classList.contains('bespoke-marp-active'), true);
});

test('presenter and fullscreen toggles expose mode state', async () => {
  const { fakeDocument, container, preview } = makePreview();

  preview.loadHtml('<section>One</section>', { slideCount: 1 });
  attachSlideDocument(preview, 1);

  preview.togglePresenterMode();

  assert.equal(preview.presenterMode, true);
  assert.equal(preview.root.classList.contains('is-presenter-mode'), true);
  assert.equal(preview.presenterButton.getAttribute('aria-pressed'), 'true');
  assert.equal(preview.iframe.contentDocument.body.classList.contains('band-deck-presenter-mode'), true);

  await preview.toggleFullscreen();

  assert.equal(preview.fullscreenMode, true);
  assert.equal(fakeDocument.fullscreenElement, container);
  assert.equal(preview.root.classList.contains('is-fullscreen'), true);
  assert.equal(preview.fullscreenButton.getAttribute('aria-pressed'), 'true');

  await preview.toggleFullscreen();

  assert.equal(preview.fullscreenMode, false);
  assert.equal(fakeDocument.fullscreenElement, null);
  assert.equal(preview.root.classList.contains('is-fullscreen'), false);
});
