const fs = require('fs');
const tasks = JSON.parse(fs.readFileSync('test.raw.json', 'utf8'));

for (const summaryFile of ['ecommerce_21-50.json', 'reddit_27-70.json']) {
  const summary = JSON.parse(fs.readFileSync('data/screening/' + summaryFile, 'utf8'));
  console.log('============================================================');
  console.log('  ' + summaryFile);
  console.log('============================================================\n');

  for (const s of summary) {
    const tid = parseInt(s.taskId);
    const task = tasks.find(x => x.task_id === tid);
    const intent = task ? task.intent : 'unknown';
    const ref = task && task.eval && task.eval.reference_answers
      ? (task.eval.reference_answers.exact_match || task.eval.reference_answers.must_include || task.eval.reference_answers.fuzzy_match || '')
      : '';
    const evalType = task && task.eval ? (task.eval.eval_types || []).join(',') : 'unknown';

    // Try to load trace
    const traceFile = 'data/screening/traces/' + s.app + '_' + s.taskId + '.json';
    let agentAnswer = 'N/A';
    let steps = [];
    if (fs.existsSync(traceFile)) {
      const td = JSON.parse(fs.readFileSync(traceFile, 'utf8'));
      steps = td.trace.steps || [];
      const last = steps[steps.length - 1];
      if (last) {
        const m = last.action.match(/send_msg_to_user\("(.*)"\)/);
        agentAnswer = m ? m[1] : last.action;
      }
    }

    const status = s.success ? '✅ SUCCESS' : '❌ FAIL';
    console.log('--- Task ' + tid + ' | ' + status + ' | ' + s.steps + ' steps | ' + Math.round(s.durationMs/1000) + 's ---');
    console.log('Intent: ' + intent.substring(0, 120));
    console.log('Eval: ' + evalType);
    console.log('Expected: ' + JSON.stringify(ref).substring(0, 120));
    console.log('Agent: ' + agentAnswer.substring(0, 120));

    // Show step summary
    for (const step of steps) {
      const detail = (step.resultDetail || '').substring(0, 80);
      console.log('  step ' + step.stepNum + ' [' + step.result + '] ' + step.action.substring(0, 100) + (detail ? ' | ' + detail : ''));
    }
    console.log('');
  }
}
