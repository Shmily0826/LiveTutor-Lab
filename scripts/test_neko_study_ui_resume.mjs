// Actual canonical UI methods with a local DOM/RPC fixture; no service or device.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {test} from 'node:test';
const source = readFileSync(new URL('../patches/neko-study-2026-10-10-product/static/main.js', import.meta.url), 'utf8');
const html = readFileSync(new URL('../patches/neko-study-2026-10-10-product/static/index.html', import.meta.url), 'utf8');
function section(first, next) {
  const start = source.indexOf(first), end = source.indexOf(next, start + first.length);
  assert.ok(start >= 0 && end > start, first);
  return source.slice(start, end);
}
const code = [
  section('function setGeneratedQuestion(', 'function renderFeedback('),
  section('function formatPluginError(', 'function formatTutorDiagnostic('),
  section('function setPasteError(', 'function setImagePreview('),
  section('function studyContextIsCurrent(', 'function normalizeVisionMaxImagePx('),
  section('function syncStatusQuestion(', 'function setAdvancedSettingsOpen('),
  section('async function refreshStatus(', 'async function loadQuestionContext('),
  section('async function loadQuestionContext(', 'function clearOcrAttribution('),
  section('async function startCourseSession(', 'async function generateQuestion('),
  section('async function generateQuestion(', 'async function evaluateAnswer('),
  section('async function evaluateAnswer(', 'async function refreshMemoryDeck('),
  section('function bindButton(', 'async function handleNekoCoachAction('),
].join('\n');
const q = (id='q1', attempt='a1') => ({question_id:id, attempt_id:attempt, question:'Which arrow?', options:['left','right']});
function fixture() {
  const elements = new Map(); let deviceCalls = 0;
  function node(id) {
    if (!elements.has(id)) elements.set(id, {textContent:'',value:'',hidden:true,disabled:false,checked:false,
      dataset:{},listeners:{},setAttribute(){},addEventListener(type,callback){this.listeners[type]=callback;},
      click(){return this.listeners.click?.();}});
    return elements.get(id);
  }
  const ui = {Error, document:{activeElement:null}, $id:node,
    t:(_,fallback)=>fallback, tf:(_,fallback)=>fallback, modeLabel:v=>v, compactText:v=>v,
    lastStatusPayload:{}, currentQuestion:null, hasInitializedCourseInput:false,
    studyMaterialRevision:0, statusRefreshRevision:0, studyServiceReady:false, uiActionInFlight:false,
    studyInputImageValue:'', answerInputImageValue:'', previousExplanation:null,
    currentSelectionContext:null,currentPracticeScope:null,pastePendingCount:0,ocrN:'',ocrT:'',
    calls:[],replies:[],statuses:[],previewCalls:[],
    setStatus:value=>{ui.statuses.push(value);node('statusLine').textContent=value;},
    setReply:value=>{ui.replies.push(value);node('replyText').textContent=value;},
    setImagePreview:(kind,value)=>{ui.previewCalls.push({kind,value});ui[kind==='study'?'studyInputImageValue':'answerInputImageValue']=value;},
    scrollReplyIntoView(){}, applyRuntimeConfig(){},syncLearningProfileUi(){},renderDiagnosis(){},
    renderFirstRunGuide(){},updateStudySummaries(){},renderNekoCoach(){},setModeButtons(){},setStudyState(){},
    clearOcrAttribution(){ui.ocrT=ui.ocrN='';},setQuestionContext(){},openPracticePanel(){},setPracticeScopeState(){},
    formatTutorDiagnostic:d=>d,renderFeedback:d=>{node('feedbackText').textContent=d.feedback;},
    updatePracticeCompletionAction(){},practiceCompletionMessage:()=>'',
    outcomeFormatters:{formatKnowledgeGuidanceEvidence:()=>'',formatSolutionNarrationNotice:()=>'',formatGeneralNarrationNotice:()=>''},
  };
  for (const id of ['questionText','questionStatus','questionTopicMeta','questionDifficultyMeta','questionAttemptMeta',
    'hintToggleBtn','hintText','feedbackPanel','feedbackText','masteryDeltaText','evaluationStatus','answerInput',
    'studyInput','studyInputPasteError','answerInputPasteError','studyMaterialControlNotice','selectedStudyCourse',
    'studyCourseId','usePreviousExplanation','selectionReason']) ui[id]=node(id);
  ui.studyCourseId.value='flutter-provider';
  const denied=()=>{deviceCalls++;throw Error('Device use forbidden');};
  Object.assign(ui,{navigator:{mediaDevices:{getUserMedia:denied,getDisplayMedia:denied,enumerateDevices:denied}},
    Audio:denied,AudioContext:denied,SpeechRecognition:denied,webkitSpeechRecognition:denied});
  ui.deviceCalls=()=>deviceCalls;
  ui.status={study_course_id:'A',study_session_id:'s1',status:'ready',current_question:q(),question_state:'pending'};
  ui.callPlugin=async(entry,args)=>{
    ui.calls.push({entry,args});
    if(entry==='study_status') return structuredClone(ui.status);
    if(entry==='__llm_tool__study_material') return {course_id:ui.status.study_course_id,material_control_submission:[]};
    if(entry==='study_submit_image'||entry==='study_explain_text')return {reply:'Accepted explanation'};
    if(entry==='study_evaluate_answer')return {feedback:'Actual fixture grade',verdict:'wrong',score:0};
    if(entry==='study_generate_question')return q('generated-q','generated-a');
    if(entry==='study_summarize_session')return {summary:'Current summary fixture'};
    if(entry==='study_get_practice_scope')return {active:false};
    if(entry==='study_question_context')return {no_data:true};
    throw Error('Unexpected entry '+entry);
  };
  vm.createContext(ui);vm.runInContext(code,ui);
  return ui;
}
test('fresh DOM restores actual public pending question and submits its original ids without re-quiz',async()=>{
  const ui=fixture();await ui.refreshStatus();
  assert.equal(ui.questionText.textContent,'Which arrow?');assert.equal(ui.questionAttemptMeta.textContent,'待回答');
  ui.answerInput.value='left';await ui.evaluateAnswer();
  const call=ui.calls.find(c=>c.entry==='study_evaluate_answer');
  assert.equal(call.args.question_id,'q1');assert.equal(call.args.attempt_id,'a1');
  assert.equal(ui.calls.some(c=>/generate_question|quiz/.test(c.entry)),false);
  assert.equal(ui.feedbackText.textContent,'Actual fixture grade');assert.equal(ui.deviceCalls(),0);
});
test('unchanged pending status retains answer draft, answer image and feedback',async()=>{
  const ui=fixture();await ui.refreshStatus();ui.answerInput.value='my unfinished answer';
  ui.answerInputImageValue='same-answer-image';ui.feedbackText.textContent='existing feedback';
  await ui.refreshStatus();
  assert.equal(ui.answerInput.value,'my unfinished answer');assert.equal(ui.answerInputImageValue,'same-answer-image');
  assert.equal(ui.feedbackText.textContent,'existing feedback');
});
test('same evaluated question retains freshly rendered grade feedback',async()=>{
  const ui=fixture();await ui.refreshStatus();ui.feedbackText.textContent='Current grade feedback';
  ui.status.question_state='evaluated';await ui.refreshStatus();
  assert.equal(ui.feedbackText.textContent,'Current grade feedback');assert.equal(ui.questionAttemptMeta.textContent,'已评分');
});
for(const change of ['course','session','question','attempt','text','none'])test(change+' change clears stale answer and feedback',async()=>{
  const ui=fixture();await ui.refreshStatus();ui.answerInput.value='old answer';ui.answerInputImageValue='old-image';
  ui.feedbackText.textContent='old feedback';
  if(change==='course')ui.status.study_course_id='B';
  if(change==='session')ui.status.study_session_id='s2';
  if(change==='question')ui.status.current_question.question_id='q2';
  if(change==='attempt')ui.status.current_question.attempt_id='a2';
  if(change==='text')ui.status.current_question.question='Another question';
  if(change==='none'){ui.status.current_question={};ui.status.question_state='none';}
  await ui.refreshStatus();assert.equal(ui.answerInput.value,'');assert.equal(ui.answerInputImageValue,'');
  assert.equal(ui.feedbackText.textContent,'');
  if(change==='none')assert.equal(ui.currentQuestion.question_id,undefined);
});
test('resume uses set_course and restores held question; fresh explicitly uses start and retires it',async()=>{
  const ui=fixture();await ui.refreshStatus();const base=ui.callPlugin;
  ui.callPlugin=async(entry,args)=>{
    if(entry==='study_set_course'||entry==='study_start_session'){
      ui.calls.push({entry,args});
      ui.status={...ui.status,study_course_id:args.course_id,study_session_id:'s'+ui.calls.length,
        current_question:entry==='study_set_course'?q():{},question_state:entry==='study_set_course'?'pending':'none'};
      return {course_id:args.course_id,session_id:ui.status.study_session_id};
    }
    return base(entry,args);
  };
  ui.studyCourseId.value='A';await ui.resumeCourseSession();
  assert.equal(ui.currentQuestion.question_id,'q1');assert.equal(ui.calls.filter(c=>c.entry==='study_set_course').length,1);
  await ui.startCourseSession();assert.equal(ui.currentQuestion.question_id,undefined);
  assert.equal(ui.calls.filter(c=>c.entry==='study_start_session').length,1);
  assert.match(html,/id="resumeCourseSessionBtn"[^>]*>选择 \/ 返回课程/);
  assert.match(html,/id="startCourseSessionBtn"[^>]*>新开 Session（退役当前题）/);
});
test('successful image reply survives final refresh failure and busy recovers without another submit',async()=>{
  const ui=fixture();await ui.refreshStatus();ui.studyInputImageValue='data:image/png;base64,fixture';
  ui.studyInput.value='Explain image';let accepted=false;const base=ui.callPlugin;
  ui.callPlugin=async(entry,args)=>{
    if(entry==='study_status'&&accepted)throw Error('Failed to fetch');
    if(entry==='study_submit_image')accepted=true;
    return base(entry,args);
  };
  const button=ui.$id('explainBtn');ui.bindButton(button,ui.explainText);await button.click();
  assert.equal(ui.$id('replyText').textContent,'Accepted explanation');
  assert.match(ui.$id('studyRefreshNotice').textContent,/回复已保留.*状态暂未刷新/);
  assert.equal(ui.studyServiceReady,false);assert.equal(ui.previousExplanation.reply,'Accepted explanation');
  assert.equal(ui.studyInputImageValue,'data:image/png;base64,fixture');
  assert.equal(ui.calls.filter(c=>c.entry==='study_submit_image').length,1);
  assert.equal(ui.uiActionInFlight,false);assert.equal(button.disabled,false);assert.equal(ui.deviceCalls(),0);
  ui.callPlugin=base;await ui.refreshStatus();assert.equal(ui.$id('studyRefreshNotice').hidden,true);
});
test('submit failure remains an honest failure; it never manufactures a successful explanation',async()=>{
  const ui=fixture();await ui.refreshStatus();ui.studyInput.value='literal text';const base=ui.callPlugin;
  ui.callPlugin=async(entry,args)=>{if(entry==='study_explain_text')throw Error('Failed to fetch');return base(entry,args);};
  const button=ui.$id('explainBtn');ui.bindButton(button,ui.explainText);await button.click();
  assert.match(ui.$id('replyText').textContent,/学习服务连接失败/);assert.equal(ui.previousExplanation,null);
  assert.equal(ui.$id('studyRefreshNotice').hidden,true);assert.equal(button.disabled,false);
});
test('late old status cannot replace a newer course question',async()=>{
  const ui=fixture();let done;const base=ui.callPlugin;
  ui.callPlugin=async(entry,args)=>entry==='study_status'?new Promise(resolve=>{done=resolve;}):base(entry,args);
  const old=ui.refreshStatus();ui.callPlugin=base;ui.status.study_course_id='B';ui.status.current_question=q('q-B','a-B');
  await ui.refreshStatus();done({study_course_id:'A',study_session_id:'old',current_question:q(),question_state:'pending'});
  await old;assert.equal(ui.lastStatusPayload.study_course_id,'B');assert.equal(ui.currentQuestion.question_id,'q-B');
});
new vm.Script(source); // Whole canonical main remains syntactically valid.

function deferred() {
  let resolve,reject;
  const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});
  return {promise,resolve,reject};
}
const operations = {
  generate:{entry:'study_generate_question',call:ui=>ui.generateQuestion({fromMaterial:true}),result:q('old-generated','old-attempt')},
  grade:{entry:'study_evaluate_answer',call:ui=>ui.evaluateAnswer(),result:{feedback:'OLD_GRADE',verdict:'wrong',score:0}},
  summary:{entry:'study_summarize_session',call:ui=>ui.summarizeSession(),result:{summary:'OLD_SUMMARY'}},
};
for(const [name,operation] of Object.entries(operations))for(const changed of ['course','session','material'])for(const failure of [false,true])
test(`${name} late ${failure?'failure':'success'} after ${changed} change leaves current DOM intact`,async()=>{
  const ui=fixture();await ui.refreshStatus();ui.studyInput.value='material';ui.answerInput.value='old answer';
  const wait=deferred();let entered;const ready=new Promise(done=>{entered=done;});const base=ui.callPlugin;
  ui.callPlugin=async(entry,args)=>{
    if(entry===operation.entry){ui.calls.push({entry,args});entered();return wait.promise;}
    return base(entry,args);
  };
  const button=ui.$id('operation');ui.bindButton(button,()=>operation.call(ui));const running=button.click();await ready;
  if(changed==='course')ui.status.study_course_id='B';
  if(changed==='session')ui.status.study_session_id='s-new';
  if(changed==='material')ui.studyMaterialRevision+=1;
  ui.status.current_question=q('current-q','current-a');await ui.refreshStatus();
  ui.answerInput.value='current answer';ui.feedbackText.textContent='current feedback';
  ui.setReply('CURRENT_REPLY');ui.setStatus('CURRENT_STATUS');
  const callsBefore=ui.calls.length;
  if(failure)wait.reject(Error('OLD_REMOTE_FAILURE'));else wait.resolve(operation.result);
  await running;
  assert.equal(ui.$id('replyText').textContent,'CURRENT_REPLY');assert.equal(ui.$id('statusLine').textContent,'CURRENT_STATUS');
  assert.equal(ui.currentQuestion.question_id,'current-q');assert.equal(ui.answerInput.value,'current answer');
  assert.equal(ui.feedbackText.textContent,'current feedback');assert.equal(ui.calls.length,callsBefore);
  assert.equal(ui.calls.filter(c=>c.entry===operation.entry).length,1);assert.equal(button.disabled,false);assert.equal(ui.deviceCalls(),0);
});
for(const field of ['question_id','attempt_id'])for(const failure of [false,true])
test(`grade late ${failure?'failure':'success'} after ${field} replacement is discarded`,async()=>{
  const ui=fixture();await ui.refreshStatus();ui.answerInput.value='old';const wait=deferred();
  const base=ui.callPlugin;let entered;const ready=new Promise(done=>{entered=done;});
  ui.callPlugin=async(entry,args)=>{if(entry==='study_evaluate_answer'){ui.calls.push({entry,args});entered();return wait.promise;}return base(entry,args);};
  const button=ui.$id('grade');ui.bindButton(button,ui.evaluateAnswer);const running=button.click();await ready;
  ui.currentQuestion={...ui.currentQuestion,[field]:'replacement'};ui.setReply('CURRENT_REPLY');ui.setStatus('CURRENT_STATUS');
  ui.feedbackText.textContent='CURRENT_FEEDBACK';const count=ui.calls.length;
  if(failure)wait.reject(Error('OLD_FAILURE'));else wait.resolve({feedback:'OLD_GRADE'});
  await running;assert.equal(ui.$id('replyText').textContent,'CURRENT_REPLY');assert.equal(ui.feedbackText.textContent,'CURRENT_FEEDBACK');
  assert.equal(ui.$id('statusLine').textContent,'CURRENT_STATUS');assert.equal(ui.calls.length,count);
});
test('current generate and summary results remain visible and use ordinary scope preparation',async()=>{
  const ui=fixture();await ui.refreshStatus();ui.studyInput.value='current material';const base=ui.callPlugin;
  ui.callPlugin=async(entry,args)=>{
    const result=await base(entry,args);
    if(entry==='study_generate_question'){ui.status.current_question=result;ui.status.question_state='pending';}
    return result;
  };
  await ui.generateQuestion();assert.equal(ui.currentQuestion.question_id,'generated-q');assert.equal(ui.$id('replyText').textContent,'Which arrow?');
  assert.ok(ui.calls.some(c=>c.entry==='study_get_practice_scope'));assert.ok(ui.calls.some(c=>c.entry==='study_question_context'));
  await ui.summarizeSession();assert.equal(ui.$id('replyText').textContent,'Current summary fixture');
});
for(const failure of [false,true])test(`stale scope-preparation ${failure?'failure':'success'} stops generation without applying old scope`,async()=>{
  const ui=fixture();await ui.refreshStatus();ui.studyInput.value='material';const wait=deferred();const base=ui.callPlugin;
  let entered;const ready=new Promise(done=>{entered=done;});let applied=0;ui.setPracticeScopeState=()=>{applied++;};
  ui.callPlugin=async(entry,args)=>{if(entry==='study_get_practice_scope'){ui.calls.push({entry,args});entered();return wait.promise;}return base(entry,args);};
  const button=ui.$id('generate');ui.bindButton(button,ui.generateQuestion);const running=button.click();await ready;
  ui.lastStatusPayload.study_course_id='B';ui.setReply('B_REPLY');
  if(failure)wait.reject(Error('OLD_PREPARATION'));else wait.resolve({active:true});await running;
  assert.equal(applied,0);assert.equal(ui.calls.some(c=>c.entry==='study_generate_question'),false);
  assert.equal(ui.$id('replyText').textContent,'B_REPLY');
});
for(const failure of [false,true])test(`late selection-context ${failure?'failure':'success'} does not update new course or request a quiz`,async()=>{
  const ui=fixture();await ui.refreshStatus();ui.studyInput.value='material';const wait=deferred(),base=ui.callPlugin;
  let entered;const ready=new Promise(done=>{entered=done;});let applied=0;ui.setQuestionContext=()=>{applied++;};
  ui.callPlugin=async(entry,args)=>{if(entry==='study_question_context'){ui.calls.push({entry,args});entered();return wait.promise;}return base(entry,args);};
  const button=ui.$id('generate');ui.bindButton(button,ui.generateQuestion);const running=button.click();await ready;
  ui.lastStatusPayload.study_course_id='B';ui.selectionReason.textContent='B_SELECTION';ui.setReply('B_REPLY');
  if(failure)wait.reject(Error('OLD_SELECTION'));else wait.resolve({selection_context_id:'old-context'});await running;
  assert.equal(applied,0);assert.equal(ui.selectionReason.textContent,'B_SELECTION');assert.equal(ui.$id('replyText').textContent,'B_REPLY');
  assert.equal(ui.calls.some(c=>/generate.*question/.test(c.entry)),false);
});
test('current optional selection failure still permits the existing literal-text generation fallback',async()=>{
  const ui=fixture();await ui.refreshStatus();ui.studyInput.value='literal material';const base=ui.callPlugin;
  ui.callPlugin=async(entry,args)=>{
    if(entry==='study_question_context'){ui.calls.push({entry,args});throw Error('Current optional selection unavailable');}
    const result=await base(entry,args);if(entry==='study_generate_question')ui.status.current_question=result;return result;
  };
  await ui.generateQuestion();assert.match(ui.selectionReason.textContent,/optional selection unavailable/);
  assert.equal(ui.calls.filter(c=>c.entry==='study_generate_question').length,1);assert.equal(ui.currentQuestion.question_id,'generated-q');
});
for(const [name,operation] of Object.entries(operations))test(`${name} current remote error remains visible and is not retried`,async()=>{
  const ui=fixture();await ui.refreshStatus();ui.studyInput.value='material';ui.answerInput.value='answer';const base=ui.callPlugin;
  ui.callPlugin=async(entry,args)=>{if(entry===operation.entry){ui.calls.push({entry,args});throw Error('CURRENT_REMOTE_FAILURE');}return base(entry,args);};
  const button=ui.$id('operation');ui.bindButton(button,()=>operation.call(ui));await button.click();
  assert.equal(ui.$id('replyText').textContent,'CURRENT_REMOTE_FAILURE');assert.equal(ui.calls.filter(c=>c.entry===operation.entry).length,1);
  assert.equal(button.disabled,false);
});
