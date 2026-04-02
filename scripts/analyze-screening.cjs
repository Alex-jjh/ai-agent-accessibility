const fs = require('fs');
const tasks = JSON.parse(fs.readFileSync('test.raw.json','utf8'));
const traceDir = 'data/screening/traces';
const files = fs.readdirSync(traceDir).filter(f => f.startsWith('ecommerce_admin_') && f.endsWith('.json')).sort((a,b) => {
  return parseInt(a.match(/\d+/)[0]) - parseInt(b.match(/\d+/)[0]);
});

for (const f of files) {
  const d = JSON.parse(fs.readFileSync(traceDir + '/' + f, 'utf8'));
  const t = d.trace;
  const tid = parseInt(d.taskId);
  const task = tasks.find(x => x.task_id === tid);
  const intent = task ? task.intent : 'unknown';
  const refAnswer = task && task.eval && task.eval.reference_answers
    ? (task.eval.reference_answers.exact_match || task.eval.reference_answers.must_include || '')
    : '';
  const steps = t.steps || [];
  const lastStep = steps[steps.length - 1];
  const sendMatch = lastStep ? lastStep.action.match(/send_msg_to_user\("(.*)"\)/) : null;
  const agentAnswer = sendMatch ? sendMatch[1] : (lastStep ? lastStep.action : '');

  console.log('========================================');
  console.log('TASK ' + tid + ' | ' + (t.success ? 'SUCCESS' : 'FAIL') + ' | ' + steps.length + ' steps');
  console.log('INTENT: ' + intent);
  console.log('EXPECTED: ' + JSON.stringify(refAnswer));
  console.log('AGENT SAID: ' + agentAnswer.substring(0, 300));
  console.log('');
  for (const s of steps) {
    const r = (s.reasoning || '').substring(0, 200);
    const detail = (s.resultDetail || '').substring(0, 120);
    console.log('  Step ' + s.stepNum + ' [' + s.result + '] ' + s.action.substring(0, 120));
    if (detail) console.log('    detail: ' + detail);
    if (r) console.log('    reasoning: ' + r);
  }
  console.log('');
}
