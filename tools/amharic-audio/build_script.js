// Builds the recording script from the lines the Amharic app can speak.
// Run: node tools/amharic-audio/build_script.js
// Writes script.md (to read from while recording) and lines.json (used by split.py).
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const ROOT = path.join(__dirname, '..', '..');
const PER_TAKE = 20;

const html = fs.readFileSync(path.join(ROOT, 'amharic', 'index.html'), 'utf8');
const src = html.slice(html.indexOf('const UNITS'), html.indexOf('const KEY='));
const { UNITS, GRAMMAR, SCENES } = new Function(src + ';return{UNITS,GRAMMAR,SCENES}')();

const lines = [], seen = new Set();
function add(am, tr, en, where) {
  if (!am || seen.has(am)) return;
  seen.add(am);
  // File name comes from the text, so clips stay matched when lines are added or reordered.
  const file = crypto.createHash('sha1').update(am).digest('hex').slice(0, 10) + '.m4a';
  lines.push({ am, tr, en, where, file });
}
const forms = (x, y) => (x && typeof x === 'object') ? [[x.f, y.f, 'said to a woman'], [x.m, y.m, 'said to a man']] : [[x, y, '']];

UNITS.forEach(u => u.items.forEach(([id, am, tr, en]) => add(am, tr, en, 'Phrases')));
GRAMMAR.forEach(gr => gr.rows.forEach(([am, tr, en]) => { if (!am.includes('→')) add(am, tr, en, 'Grammar: ' + gr.title) }));
SCENES.forEach(sc => sc.turns.forEach(t => {
  if (t.npc) forms(t.npc.am, t.npc.tr).forEach(([am, tr, note]) => add(am, tr, t.npc.en + (note ? ` (${note})` : ''), 'Conversation: ' + sc.title));
  const c = t.opts.find(o => o.ok);
  if (t.type !== 'check' && c) add(c.am, c.tr, c.en, 'Conversation: ' + sc.title);
}));

const takes = [];
for (let i = 0; i < lines.length; i += PER_TAKE) takes.push(lines.slice(i, i + PER_TAKE));

fs.writeFileSync(path.join(__dirname, 'lines.json'), JSON.stringify(takes, null, 1) + '\n');

let md = `# Amharic recording script\n\n${lines.length} lines in ${takes.length} takes of up to ${PER_TAKE}.\n\n` +
  `Record each take as one file named \`take-01.m4a\`, \`take-02.m4a\`, and so on. ` +
  `Read the lines in order and leave about 2 seconds of silence between them. ` +
  `For lines with “…”, pause briefly (under a second) where the blank is. ` +
  `If you make a mistake, stop and record the whole take again.\n`;
takes.forEach((tk, i) => {
  md += `\n## Take ${String(i + 1).padStart(2, '0')}\n\n`;
  let where = '';
  tk.forEach((l, j) => {
    if (l.where !== where) { where = l.where; md += `*${where}*\n\n`; }
    md += `${j + 1}. **${l.am}** · ${l.tr} · ${l.en}\n`;
  });
});
fs.writeFileSync(path.join(__dirname, 'script.md'), md);
console.log(`${lines.length} lines, ${takes.length} takes → tools/amharic-audio/script.md`);
