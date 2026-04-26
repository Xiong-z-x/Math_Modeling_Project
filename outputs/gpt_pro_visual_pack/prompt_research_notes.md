# GPT Pro 生图提示词检索摘要

## 检索结论

本次提示词采用以下原则：

1. 把指令放在开头，并用清晰分隔符区分项目背景、数据文件、生成任务和自检规则。
2. 对图像任务显式给出用途、构图、视觉层级、配色、中文文字、输出比例和禁区。
3. 对含文字的信息图，要求逐字准确、短标签优先、生成后自检；复杂中文长句不直接塞进图面。
4. 对项目数据图，先读文件再生成；通过排序、分面、标准化、透明度、分位数突出等方法改善视觉质量，不改变真实数值。
5. 对多图工作流，采用“一张图一次生成 + 生成后自检 + 不合格重画”的迭代方式，避免一次性批量生成造成事实漂移。

## 参考来源

- OpenAI Help Center, Best practices for prompt engineering with the OpenAI API  
  https://help.openai.com/en/articles/6654000-best-practices-for-prompt-engineering-with-the-openai-api

- OpenAI Cookbook, Gpt-image-1.5 Prompting Guide  
  https://cookbook.openai.com/examples/multimodal/image-gen-1.5-prompting_guide

- OpenAI API Docs, Image generation  
  https://platform.openai.com/docs/guides/images

- ZeroLu/awesome-gpt-image, curated GPT Image prompt examples  
  https://github.com/ZeroLu/awesome-gpt-image/

- ImgEdify/Awesome-GPT4o-Image-Prompts, prompt dictionary  
  https://github.com/ImgEdify/Awesome-GPT4o-Image-Prompts

## 技能检索记录

按用户要求使用 `find-skills` 工作流，并执行：

```powershell
npx skills find "image prompt engineering"
```

检索结果中与提示词工程相关的技能包括：

- `davila7/claude-code-templates@prompt-engineer`，689 installs
- `alirezarezvani/claude-skills@senior-prompt-engineer`，245 installs
- `oakoss/agent-skills@prompt-engineering`，32 installs

这些技能安装量均不高于大型官方技能，因此本次没有新增安装，而是直接结合官方 OpenAI 文档、公开 GitHub 提示词仓库和本项目图表数据包编写专用总控提示词。
