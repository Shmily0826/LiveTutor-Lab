# P7：全新课程的一键准备

新增scripts/neko_prepare_acceptance_course.py：只接受尚不存在的neko-acceptance-*任务目录，拒绝日常库、已有目录、路径逃逸；不复制学习库，仅沿用已有只读源码授权。提交固定Sky Scout PNG、设置课程和中文简短偏好，核对Study当前图片与保存像素SHA。独立启动器副本重定向原日志、设置用户给出的累计停止线，原账本轮次与全局上限保持不变。全程text-only、无采集/回环，结束后清理自己拥有的进程。

两个离线边界测试通过：拒绝日常/已有/逃逸路径并保留标记文件；验证新名称本身不创建目录。实际脚本在新库neko-acceptance-r2-rehearsal创建课程sky-scout-r2-acceptance-20261016，真实Study提交与讲解成功。源PNG与SQLite保存图片SHA均为858cfcc0…；study_material确认当前课程有图。这是Study图片路径证据，不是Native直接看屏幕或真人验收。

账本1441/123→1443/123，新增DeepSeek2、Native连接0。完整输出在raw/evidence/neko-acceptance-r2-rehearsal-prepare.json。该新库继续用于P8全流程彩排，避免用日常课程或已有答案代替准备。用户在Study里新建课程、选择/粘贴图片并点击Explain的步骤见验收说明。
