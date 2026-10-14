/** Read-only incremental E2E for the real daily store. No teaching requests. */
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

const hash=value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
export async function checkStudyReadiness(page,steps){
  const ready=()=>page.waitForFunction(()=>studyServiceReady && !uiActionInFlight,null,{timeout:30000});
  const snapshot=()=>page.evaluate(()=>({guard:globalThis.NekoCapturePolicy?.getResult(),
    course:lastStatusPayload.study_course_id,session:lastStatusPayload.study_session_id,
    question:lastStatusPayload.current_question,state:lastStatusPayload.question_state,
    displayedQuestion:currentQuestion,status:document.querySelector('#statusLine')?.textContent,
    title:document.title,textOnly:globalThis.__NEKO_TEXT_ONLY__===true}));
  await ready();const before=await snapshot();
  assert.equal(before.guard?.status,'installed');assert.equal(before.guard?.captureBlocked,true);
  assert.equal(before.textOnly,true);
  assert.ok(before.session);assert.ok(['none','pending','evaluated'].includes(before.state));
  if(before.state!=='none')assert.equal(before.displayedQuestion.question_id,before.question.question_id);
  await page.click('#refreshBtn');await ready();const after=await snapshot();
  assert.equal(after.course,before.course);assert.equal(after.session,before.session);
  assert.deepEqual(after.question,before.question);assert.equal(after.state,before.state);
  steps.push({step:'real_daily_readonly_ready_and_refresh',course_hash:hash(before.course),
    session_hash:hash(before.session),question_hash:hash(before.question),question_state:before.state,
    guard_installed:true,capture_blocked:true,status:before.status,title:before.title});
}
