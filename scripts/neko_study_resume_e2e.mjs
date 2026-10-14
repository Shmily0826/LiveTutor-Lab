/** Incremental Study E2E: real local SDK/checkpoint, labelled synthetic result cases. */
import assert from 'node:assert/strict';

export async function checkStudyResume(page, steps) {
  const expected = process.env.NEKO_STUDY_FIXTURE_QUESTION;
  assert.equal(expected, 'LOCAL_STAGE17_HELD_QUESTION');
  const idle = () => page.waitForFunction(() => studyServiceReady && !uiActionInFlight,
    null, {timeout: 30000});
  await idle();
  const ready = await page.evaluate(() => ({guard: globalThis.NekoCapturePolicy?.getResult(),
    question: currentQuestion, course: lastStatusPayload.study_course_id,
    session: lastStatusPayload.study_session_id, status: document.querySelector('#statusLine').textContent}));
  assert.equal(ready.guard?.status, 'installed');
  assert.equal(ready.course, 'stage17-a');
  assert.equal(ready.question.question_id, 'local-stage17-q');
  assert.equal(ready.question.attempt_id, 'local-stage17-attempt');
  assert.equal(ready.question.question, expected);
  assert.ok(!('answer' in ready.question) && !('answer_evaluation_cache' in ready.question));
  steps.push({step:'real_sdk_public_status_and_held_question', ...ready});
  await page.click('#practicePanel > summary');
  assert.equal(await page.isVisible('#questionText'),true);
  await page.fill('#answerInput','local unfinished draft');
  await page.click('#refreshBtn'); await idle();
  assert.equal(await page.inputValue('#answerInput'),'local unfinished draft');
  await page.reload({waitUntil:'domcontentloaded'}); await idle();
  await page.click('#practicePanel > summary');
  assert.equal(await page.isVisible('#questionText'),true);
  assert.equal(await page.textContent('#questionText'),expected);
  const select = async course => {
    await page.fill('#studyCourseId',course);
    await page.click('#resumeCourseSessionBtn'); await idle();
  };
  await select('stage17-b');
  assert.ok(!(await page.textContent('#questionText')).includes(expected));
  await select('stage17-a');
  assert.equal(await page.textContent('#questionText'),expected);
  assert.deepEqual(await page.evaluate(() => [currentQuestion.question_id,currentQuestion.attempt_id]),
    ['local-stage17-q','local-stage17-attempt']);
  steps.push({step:'real_sdk_reload_and_A_B_A_original_question'});

  // Only explain and delayed-grade results are doubles; other requests use the local SDK.
  let submits=0, failStatus=false, failedStatus=0;
  const syntheticId='stage17-labelled-synthetic-reply';
  const gradeId='stage17-labelled-delayed-grade';
  let gradeRequests=0, gradeEntered=false, releaseGrade;
  const gradeDelay=new Promise(resolve => {releaseGrade=resolve;});
  await page.route('**/runs**',async route => {
    const request=route.request(), url=new URL(request.url());
    const json=body => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
    if(request.method()==='POST' && url.pathname==='/runs'){
      const body=request.postDataJSON();
      if(body.entry_id==='study_evaluate_answer'){
        gradeRequests++; return json({run_id:gradeId});
      }
      if(body.entry_id==='study_explain_text'){
        submits++; failStatus=true; return json({run_id:syntheticId});
      }
      if(body.entry_id==='study_status' && failStatus){
        failedStatus++; return route.fulfill({status:503,body:'LOCAL_LABELLED_STATUS_FAILURE'});
      }
    }
    if(url.pathname==='/runs/'+syntheticId) return json({status:'succeeded'});
    if(url.pathname==='/runs/'+syntheticId+'/export') return json({items:[{type:'json',
      json:{success:true,data:{reply:'LOCAL_LABELLED_EXPLANATION_SUCCESS'}}}]});
    if(url.pathname==='/runs/'+gradeId) return json({status:'succeeded'});
    if(url.pathname==='/runs/'+gradeId+'/export'){
      gradeEntered=true; await gradeDelay;
      return json({items:[{type:'json',json:{success:true,data:{feedback:'LOCAL_OLD_COURSE_GRADE',verdict:'wrong',score:0}}}]});
    }
    return route.continue();
  });
  await page.fill('#answerInput','LOCAL_DELAYED_ANSWER_FIXTURE');
  await page.click('#evaluateAnswerBtn');
  const deadline=Date.now()+15000;
  while(!gradeEntered){
    if(Date.now()>deadline)throw Error('synthetic grade export was not requested');
    await new Promise(resolve => setTimeout(resolve,50));
  }
  // Simulate another role surface changing the course through the actual SDK.
  await page.evaluate(async () => {
    await callPlugin('study_set_course',{course_id:'stage17-b'});
    await refreshStatus();
  });
  const replyBeforeGrade=await page.textContent('#replyText');
  releaseGrade(); await idle();
  assert.equal(await page.evaluate(() => lastStatusPayload.study_course_id),'stage17-b');
  assert.equal(await page.textContent('#replyText'),replyBeforeGrade);
  assert.ok(!(await page.textContent('#feedbackText')).includes('LOCAL_OLD_COURSE_GRADE'));
  assert.equal(gradeRequests,1);
  steps.push({step:'LABELLED_SYNTHETIC_late_grade_after_actual_SDK_course_change_ignored',gradeRequests});
  await select('stage17-a');
  await page.fill('#studyInput','LOCAL_OFFLINE_EXPLANATION_FIXTURE');
  await page.click('#explainBtn');
  await page.waitForFunction(() => !uiActionInFlight &&
    document.querySelector('#studyRefreshNotice')?.hidden===false,null,{timeout:30000});
  assert.equal(await page.textContent('#replyText'),'LOCAL_LABELLED_EXPLANATION_SUCCESS');
  assert.equal(submits,1);assert.equal(failedStatus,1);
  assert.match(await page.textContent('#studyRefreshNotice'),/回复已保留/);
  assert.equal(await page.evaluate(() => studyServiceReady),false);
  steps.push({step:'LABELLED_SYNTHETIC_explain_success_status_failure_preserves_reply',submits,failedStatus});
  failStatus=false;
  await page.click('#refreshBtn'); await idle();
  assert.equal(await page.isHidden('#studyRefreshNotice'),true);
  assert.equal(await page.textContent('#replyText'),'LOCAL_LABELLED_EXPLANATION_SUCCESS');
  await page.click('#startCourseSessionBtn'); await idle();
  assert.ok(!(await page.textContent('#questionText')).includes(expected));
  await select('stage17-b'); await select('stage17-a');
  assert.ok(!(await page.textContent('#questionText')).includes(expected));
  steps.push({step:'real_sdk_explicit_fresh_retires_question_and_does_not_revive'});
}
