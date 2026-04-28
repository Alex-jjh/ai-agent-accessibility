const fs = require('fs');
const dir = 'data/regression/cases';
const tasks = JSON.parse(fs.readFileSync('test.raw.json', 'utf8'));
const files = fs.readdirSync(dir).filter(f => f.endsWith('.json'));

// Find latest run files by checking timestamps
const latest = {};
for (const f of files) {
  const d = JSON.parse(fs.readFileSync(dir + '/' + f, 'utf8'));
  const tid = String(d.taskId);
  const ts = d.trace?.steps?.[0]?.timestamp || '';
  if (!latest[tid] || ts > latest[tid].ts) {
    latest[tid] = { file: f, ts, data: d };
  }
}

for (const [tid, entry] of Object.entries(latest).sort((a,b) => parseInt(a[0]) - parseInt(b[0]))) {
  const d = entry.data;
  const t = d.trace;
  const task = tasks.find(x => x.task_id === parseInt(tid));
  const ref = task && task.eval && task.eval.reference_answers
    ? (task.eval.reference_answers.exact_match || task.eval.reference_answers.must_include || task.eval.reference_answers.fuzzy_match || '')
    : '';
  const steps = t.steps || [];
  const last = steps[steps.length - 1];
  const sendMatch = last ? last.action.match(/send_msg_to_user\("(.*)"\)/) : null;
  const ans = sendMatch ? sendMatch[1] : (last ? last.action : 'N/A');

  console.log('=== Task ' + tid + ' | ' + (t.success ? 'SUCCESS' : 'FAIL') + ' | ' + steps.length + ' steps ===');
  console.log('  Intent: ' + (task ? task.intent : 'unknown'));
  console.log('  Expected: ' + JSON.stringify(ref).substring(0, 100));
  console.log('  Agent: ' + ans.substring(0, 100));
  for (const s of steps) {
    const detail = (s.resultDetail || '').substring(0, 80);
    console.log('  step ' + s.stepNum + ' [' + s.result + '] ' + s.action.substring(0, 100) + (detail ? ' | ' + detail : ''));
  }
  console.log('');
}
