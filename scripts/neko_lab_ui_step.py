"""Run one real Study UI action through the shared browser CLI."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'benchmarks/raw/evidence'
WRAPPER = r'D:\AI\tools\playwright-chrome\playwright-chrome.cmd'
MATERIAL = ('NEKO-LAB-20261008 固定学习材料。链式法则：当 y=f(u)，u=g(x) 时，'
            'dy/dx=(dy/du)×(du/dx)。例题 y=sin(x²)，内层 u=x²、外层 sin(u)，'
            '正确导数为 2x cos(x²)。常见错误是只写 cos(x²)，漏乘内层导数。'
            '请解释内外两层如何相乘，并给一道不同的复合函数练习题。')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['explain', 'followup', 'question', 'wrong', 'correct', 'ocr'])
    parser.add_argument('--text')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--fullscreen',action='store_true')
    parser.add_argument('--current-input',action='store_true')
    options = parser.parse_args()
    actions = {
        'explain': ('#studyInput', options.text or MATERIAL, '#explainBtn'),
        'followup': ('#studyInput', options.text or '你刚才给出的那道练习题，为什么要乘内层导数？请沿用上一轮的函数解释。', '#explainBtn'),
        'question': (None, None, '#generateQuestionBtn'),
        'wrong': ('#answerInput', options.text or '答案是 42。', '#evaluateAnswerBtn'),
        'correct': ('#answerInput', options.text, '#evaluateAnswerBtn'),
        'ocr': (None, None, '#ocrBtn'),
    }
    field, text, button = actions[options.phase]
    if options.phase == 'explain' and options.current_input:
        field, text = None, None
    if options.phase == 'correct' and not text:
        parser.error('--text must answer the actually generated question')
    operation = ''
    if options.phase == 'ocr' and options.fullscreen:
        operation += "await page.locator('#ocrCaptureMode').selectOption('fullscreen');\n"
    if options.phase == 'followup':
        operation += "await page.locator('#usePreviousExplanation').check();\n"
    if options.phase in {'question', 'wrong', 'correct'}:
        operation += "if (!await page.locator('#generateQuestionBtn').isVisible()) await page.locator('#practicePanel > summary').click();\n"
    if field:
        operation += f'await page.locator({json.dumps(field)}).fill({json.dumps(text, ensure_ascii=False)});\n'
    operation += f'await page.locator({json.dumps(button)}).click();\n'
    code = '''async (page) => {
  const started = Date.now();
    const material = page.context().pages().find(p => p.url().endsWith('/study-chain-rule.html'));
    page = page.context().pages().find(p => p.url().includes('/plugin/study_companion/ui/'));
    if (!page || (PHASE === 'ocr' && !material)) throw new Error('Required task-created pages are missing');
    await page.bringToFront();
    const profile = page.locator('#learningProfileModal');
    if (await profile.isVisible()) await profile.getByRole('button', {name:'Skip', exact:true}).click();
    const drawerClose = page.locator('#surfaceDrawerCloseBtn');
    if (await drawerClose.isVisible()) await drawerClose.click();
    ACTION
    if (PHASE === 'ocr') await material.bringToFront();
    await page.waitForFunction((selector) => !document.querySelector(selector)?.disabled,
                              BUTTON, {timeout: 55000});
    const state = await page.evaluate(() => {
      const read = (id) => document.getElementById(id)?.innerText || '';
      return {status: read('statusLine'), reply: read('replyText'), question: read('questionText'),
              evaluation: read('feedbackText'), evaluationStatus: read('evaluationStatus'),
              input: document.getElementById('studyInput')?.value || ''};
    });
    if (PHASE === 'ocr') return {phase:PHASE,elapsed_ms:Date.now()-started,status:state.status,
      materialMarkerFound:state.input.includes('NEKO-LAB-20261008'),
      chainRuleFound:/链式法则|复合函数求导/.test(state.input),
      sinFound:/sin/.test(state.input),inputChars:state.input.length};
    return {phase: PHASE, elapsed_ms: Date.now()-started, ...state};
}'''.replace('ACTION', operation).replace('BUTTON', json.dumps(button)).replace('PHASE', json.dumps(options.phase))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    script = EVIDENCE / f'ui-{options.phase}-callback.js'
    script.write_text(code, encoding='utf-8')
    if options.prepare_only:
        print(script)
        return
    process = subprocess.run([WRAPPER, '-s=neko-lab', 'run-code', '--filename', str(script)],
                             cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    (EVIDENCE / f'goal-ui-{options.phase}.txt').write_text(process.stdout + process.stderr, encoding='utf-8')
    print(process.stdout)
    print(process.stderr)
    raise SystemExit(process.returncode)


if __name__ == '__main__':
    main()
