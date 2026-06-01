# 运行方法

首先请确保你已经安装了 uv，如果没有的话，请按以下页面的要求安装：

https://docs.astral.sh/uv/guides/install-python/

然后在当前目录下，新建一个叫做 .env 的文件，输入以下内容：

```
OPENROUTER_API_KEY=xxx
```

xxx 就是你在 OpenRouter 上配好的 API Key。如果你不用 OpenRouter，那直接改下代码，换个别的 baseUrl 就行了。

确保 uv 已经安装成功后，进入到当前文件所在目录，然后执行以下命令即可启动：

```bash
uv run agent.py snake
```


## 📝 專案說明 (About This Project)

這是一個用於學習與練習的專案 (Practice Repository)。
主要是跟著 [Agent 的概念、原理與構建模式 —— 從零打造一個簡化版的 Claude Code] 的教學步驟，親手實作並測試相關功能。

**📚 學習來源 (Credits & Resources)：**
* 原始教學 / 檔案提供者：[馬克的技術工作坊]
* 教學連結：[https://www.youtube.com/watch?v=GE0pFiFJTKo]

**💡 我在這個練習中學到了什麼？**
* ReAct 架構實作：理解並實作出大語言模型「推理 (Reasoning) 與行動 (Acting)」交錯運作的開發模式。
* LLM 引擎無縫遷移：基於成本考量，重寫 API 呼叫邏輯，將需付費的 OpenAI 成功重構並替換為 Google Gemini 模型。