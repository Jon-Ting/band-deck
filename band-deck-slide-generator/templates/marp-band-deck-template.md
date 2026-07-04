---
marp: true
theme: default
paginate: false
size: 16:9
---

<style>
section {
  font-family: Arial, Helvetica, sans-serif;
  color: #111827;
  padding: 34px 42px;
}
h1, h2 {
  color: #1d4ed8;
  margin-top: 0;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  font-size: 18px;
  font-weight: 700;
  border-bottom: 2px solid #d1d5db;
  padding-bottom: 8px;
  margin-bottom: 16px;
}
.layout {
  display: grid;
  grid-template-columns: 2.1fr 0.9fr;
  gap: 22px;
}
.line {
  font-family: "Courier New", monospace;
  margin: 12px 0;
}
.chart-lines {
  --chart-font-size: 30px;
  --lyric-font-size: var(--chart-font-size);
  --chord-font-size: var(--chart-font-size);
  --bar-font-size: var(--chart-font-size);
}
.line-pair {
  font-family: "Courier New", monospace;
  white-space: pre;
  margin: 10px 0 18px;
}
.chord-line {
  color: #c2410c;
  font-size: var(--chord-font-size);
  font-weight: 800;
  line-height: 1.05;
}
.lyric-line {
  color: #111827;
  font-size: var(--lyric-font-size);
  line-height: 1.1;
}
.song-map {
  font-size: 21px;
  line-height: 1.45;
}
.current {
  background: #dbeafe;
  color: #1d4ed8;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 4px;
}
.cue-box {
  background: #eef2f7;
  border-left: 6px solid #64748b;
  padding: 12px 14px;
  font-size: 21px;
  line-height: 1.35;
}
.warning {
  background: #fee2e2;
  border-left-color: #dc2626;
  color: #991b1b;
  font-weight: 800;
}
.context-label {
  color: #475569;
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}
.context-value {
  font-size: 24px;
  font-weight: 800;
  margin: 0 0 16px;
}
</style>

# {{title}}

<div class="meta">
<span>Key: {{target_key}}</span><span>BPM: {{bpm}}</span><span>Time: {{time_signature}}</span><span>Capo: {{capo}}</span>
</div>

**Authors:** {{authors}}  
**Song map:** {{song_map}}

<div class="cue-box">
{{overview_cues}}
</div>

---

## {{section_name}} {{section_repeat_label}}

<div class="meta">
<span>Key: {{target_key}}</span><span>BPM: {{bpm}}</span><span>Time: {{time_signature}}</span><span>Capo: {{capo}}</span>
</div>

<div class="layout">
<div class="chart-lines"{{chart_style_attr}}>
{{chorded_lyrics}}
</div>
<div class="song-map">
<div class="context-label">Now</div>
<div class="context-value">{{section_name}} {{section_repeat_label}}</div>
<div class="context-label">Next</div>
<div class="context-value">{{next_section}}</div>
<div class="context-label">After</div>
<div class="context-value">{{after_section}}</div>
</div>
</div>

{{bottom_cue}}
