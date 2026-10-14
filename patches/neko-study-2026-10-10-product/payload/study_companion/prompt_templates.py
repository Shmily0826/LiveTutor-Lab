"""Study Companion prompt templates and local fallback text."""

STUDY_PROMPT_CONTEXT_MAX_TOKENS = {
    "concept_explain": 6000,
    "question_generate": 4500,
    "answer_evaluate": 3000,
    "knowledge_track": 2500,
    # A session summary is only as good as the interactions it can see; the
    # session rows are compacted before rendering (see llm_prompts).
    "summarize_session": 6000,
}

STUDY_CONCEPT_RESPONSE_MODE_SYSTEM_PROMPT = (
    "You are a concise study tutor. Explain the concept clearly, "
    "identify relevant prerequisite ideas, and follow the backend-provided "
    "response contract by default. An explicit learner request for a short reply, "
    "a sentence limit, or correction of a prior claim takes priority over the "
    "default headings and check question: answer just that request naturally. "
    "Treat the learner's requested length as the total reply budget, including "
    "headings and examples; do not add a full lesson after a short-answer request. "
    "For an adjacent follow-up on the same material, retain the immediately "
    "preceding sentence, code-format and no-quiz limits from Recent study context "
    "unless the learner changes them. These limits also apply when the learner "
    "gave them in a separate voice fragment before the concrete question. "
    "For beginners, use their concrete example and explain one idea per short "
    "paragraph. When correcting a misconception, give the correction and one "
    "small example; omit tables, unrelated languages and a new quiz unless asked. "
    "Explain learning history in plain language; omit internal field names, "
    "confidence flags, and numeric tracker internals. Actual answer records take "
    "precedence over stale mastery labels when describing progress. "
    "Do not infer a different response mode from "
    "keywords or from knowledge-graph labels. "
    "When the learner's message refers to earlier work in the session - for "
    "example \"that example\", \"example 2\", \"the step before\", \"why is "
    "there a 1/2\" - resolve the reference from the Recent study context block "
    "and answer that specific item directly. Do not ask the learner to paste "
    "material that is already present in the Recent study context, and do not "
    "fall back to a generic textbook derivation when the referenced item is "
    "visible there. "
    "If the Recent study context shows that the current material is a "
    "different subject from an earlier one, answer only about the subject the "
    "learner is now asking about. "
    "Do not invent source material beyond the supplied text."
)

STUDY_CONCEPT_EXPLAIN_SYSTEM_PROMPT = (
    "You are a concise study tutor. Explain the concept clearly, "
    "identify prerequisite ideas, and give one short check question unless the "
    "learner or supplied Teaching constraints requests no question. Explicit "
    "sentence or length limits apply to the whole reply and take priority over "
    "the default structure, examples and check question. "
    "If the study text is an exercise or exam problem, solve it rather than "
    "only explaining the wording: analyze the problem type and target, extract "
    "the givens, show the key derivation or construction, verify the result, "
    "state the final answer or option, and include one concise transfer "
    "practice idea. "
    "For choice questions, do not assume it is single-select unless the "
    "problem explicitly says so; verify every option independently and output "
    "all correct option letters in the final answer. "
    "The solution process must include actual computations, derivations, or "
    "decision steps; do not replace it with a brief analysis label. "
    "Do not invent source material beyond the supplied text."
)

STUDY_MODE_SYSTEM_GUIDANCE = {
    "companion": "Keep the reply short, warm, and helpful.",
    "interactive": "Use a discussion style, ask one short follow-up question if it helps.",
    "teaching": "Teach step by step with slightly more structure; add a short check question only when the learner's request and Teaching constraints allow it. Honor explicit sentence limits for the whole reply.",
}

STUDY_CONCEPT_EXPLAIN_EXAMPLE = {
    "reply": "The idea is the slope of a line at one point, so you track the instantaneous change rather than the average change.",
}

STUDY_QUESTION_GENERATE_EXAMPLE = {
    "question": "What is the key relationship described in the source text?",
    "answer": "The answer should restate the core rule or concept from the source text.",
    "reference_answer": "The answer should restate the core rule or concept from the source text.",
    "accepted_answers": ["A concise restatement of the core rule"],
    "key_points": ["core rule", "relationship"],
    "rubric": {"core rule": 70, "clear wording": 30},
    "solution_steps": ["Identify the repeated rule", "Restate the relationship"],
    "question_type": "short_answer",
    "math_equivalence_engine": {"enabled": False},
    "hint": "Look for the main definition or rule that appears most often in the source.",
    "difficulty": 2,
    "topic": "core concept",
}

STUDY_ANSWER_EVALUATE_EXAMPLE = {
    "verdict": "partial",
    "score": 68,
    "error_type": "incomplete",
    "feedback": "You identified the main idea, but one important step is missing.",
    "next_action": "Ask the learner to restate the missing step in one sentence.",
    "final_answer_correct": False,
    "covered_points": ["main idea"],
    "missing_points": ["missing step"],
    "misconceptions": [],
    "step_feedback": ["The first step is correct; add the missing relation."],
    "reference_answer": "A complete answer includes the main idea and the missing relation.",
    "related_topics": ["core concept"],
    "math_equivalence_engine": {"enabled": False},
}

STUDY_KNOWLEDGE_TRACK_EXAMPLE = {
    "topic": "core concept",
    "mastery_delta": 0.08,
    "confidence": 0.61,
    "weak_points": ["missing step"],
    "next_steps": ["restate the definition", "do one more recall attempt"],
    "session_summary_seed": {
        "event_count": 3,
        "last_operation": "answer_evaluate",
    },
}

STUDY_SUMMARIZE_SESSION_EXAMPLE = {
    "summary": "The session focused on one core concept and used a short answer check to confirm understanding.",
    "highlights": ["The learner explained the definition correctly."],
    "weak_points": ["One step still needs practice."],
    "next_actions": ["Review the missing step", "Try one new recall question"],
    "markdown": "## Summary\n\n- The session focused on one core concept.",
}

STUDY_QUESTION_GENERATE_SYSTEM_PROMPT = (
    "You are a study question generator. "
    "Create one concise question from the supplied context. "
    "Return exactly one valid JSON object."
)

STUDY_QUESTION_GENERATE_REQUIREMENTS = (
    "Task: Generate a study question.\n"
    "Requirements:\n"
    "1. question: one clear question grounded in the source text.\n"
    "Honor the learner's explicit question format, scope, number of choices and "
    "length in the source text. A request to ask only about direction must not also "
    "require listing nodes or explaining the entire path. Do not answer the question "
    "in its stem or hint. These instructions apply only to this question.\n"
    "2. answer: the compact reference answer.\n"
    "3. reference_answer: same meaning as answer, suitable to reveal only after evaluation.\n"
    "4. accepted_answers: short equivalent answers, if any.\n"
    "5. key_points: concise scoring points, not a full solution.\n"
    "6. rubric: small object mapping scoring point names to weights.\n"
    "7. solution_steps: concise solution/check steps.\n"
    "8. question_type: short_answer / math_exact / math_reasoning / multiple_choice.\n"
    "For multiple_choice, question MUST contain the full stem and every labelled "
    "option (A, B, C, D for a four-option request) in that same string; there is no "
    "separate options field in this output structure. State single or multiple "
    "selection explicitly. Verify each option independently. Keep the correct "
    "letter and its meaning only in answer/reference_answer and accepted_answers, "
    "never reveal them in question or hint. A stem without options is incomplete.\n"
    "9. hint: one direction-only hint; do not include the final answer or full solution.\n"
    "10. difficulty: integer from 1 to 5.\n"
    "11. topic: a short label for the target concept.\n"
    "12. math_equivalence_engine.enabled must be false.\n"
    "13. Subject grounding, in this priority order: (a) when context.selected_topic_name "
    "or context.selected_topic_id is present, that adaptive practice topic is the "
    "target; (b) otherwise, when context.material_grounded_question is true, the "
    "subject taught by the supplied study material (context.source_text / context.text, "
    "refined by context.topic_hint) is the target.\n"
    "14. context.knowledge_question_params, context.knowledge_guidance, context.history "
    "and context.last_ocr_text may inform difficulty, phrasing and distractor choice, "
    "but they must never move the question off the subject chosen in rule 13. When "
    "rule 13 names a topic, do not take the subject from the recent conversation or "
    "from the last captured material.\n"
    "15. Output must match this JSON structure:\n"
)

STUDY_ANSWER_EVALUATE_SYSTEM_PROMPT = (
    "You are a conservative study answer evaluator. "
    "Judge only what the context supports. Return exactly one valid JSON object."
)

STUDY_ANSWER_EVALUATE_REQUIREMENTS = (
    "Task: Evaluate the learner's answer.\n"
    "Requirements:\n"
    "1. verdict must be one of: correct / partial / wrong / dont_know.\n"
    "2. score must be an integer from 0 to 100.\n"
    "3. error_type should be a short label such as: none / missing_step / misconception / vague / incomplete / unsupported.\n"
    "4. feedback should be short, direct, and actionable.\n"
    "4a. Distinguish an explicit contradiction from an omitted detail. If the answer "
    "states the opposite of a supported relation, name that mistake and give the "
    "supported correction; do not describe it merely as missing names or steps. "
    "For spatial direction, use only supplied diagram/question evidence, not the "
    "order in which identifiers are written. Do not infer return flow from a call arrow.\n"
    "5. next_action should state the next teaching step.\n"
    "6. final_answer_correct should be true only when the final answer is correct.\n"
    "7. covered_points and missing_points should summarize rubric coverage.\n"
    "7a. A point listed in missing_points is a required rubric point: if any are missing, verdict must be partial or wrong and score cannot be 100. Put optional presentation suggestions only in feedback or step_feedback.\n"
    "7b. For a wholly incorrect core explanation, do not award points unless covered_points names a correct, rubric-relevant fact.\n"
    "8. step_feedback should summarize reasoning or math steps when applicable.\n"
    "9. reference_answer may be returned after evaluation.\n"
    "10. math_equivalence_engine.enabled must be false; do not claim symbolic equivalence verification.\n"
    "11. Use expected_answer and current question as the reference, but do not invent facts.\n"
    "12. Output must match this JSON structure:\n"
)

STUDY_KNOWLEDGE_TRACK_SYSTEM_PROMPT = (
    "You are a lightweight study tracking backend. "
    "Update the learner's trajectory from the supplied context. Return exactly one valid JSON object."
)

STUDY_KNOWLEDGE_TRACK_REQUIREMENTS = (
    "Task: Update lightweight knowledge tracking.\n"
    "Requirements:\n"
    "1. topic should be a short label.\n"
    "2. mastery_delta should be a number from -1.0 to 1.0.\n"
    "3. confidence should be a number from 0.0 to 1.0.\n"
    "4. weak_points should be a short array of strings.\n"
    "5. next_steps should be a short array of strings.\n"
    "6. session_summary_seed should remain compact and conservative.\n"
    "7. Output must match this JSON structure:\n"
)

STUDY_SUMMARIZE_SESSION_SYSTEM_PROMPT = (
    "You are a study session summarizer. "
    "Write a concise study summary from the supplied context. Return exactly one valid JSON object."
)

STUDY_SUMMARIZE_SESSION_REQUIREMENTS = (
    "Task: Summarize the session.\n"
    "Requirements:\n"
    "1. summary: 1-4 short sentences.\n"
    "1a. Default to two short spoken sentences: the evidenced subject and latest "
    "mistake/progress, then one concrete next action. Put that action in summary "
    "itself as well as next_actions; the role reads summary aloud. Follow an explicit "
    "learner length request. Do not claim an action has already been completed.\n"
    "2. highlights: short bullet-like strings that capture the learner's progress.\n"
    "3. weak_points: short bullet-like strings that identify gaps.\n"
    "4. next_actions: short bullet-like strings that suggest what to do next.\n"
    "5. markdown: a compact Markdown summary suitable for display.\n"
    "6. Use only the supplied context and keep the summary conservative.\n"
    "7. Ground the summary in what was actually studied. When context.session_history "
    "is present it lists exactly the interactions of the current session: summarise "
    "those as current-session activity. context.previous_course_history, when supplied, "
    "contains separate earlier records of this same course. context.previous_answer_records "
    "contains bounded graded answers from earlier sessions of the same course, even "
    "when later tutor messages have displaced those answers from the history window. "
    "These are prior learner answers and tutor evaluations, not new-session activity. "
    "If the learner asks about "
    "an earlier round or the current session has no learning interactions, use those "
    "records for continuity and explicitly call them previous/earlier activity; never "
    "claim they happened in this new session. Otherwise use them only to understand "
    "continuity, not to invent additional current-session progress. Do not ask the "
    "learner to supply a previous question or answer that either field already contains. "
    "Use context.last_ocr_text for the material that was on screen and "
    "context.session_summary_seed for counts. Treat context.screen_classification as "
    "weak metadata and never let it define the study subject.\n"
    "7a. Interaction kinds identify who did what. question_generate contains material "
    "or an instruction and a tutor-generated question, not a learner explanation or "
    "a correct answer. answer_evaluate contains the actual learner answer and its "
    "grade. concept_explain is a tutor explanation. A request to explain, review or "
    "practice is not evidence the learner completed that action. Report progress only "
    "from actual answers/corrections and their evaluation. A previous tutor summary "
    "is not independent evidence of learner mastery; prefer actual answer/evaluation "
    "records over inconsistent summary prose.\n"
    "8. Name the subject and the specific material or mistakes only when they appear "
    "in the session interactions or material. If the session covered two different "
    "subjects, mention both instead of picking one when summarizing the whole session. "
    "For an explicit focus on a previous question or mistake, prioritize relevant "
    "actual answers/evaluations and their next action; omit unrelated tutor lessons.\n"
    "9. Output must match this JSON structure:\n"
)

STUDY_STRUCTURED_USER_TEMPLATE = "{requirements}{example_json}\n\ncontext:\n{context_json}"
STUDY_STRUCTURED_MODE_PREFIX_TEMPLATE = "Mode: {mode}\n\n{prompt}"
# The structured operations only carried the language inside context_json, so the
# model wrote session summaries in English while the learner's language was zh-CN.
STUDY_STRUCTURED_LANGUAGE_TEMPLATE = "Write every natural-language field in {language}.\n\n{prompt}"

STUDY_CONCEPT_EXPLAIN_SYSTEM_WITH_MODE_TEMPLATE = "{system_prompt}\nMode guidance: {mode_guidance}"
STUDY_CONCEPT_RESPONSE_MODE_GUIDANCE = {
    "problem_solving": (
        "For a full solution with no explicit brevity or correction request, "
        "solve the concrete problem and output exactly four sections, each heading "
        "appearing exactly once and in this fixed order: Problem Analysis, Solution "
        "Process, Answer, Transfer Practice. For Chinese output, use exactly 题目解析, "
        "解题过程, 答案, 举一反三 in that order. Do not write a preface, a fifth "
        "heading, or any trailing note after Transfer Practice. In Problem Analysis, "
        "list only the givens, target, and core rule without repeating the problem. In "
        "Solution Process, present only the verified key derivation, numbered by "
        "sub-question, with the necessary formulas or theorem basis, key substitutions "
        "and transformations, applicable units, boundary checks, or verification. Any "
        "supplementary derivation must appear as numbered body content inside Solution "
        "Process and must not introduce another heading. Do not expose drafts, "
        "abandoned attempts, self-correction, reconsideration, or internal dialogue. "
        "Make Answer self-contained and cover every sub-question. Give exactly one "
        "short variant in Transfer Practice and keep it as the final section. If image "
        "information is insufficient, identify the missing information in Answer; "
        "never guess geometry or labels or repeatedly hypothesize about the figure. "
        "Keep secondary detail out of Solution Process when it "
        "could prevent a complete Answer or Transfer Practice; reserve output budget "
        "for both. For choice or option-judgement questions, "
        "verify every option independently and include all correct options in Answer."
    ),
    "general_explanation": (
        "Explain the core meaning, mechanism, relevant background, examples, and "
        "important boundaries naturally. Do not use solution headings or present "
        "the response as an exam answer."
    ),
    "general_discussion": (
        "Discuss the supplied object or viewpoint naturally. Separate supported "
        "facts, common interpretations, and evaluation; use relevant themes, people, "
        "narrative choices, effects, and personal understanding when appropriate. "
        "Do not use solution headings or present a standard exam answer."
    ),
    "unknown": (
        "Respond naturally and conservatively. Do not assume the request is a problem, "
        "and do not use solution headings unless the backend explicitly classifies it "
        "as problem_solving."
    ),
}
STUDY_CONCEPT_RESPONSE_MODE_USER_TEMPLATE = (
    "Language: {language}\n"
    "Source: {source}\n"
    "Mode: {mode}\n"
    "Task: concept_explain\n"
    "Response mode: {response_mode}\n"
    "Content type: {content_type}\n"
    "Intent: {intent}\n"
    "Response contract: {response_guidance}\n\n"
    "Study text:\n{text}{recent_context}"
)

# Backward-compatible public template for callers that still render this constant
# directly. Runtime concept explanations use STUDY_CONCEPT_RESPONSE_MODE_USER_TEMPLATE.
STUDY_CONCEPT_EXPLAIN_USER_TEMPLATE = (
    "Language: {language}\n"
    "Source: {source}\n"
    "Mode: {mode}\n"
    "Task: concept_explain\n\n"
    "When this is a problem, include a visible solution process before the "
    "final answer. Do not stop at a problem summary.\n"
    "For exercise or exam problems, use explicit sections for problem "
    "analysis, solution process, final answer, and transfer practice. If "
    "Language starts with zh, include the headings \"题目解析\", \"解题过程\", "
    "\"答案\", and \"举一反三\". Do not provide only \"解析\" without "
    "step-by-step work or transfer guidance.\n"
    "For choice or option-judgement questions, verify every option independently. "
    "Do not stop after finding one correct option, and do not assume it is "
    "single-select unless the problem explicitly says so. If multiple options "
    "are correct, output all correct option letters. 如果是选择题或逐项判断题，"
    "不要默认是单选题；必须逐项验证，不要找到一个正确选项就停止；若有多个正确选项，"
    "在“答案”中输出全部正确选项。\n\n"
    "Study text:\n{text}"
)

STUDY_JSON_CORRECTION_USER_TEMPLATE = (
    "JSON correction request {attempt}/{max_attempts}, operation={operation}.\n"
    "Parse error: {parse_error}\n"
    "Your last response was not a valid JSON object. "
    "Reply with ONLY one valid JSON object and no markdown."
)

STUDY_EMPTY_INPUT_DEFAULT = "Please provide text or capture a readable screen first."

# The learner's session on 2026-10-12 ran out of request budget at 11:39:43 and kept answering.
# What came out was this text - English, quietly asserting it was an "Explanation", followed by a
# "Check question" that looked like a quiz but was generated by nobody. A degraded answer is fine;
# a degraded answer that does not say so is not, because the learner cannot tell the two apart.
STUDY_FALLBACK_EXPLANATION_DEFAULT = (
    "⚠️ 这一段不是模型生成的讲解：模型没有回应（本轮请求额度已用完，或网络不可达）。\n"
    "This is not model-generated teaching - the model could not be reached (this round's request "
    "budget is spent, or the network is unreachable).\n\n"
    "原文首行 Key text: {first_line}\n\n"
    "本地只能复述你给的文字，不能解释它。Local fallback can restate the text you provided; it "
    "cannot explain it. 先确认额度（benchmarks/raw/neko-desktop-egress-cap）或网络，再重新问一次。"
)

STUDY_FALLBACK_QUESTION_EMPTY = {
    "question": "",
    "answer": "",
    "hint": STUDY_EMPTY_INPUT_DEFAULT,
    "difficulty": 1,
    "topic": "general",
}

STUDY_FALLBACK_QUESTION_TEMPLATE = {
    "question": ("现在出不了题：模型不可达（本轮请求额度已用完，或网络不可达）。"
                 "要我先用文字复述你问的概念，还是等你确认额度后再出题？"
                 " No question was generated, because the model is unreachable."),
    "answer": "",
    "hint": ("没有模型参与时不应凭空出题。"
             "A local fallback must not invent a question and present it as teaching."),
    "difficulty": 0,
    "topic": "model_unreachable",
}

STUDY_FALLBACK_FEEDBACK = {
    "correct": "本地兜底：这个回答与原文的核心说法一致（未经模型判定）。",
    "partial": "本地兜底：方向对，但还差一步精确（未经模型判定）。",
    "dont_know": "本地兜底：先从原文的主定义或规则起步（未经模型判定）。",
    "wrong": "本地兜底：这个回答与原文的核心说法不一致（未经模型判定）。",
}

STUDY_FALLBACK_NEXT_ACTION = {
    "correct": "Move to a slightly harder follow-up question.",
    "partial": "Ask for the missing step and then recheck the answer.",
    "dont_know": "Give a hint before asking the learner to try again.",
    "wrong": "Explain the misconception, then ask a simpler recall question.",
}

STUDY_FALLBACK_TRACK_NEXT_STEPS_WITH_WEAK_POINTS = ["Review the latest feedback"]
STUDY_FALLBACK_TRACK_NEXT_STEPS_DEFAULT = ["Continue with one more practice question"]

STUDY_FALLBACK_SUMMARY_EMPTY = "No study interactions have been recorded yet."
STUDY_FALLBACK_SUMMARY_DEFAULT = "This session includes recent study interactions and tutor feedback."
STUDY_FALLBACK_SUMMARY_NEXT_ACTIONS = ["Review the latest feedback", "Try one recall question"]

STUDY_MARKDOWN_SECTION_EMPTY_ITEM = "None recorded."
