# W-C：第二次验收说明

- 更新 `docs/claude-acceptance-guide.md`，说明新课程 ID、选择/返回课程、新开 Session 的区别、选择图片后还需点 Explain 提交。
- 明确 Study 提交图片决定角色看到的材料；“显示学习材料”窗口用于查看和指点，在那里换 HTML 不会换掉 Study 图像。
- 增加第一次真人验收的评分落库、重启泛问遗漏、18 秒延迟及麦克风输入环境问题；保留评分偏严、中文整句 explore 不可靠等边界。
- 操作标签核对当前 `static/index.html` 的 `studyCourseId`、`resumeCourseSessionBtn`、`startCourseSessionBtn`、`studyImageChoose`、`explainBtn`，以及 `main.js` 的课程和图片提交处理。此项是源码/文档核对，没有代用户操作日常课程，也没有宣称现场点击验收通过。
- 没有修改用户日常数据或生成验收课程；需要用户在最终验收前按说明自行选择材料。
