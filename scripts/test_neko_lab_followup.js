const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname,
  '../benchmarks/raw/goal-isolated/study_companion/static/main.js'), 'utf8');
const start = source.indexOf('function buildFollowupText(');
const end = source.indexOf('\nasync function explainText', start);
assert.ok(start >= 0 && end > start, 'actual request helper must exist');
const context = {};
vm.runInNewContext(source.slice(start, end), context);
const previous = {input:'Differentiate (3x+1)^5.', reply:'15(3x+1)^4. 内层导数是 3。'};
const answer = '为什么要乘内层导数？';
const request = JSON.parse(context.buildFollowupText(answer,previous));
assert.equal(request.current_followup, answer);
assert.equal(request.previous_input, previous.input);
assert.equal(request.previous_explanation, previous.reply);
assert.equal(context.buildFollowupText(answer,null), answer);
assert.equal(previous.input,'Differentiate (3x+1)^5.');
console.log('Follow-up context preservation and fresh-input checks passed.');
