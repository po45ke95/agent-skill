簡易 Python Agent Skill 範本

說明:
- agent_skill.py 提供一個簡易的任務註冊與執行框架。
- 使用範例:
  - CLI: python agent_skill.py run-task --task hello --args '{"name":"Peter"}'
  - 程式內: from agent_skill import task, run_task

擴充建議:
- 在任務中使用 type hints 與驗證 (pydantic)
- 加入日誌、儲存輸出、或外部 API 呼叫能力
