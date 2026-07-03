const assert = require('node:assert/strict');
const test = require('node:test');

const ArrangementEditor = require('../src/static/js/arrangement_editor.js');

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
    this.checked = false;
    this.value = '';
    this.textContent = '';
    this.type = '';
    this.name = '';
    this.draggable = false;
    this.placeholder = '';
    this.min = '';
    this.max = '';
    this.rows = 0;
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
    if (name.startsWith('data-')) {
      const key = name
        .slice(5)
        .replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
      this.dataset[key] = String(value);
    }
  }

  getAttribute(name) {
    return this.attributes[name];
  }

  addEventListener(type, callback) {
    this.eventListeners[type] = this.eventListeners[type] || [];
    this.eventListeners[type].push(callback);
  }

  dispatchEvent(event) {
    event.target = event.target || this;
    (this.eventListeners[event.type] || []).forEach((callback) => callback(event));
  }

  querySelectorAll(selector) {
    // Simplified for our usage: collect elements with a matching attribute.
    // Supports `[attr]` (presence), `[attr="value"]` (exact), and `[attr=foo]`.
    const attrMatch = selector.match(/\[([a-zA-Z0-9_-]+)(?:=["']?([^"'\]]+)["']?)?\]/);
    const matches = [];
    const visit = (node) => {
      if (!node) return;
      if (attrMatch && node.attributes) {
        const attrName = attrMatch[1];
        if (!(attrName in node.attributes)) {
          // fall through to children
        } else if (attrMatch[2] === undefined) {
          matches.push(node);
        } else if (node.attributes[attrName] === attrMatch[2]) {
          matches.push(node);
        }
      }
      if (node.children) {
        node.children.forEach(visit);
      }
    };
    visit(this);
    return matches;
  }

  querySelector(selector) {
    const matches = this.querySelectorAll(selector);
    return matches.length ? matches[0] : null;
  }
}

class FakeDocument {
  constructor() {
    this.elementsById = {};
  }

  createElement(tagName) {
    return new FakeElement(tagName, this);
  }

  getElementById(id) {
    return this.elementsById[id] || null;
  }
}

class FakeEvent {
  constructor(type, init = {}) {
    this.type = type;
    this.key = init.key;
    this.detail = init.detail;
    this.dataTransfer = init.dataTransfer || null;
    this.currentTarget = init.currentTarget || null;
    this.target = init.target || null;
    this.defaultPrevented = false;
  }

  preventDefault() {
    this.defaultPrevented = true;
  }
}

class FakeDataTransfer {
  constructor(initial = {}) {
    this.data = new Map();
    Object.entries(initial).forEach(([k, v]) => this.data.set(k, v));
    this.effectAllowed = 'all';
    this.dropEffect = 'none';
  }

  setData(format, value) {
    this.data.set(format, value);
  }

  getData(format) {
    return this.data.get(format) || '';
  }
}

function makeTimers() {
  let nextId = 1;
  const callbacks = new Map();
  return {
    callbacks,
    setTimeout(callback, delay) {
      const id = nextId++;
      callbacks.set(id, { callback, delay });
      return id;
    },
    clearTimeout(id) {
      callbacks.delete(id);
    },
    async runOnlyTimer() {
      assert.equal(callbacks.size, 1);
      const [id, scheduled] = callbacks.entries().next().value;
      callbacks.delete(id);
      await scheduled.callback();
      return scheduled;
    },
  };
}

function makeSong() {
  return {
    title: 'Example Song',
    authors: ['Example Writer'],
    target_key: 'D',
    sections: {
      'Verse 1': { name: 'Verse 1', type: 'verse', lines: [] },
      'Verse 2': { name: 'Verse 2', type: 'verse', lines: [] },
      Chorus: { name: 'Chorus', type: 'chorus', lines: [] },
      Bridge: { name: 'Bridge', type: 'bridge', lines: [] },
    },
    arrangement: ['Verse 1', 'Chorus', 'Verse 2', 'Bridge'],
    practice_notes: {
      intro: ['Wait 4 beats before starting'],
      outro: ['Hold last chord 2 bars'],
    },
  };
}

function makeEditor(options = {}) {
  const fakeDocument = new FakeDocument();
  const container = new FakeElement('div', fakeDocument);
  fakeDocument.elementsById.editor = container;
  const timers = makeTimers();
  const fetchCalls = [];
  const previewLoads = [];
  const editor = new ArrangementEditor('editor', {
    document: fakeDocument,
    Event: FakeEvent,
    timers,
    fetch: async (url, init) => {
      fetchCalls.push({ url, init });
      return {
        ok: true,
        json: async () => ({
          html_content: '<html><body><section>Regenerated</section></body></html>',
          warnings: [],
          slide_count: 3,
        }),
      };
    },
    preview: {
      loadHtml(html, previewOptions) {
        previewLoads.push({ html, previewOptions });
      },
    },
    debounceMs: 500,
    ...options,
  });
  return { container, editor, fetchCalls, previewLoads, timers, fakeDocument };
}

function findRow(container, sectionName) {
  return container.querySelector(
    `[data-section="${sectionName}"]`,
  );
}

test('renders one draggable row per arrangement entry with section notes', () => {
  const { container, editor } = makeEditor();

  editor.setSongData(makeSong());

  const rows = container.querySelectorAll('[data-section]').map((r) => r.attributes['data-section']);
  assert.deepEqual(rows, ['Verse 1', 'Chorus', 'Verse 2', 'Bridge']);

  const introNote = editor.fields.intro;
  assert.equal(introNote.value, 'Wait 4 beats before starting');
  assert.equal(editor.fields.outro.value, 'Hold last chord 2 bars');
  assert.equal(editor.fields.interlude.value, '');

  // The adder reflects the song's section catalogue.
  const options = editor.adderSelect.children.map((c) => c.value);
  assert.deepEqual(options, ['', 'Bridge', 'Chorus', 'Verse 1', 'Verse 2']);
});

test('repeat count input updates songData.section_repeats and triggers debounced regeneration', async () => {
  const { editor, fetchCalls, timers, container } = makeEditor();
  editor.setSongData(makeSong());

  const chorusRow = findRow(container, 'Chorus');
  const repeatInput = chorusRow.children.find(
    (c) => c.tagName === 'LABEL',
  ).children.find((c) => c.tagName === 'INPUT');
  repeatInput.value = '3';
  repeatInput.dispatchEvent(new FakeEvent('input'));

  assert.equal(editor.songData.section_repeats.Chorus, 3);
  assert.equal(timers.callbacks.size, 1);
  assert.equal([...timers.callbacks.values()][0].delay, 500);

  await timers.runOnlyTimer();

  assert.equal(fetchCalls.length, 1);
  const payload = JSON.parse(fetchCalls[0].init.body);
  assert.equal(payload.song.section_repeats.Chorus, 3);
});

test('drop with a current dragKey reorders the arrangement', () => {
  const { editor, container } = makeEditor();
  editor.setSongData(makeSong());

  const verse1Row = findRow(container, 'Verse 1');
  const bridgeRow = findRow(container, 'Bridge');
  editor._dragKey = 'Verse 1';

  const dropEvent = new FakeEvent('drop', { currentTarget: bridgeRow });
  bridgeRow.dispatchEvent(dropEvent);

  assert.deepEqual(editor.songData.arrangement, ['Chorus', 'Verse 2', 'Verse 1', 'Bridge']);

  const sectionsAfter = container.querySelectorAll('[data-section]').map(
    (r) => r.attributes['data-section'],
  );
  assert.deepEqual(sectionsAfter, ['Chorus', 'Verse 2', 'Verse 1', 'Bridge']);
});

test('drop on the same row is a no-op', () => {
  const { editor, container } = makeEditor();
  editor.setSongData(makeSong());

  const verse1Row = findRow(container, 'Verse 1');
  editor._dragKey = 'Verse 1';

  const dropEvent = new FakeEvent('drop', { currentTarget: verse1Row });
  verse1Row.dispatchEvent(dropEvent);

  assert.deepEqual(editor.songData.arrangement, ['Verse 1', 'Chorus', 'Verse 2', 'Bridge']);
});

test('add and remove buttons mirror songData.arrangement updates', () => {
  const { editor, container } = makeEditor();
  editor.setSongData(makeSong());

  // Remove "Chorus"
  const chorusRow = findRow(container, 'Chorus');
  const removeBtn = chorusRow.children.find(
    (c) => c.tagName === 'BUTTON',
  );
  removeBtn.dispatchEvent(new FakeEvent('click'));
  assert.deepEqual(editor.songData.arrangement, ['Verse 1', 'Verse 2', 'Bridge']);

  // Add "Verse 2" again via the adder.
  editor.adderSelect.value = 'Verse 2';
  editor.adderButton.dispatchEvent(new FakeEvent('click'));
  assert.deepEqual(editor.songData.arrangement, ['Verse 1', 'Verse 2', 'Bridge', 'Verse 2']);
});

test('intro/interlude/outro note edits write to practice_notes', async () => {
  const { editor, fetchCalls, timers } = makeEditor();
  editor.setSongData(makeSong());

  editor.fields.interlude.value = 'Two bars of percussion only';
  editor.fields.interlude.dispatchEvent(new FakeEvent('input'));

  assert.deepEqual(editor.songData.practice_notes.interlude, ['Two bars of percussion only']);

  await timers.runOnlyTimer();
  assert.equal(fetchCalls.length, 1);
  const payload = JSON.parse(fetchCalls[0].init.body);
  assert.deepEqual(payload.song.practice_notes.interlude, ['Two bars of percussion only']);
});

test('repeat count of zero clears the section_repeats entry', () => {
  const { editor } = makeEditor();
  const song = makeSong();
  song.section_repeats = { Chorus: 2 };
  editor.setSongData(song);

  editor._onRepeatChange('Chorus', '0');

  assert.equal(editor.songData.section_repeats.Chorus, undefined);
});

test('repeat count above max clamps to 9', () => {
  const { editor } = makeEditor();
  editor.setSongData(makeSong());

  editor._onRepeatChange('Chorus', '47');

  assert.equal(editor.songData.section_repeats.Chorus, 9);
});
