# P3 发布字节校验补充

发布复核发现 study_code_teaching.py 在 Windows 工作树的 CRLF 字节被 Git 规范化为 LF，而 manifest 仍固定 CRLF 的 SHA，导致该文件在已发布树中不匹配。

已按原部署流程备份，将源码及部署副本统一为 LF，更新 manifest；没有逻辑变化。三方32/32复核通过，并为后续发布加入 staged blob 对 manifest 全部条目的 SHA 检查，避免只核对工作树字节而漏掉 Git 换行规范化。修正采用追加提交，不改写已发布历史。
