# UI/UX Gamification Specification (游戏化美化规范)

Status: pending

## 🎯 1. Overview
本规范作为跨模块的 UI/UX 参考标准，旨在对 AI-Class 目前**已有功能的组件**进行游戏化视觉与交互美化（仅限 UI/UX 层面提升，不涉及核心底层业务逻辑改变与增删）。

整体风格采用**「动森风果冻质感」+「轻赛博高光特效」**，主色调：
- 活力橙（#FF6B6B）
- 薄荷绿（#4ECDC4）
- 电玩紫（#9D4EDD）

## 🗺️ 2. Module Specifications (各模块美化细节)

### 模块一：PDF 解析变身「点亮天赋树」 (Epic 1 UI 补充)
- **趣味加载（Loading Phase）**：在文档分析调用阶段，摒弃枯燥进度条，替换为 Lottie 趣味动画（如“魔法炼金炉提炼”或“AI 挠头解析书本”）。
- **天赋树视觉优化（Knowledge Graph）**：
  - **已掌握节点**：高亮亮色，带霓虹光晕（`filter: drop-shadow`），SVG 连接线增加流光动画（`stroke-dashoffset`）。
  - **正在学习节点**：薄荷绿色，增加舒缓的心跳呼吸灯效（CSS Breathing Light 缓动）。
  - **未解锁节点**：采用战争迷雾 / 毛玻璃暗化效果（`backdrop-filter: blur(8px)`），通关前置节点后配合特效消散。
- **出击提示交互**：选中考点范围后，弹出带有阻尼弹跳动画（Spring/Jello bounce）的浮动气泡，气泡附带 Q 版提示文案（如：“前方发现 20 只知识小怪，预计掉落 500 经验值”）。

### 模块二：苏格拉底引擎化身「傲娇/暖心 NPC」 (Epic 2 UI 补充)
- **温柔试错（Safe-to-Fail）**：答错时放弃刺眼的红色叉号，改为蜜桃粉色，并在前端触发轻微的摇头（Head Shake）摇晃动效。
- **导师锦囊妙计（Floating Mentor）**：页面侧边的苏格拉底求助组件设计成伴飞的“小机甲/图腾球”。答题耗时过长（> 30s）触发空翻动效主动吸引视线。点击展开后，使用弹簧物理动效（Spring Physics）展开为对话框。
- **爽感连击反馈（Dopamine Combo）**：答对题目瞬间在前端坐标处增加五彩礼花粒子爆破动效。连续答对 3 题，触发屏幕侧边弹出的 `COMBO x 3!! 智力狂飙` 夸张字效提示框（附带音频或视觉速度线）。

### 模块三：错题集变身「小怪兽图鉴」 (Epic 3 UI 补充)
- **进度可视化（Evolution Stats）**：将知识点掌握情况从常规图表替换为赛博风格的“六边形战士雷达图”或“电子养成植物”，随掌握度加深呈现华丽特效。
- **卡片 3D 偏转（Trading Cards）**：错题列表包装为“怪物图鉴卡片”瀑布流设计。鼠标悬停触发灵敏的 3D 物理偏转反光（`useMouseInElement` + `rotateX/Y`）。
- **Boss 战动效**：“开启今日复习”按钮采用流速渐变与脉冲光圈（Pulse Glow），点击时拦截普通跳转，先播放类似玻璃碎裂或急速拉伸（Zoom-in）的 3D 转场动画，再渲染 Quiz 界面。

## 🎨 3. 空状态设计 (Empty States)
- 没有任何错题时，展示空笼子与熟睡的 NPC 插画，文案：“小怪兽均已消灭！无敌是多么寂寞，去睡个好觉吧 Zzz...”。
- 未上传 PDF 时，展示荒芜沙漠，文案：“领地还是一片荒芜，快去解析一份魔法卷轴（PDF），播下你知识的第一颗种子吧！”

## 💻 4. Frontend Edge Toolkit (前端落地推荐)
为了确保不带来沉重的业务重构，这些美化严格依赖前端表现层库完成：
- **SVG / TailwindCSS**：完成呼吸灯、毛玻璃、天赋树发光流线（`stroke-dasharray`）。
- **vue3-lottie**：处理复杂的角色插画互动（吃书、图鉴怪兽）。
- **GSAP (GreenSock)**：处理组件转场、Boss战碎屏、对话框物理缓冲。
- **@vueuse/core**：使用 `useMouseInElement` 实现 3D 卡牌特效。
- **canvas-confetti**：一行代码实现多巴胺撒花。
