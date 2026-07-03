const assert = require('node:assert/strict');
const test = require('node:test');

const SongEditor = require('../src/static/js/song_editor.js');

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
    this.defaultPrevented = false;
  }

  preventDefault() {
    this.defaultPrevented = true;
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
    bpm: 72,
    time_signature: '4/4',
    sections: {
      'Verse 1': {
        name: 'Verse 1',
        type: 'verse',
        lines: [{ text: 'Placeholder lyric', chords: [{ chord: 'D', position: 0 }] }],
      },
      Chorus: {
        name: 'Chorus',
        type: 'chorus',
        lines: [{ text: 'Lift the hook', chords: [{ chord: 'G', position: 0 }] }],
      },
    },
    arrangement: ['Verse 1', 'Chorus'],
    practice_notes: { general: ['Watch the transition'] },
  };
}

function makeEditor(options = {}) {
  const fakeDocument = new FakeDocument();
  const container = new FakeElement('div', fakeDocument);
  fakeDocument.elementsById.editor = container;
  const timers = makeTimers();
  const fetchCalls = [];
  const previewLoads = [];
  const editor = new SongEditor('editor', {
    document: fakeDocument,
    Event: FakeEvent,
    timers,
    fetch: async (url, init) => {
      fetchCalls.push({ url, init });
      return {
        ok: true,
        json: async () => ({
          html_content: '<html><body><section>Updated</section></body></html>',
          warnings: ['Check section length'],
          slide_count: 2,
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
  return { container, editor, fetchCalls, previewLoads, timers };
}

test('renders editable metadata arrangement notes and section fields', () => {
  const { editor } = makeEditor();

  editor.setSongData(makeSong());

  assert.equal(editor.fields.title.value, 'Example Song');
  assert.equal(editor.fields.target_key.value, 'D');
  assert.equal(editor.fields.bpm.value, '72');
  assert.equal(editor.fields.arrangement.value, 'Verse 1\nChorus');
  assert.equal(editor.fields.practice_notes_general.value, 'Watch the transition');
  assert.equal(editor.sectionFields['Verse 1'].value.includes('[D]Placeholder lyric'), true);
});

test('input edits update song data and debounce regeneration for 500ms', async () => {
  const { editor, fetchCalls, previewLoads, timers } = makeEditor();
  editor.setSongData(makeSong());

  editor.fields.title.value = 'Edited Song';
  editor.fields.title.dispatchEvent(new FakeEvent('input'));

  assert.equal(editor.songData.title, 'Edited Song');
  assert.equal(timers.callbacks.size, 1);
  assert.equal([...timers.callbacks.values()][0].delay, 500);
  assert.equal(fetchCalls.length, 0);

  await timers.runOnlyTimer();

  assert.equal(fetchCalls.length, 1);
  assert.equal(fetchCalls[0].url, '/api/regenerate');
  const payload = JSON.parse(fetchCalls[0].init.body);
  assert.equal(payload.song.title, 'Edited Song');
  assert.equal(payload.style, 'practice');
  assert.deepEqual(payload.options, {
    show_metadata: true,
    show_song_map: true,
    font_size: 28,
  });
  assert.equal(previewLoads[0].html.includes('<section>Updated</section>'), true);
  assert.deepEqual(editor.warnings, ['Check section length']);
});

test('blur and Enter flush pending regeneration immediately', async () => {
  const { editor, fetchCalls, timers } = makeEditor();
  editor.setSongData(makeSong());

  editor.fields.arrangement.value = 'Chorus\nVerse 1';
  editor.fields.arrangement.dispatchEvent(new FakeEvent('input'));
  editor.fields.arrangement.dispatchEvent(new FakeEvent('blur'));
  await Promise.resolve();
  await Promise.resolve();

  assert.equal(timers.callbacks.size, 0);
  assert.equal(fetchCalls.length, 1);
  assert.deepEqual(JSON.parse(fetchCalls[0].init.body).song.arrangement, ['Chorus', 'Verse 1']);

  editor.fields.practice_notes_general.value = 'Start quietly';
  editor.fields.practice_notes_general.dispatchEvent(new FakeEvent('input'));
  const keyEvent = new FakeEvent('keydown', { key: 'Enter' });
  editor.fields.practice_notes_general.dispatchEvent(keyEvent);

  assert.equal(keyEvent.defaultPrevented, true);
  assert.equal(timers.callbacks.size, 0);
  assert.equal(fetchCalls.length, 2);
  assert.deepEqual(
    JSON.parse(fetchCalls[1].init.body).song.practice_notes.general,
    ['Start quietly'],
  );
});
