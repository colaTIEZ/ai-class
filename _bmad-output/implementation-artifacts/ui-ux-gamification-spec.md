# UI/UX Aesthetic Specification (Glassmorphism 多层磨砂玻璃美学规范)

Status: approved

## 1. Overview
本规范作为跨模块的 UI/UX 参考标准，旨在将 AI-Class 的视觉从 Notion 极简风升级为**「现代 Glassmorphism 多层磨砂玻璃 SaaS Dashboard」**美学。
整体设计理念：**专业、数据驱动、层次分明、高对比度可读性**。

核心目标：
- 通过多层磨砂玻璃面板营造**深度和清晰度**
- 使用高对比度排版确保**数据可读性**
- 限制模糊效果层数以保障**渲染性能**
- 专业 SaaS Dashboard 风格，去除 "AI 感"

---

## 2. 设计令牌体系 (Design Tokens)

### 2.1 核心 CSS 自定义属性

```css
:root {
  /* 背景渐变 */
  --bg-gradient-start: #F0F2F8;
  --bg-gradient-end: #E4E9F2;

  /* 毛玻璃面板 */
  --glass-bg: rgba(255, 255, 255, 0.35);
  --glass-bg-deep: rgba(255, 255, 255, 0.55);
  --glass-bg-card: rgba(255, 255, 255, 0.45);
  --glass-border: rgba(255, 255, 255, 0.18);
  --glass-border-strong: rgba(255, 255, 255, 0.30);
  --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.06);
  --glass-blur: 15px;
  --glass-blur-sm: 8px;

  /* 主色调 — 深海军蓝/紫色 */
  --accent-primary: #4338CA;
  --accent-primary-hover: #3730A3;
  --accent-primary-light: rgba(67, 56, 202, 0.08);

  /* 文字 */
  --text-on-glass: rgba(15, 23, 42, 0.85);
  --text-muted-on-glass: rgba(15, 23, 42, 0.55);
  --text-heading: #0F172A;
}
```

### 2.2 层次结构

| 层级 | 名称 | 描述 | 举例 |
|------|------|------|------|
| Layer 1 | 背景层 | 柔和渐变 + 低饱和 SVG 抽象图案 | `glass-background` |
| Layer 2 | 毛玻璃面板层 | 侧边栏、内容区主面板 | `sidebar-glass`, `glass-panel` |
| Layer 3 | 高对比度内容层 | 文字、数据展示、徽章 | `data-number`, `data-label` |
| Layer 4 | 直接操控层 | 按钮、交互控件 | `btn-primary`, `glass-btn` |

---

## 3. 可复用组件类 (Utility Classes)

| 类名 | 用途 | 关键属性 |
|------|------|---------|
| `.glass-panel` | 主面板容器 | `backdrop-filter: blur(15px)`, `bg: rgba(255,255,255,0.55)` |
| `.glass-card` | 子级卡片 | `backdrop-filter: blur(8px)`, `bg: rgba(255,255,255,0.45)` |
| `.glass-btn` | 次要操作按钮 | `backdrop-filter: blur(8px)`, `bg: rgba(255,255,255,0.50)` |
| `.glass-input` | 输入框 | `backdrop-filter: blur(8px)`, 焦点时 accent 边框 |
| `.btn-primary` | 主要操作按钮 | 实色 `--accent-primary`，带投影 |
| `.glass-badge` | 标签/徽章 | 半透明背景，圆角药丸形 |
| `.glass-card-success` | 成功语义卡片 | 绿色半透明玻璃 |
| `.glass-card-warning` | 警告语义卡片 | 琥珀色半透明背景 |
| `.glass-card-danger` | 危险语义卡片 | 红色半透明背景 |
| `.data-number` | 大号数据数字 | `2rem`, `font-weight: 800` |
| `.data-label` | 数据标签文字 | `0.6875rem`, 大写, 字间距 |

---

## 4. Module Specifications (各模块规范细节)

### 模块一：全局布局 (Global Layout)
- **背景**：`glass-background` — 柔和线性渐变 (`#F0F2F8` → `#E4E9F2`) + 低饱和径向渐变 SVG 抽象图案，带 30s 慢速漂移动画（`prefers-reduced-motion` 时禁用）
- **侧边栏**：`sidebar-glass` — 独立毛玻璃面板
  - `background: rgba(255, 255, 255, 0.30)`
  - `backdrop-filter: blur(15px)`
  - 超薄右边框：`1px solid rgba(255, 255, 255, 0.10)`
- **导航高亮**：激活项使用 `--accent-primary` 实色背景 + 左侧 `3px #818CF8` 明亮强调边框
- **非激活项**：`--text-muted-on-glass` 低饱和文字 + hover 时 `rgba(255,255,255,0.25)` 玻璃背景
- **"生成测验"按钮**：实色 `--accent-primary`，配 `0 4px 14px rgba(67,56,202,0.30)` 投影
- **图标**：统一使用 SVG 线条图标 (stroke-width: 1.8)，不使用 emoji

### 模块二：上传文档页 (Upload View)
- **上传卡片**：`glass-panel` + `glass-border-strong` 突出边框 + hover 抬升投影
- **Choose File 按钮**：磨砂半透明交互按钮，深色文字
- **"开始分析"按钮**：`btn-primary` 实色主色调
- **"返回知识库"按钮**：`glass-btn` 毛玻璃次要按钮
- **闪电图标**：现代线条 SVG (`stroke-width: 1.8`)

### 模块三：文档选择页 (Documents Entry View)
- **文档卡片网格**：3 列 grid，每张 `glass-card`
  - 微弱 `backdrop-blur: 8px`，极简 `rgba(255,255,255,0.18)` 边框
  - ID 数字弱化 (`.glass-badge`, `opacity: 0.6`)
  - hover 时提升 `box-shadow` 和 `border-color`
- **"上传新文档"按钮**：顶部 `glass-btn` + 加号 SVG
- **"查看详情"按钮**：卡片内 `glass-btn`
- **删除图标**：线条 SVG (`stroke-width: 1.8`)，hover 变 `text-red-500`

### 模块四：错题回顾页 (Review Page)
- **数据统计卡片**：`glass-panel` + `.data-number` 大号高对比度数字 + `.data-label` 标签
- **"显示全部"按钮**：`glass-panel` + `--accent-primary` 实色背景
- **掌握进度快照**：`glass-card-success` — 绿色半透明玻璃面板
  - 百分比数字使用 `.data-number` + `opacity: 0.7` 低饱和绿色
  - 子章节卡片使用 `glass-card` + `rgba(255,255,255,0.6)` 深层
- **错题分组**：`glass-card` 可折叠面板
  - 错误计数：琥珀色半透明圆形徽章
  - 答案对比：`glass-card-danger` (红) vs `glass-card-success` (绿)
  - "反馈 AI 错误" 按钮：`glass-btn` + 三角警告 SVG

### 模块五：苏格拉底专注测验界面 (Quiz View)
- **问答区域**：`glass-panel` 大型毛玻璃面板
- **选项**：`glass-card`，选中时 `--accent-primary-light` 背景 + accent 边框
- **输入框**：`glass-input`，焦点时 accent 光环
- **苏格拉底提示面板**：蓝色半透明玻璃
  - `background: rgba(219, 234, 254, 0.55)`
  - `backdrop-filter: blur(12px)`
  - 蓝色边框：`1px solid rgba(147, 197, 253, 0.3)`
- **提交按钮**：`btn-primary`
- **次要按钮**：`glass-btn`

### 模块六：文档详情页 (Document View)
- **操作按钮**：`glass-btn` (上传新文档) + `btn-primary` (开始测验)
- **加载/错误/空态**：统一使用 `glass-panel` / `glass-card-danger`
- **知识图谱区域**：保持全宽，图谱组件自身处理内部渲染

### 模块七：教与学文案克制 (De-wizarding Copywriting)
- 放弃一切与"魔法/游戏/怪物"相关的用词。
- **重命名规范**：
  - "解读卷轴" / "魔法卷轴" 统一修改为 "上传文档" / "文档材料"。
  - "知识领地" / "点亮区块" 统一修改为 "知识库" / "构建知识图谱"。
  - "小怪兽图鉴" / "召唤测验" 统一修改为 "错题回顾" / "生成/开始测验"。

---

## 5. 性能优化约束

| 约束 | 实现 |
|------|------|
| 最大 blur 层数 | 2 层（侧边栏 + 内容面板），子卡片用 `blur-sm` 仅 8px |
| 背景方案 | CSS 线性渐变 + 内联径向渐变 SVG 图案，禁止视频/大型图片 |
| 文字可读性 | 所有 blur 表面上文字最低 `rgba(0,0,0,0.80)`，确保 WCAG 4.5:1 |
| 动画节制 | 背景漂移 30s 超慢速；hover 过渡 150-300ms；`prefers-reduced-motion` 全禁用 |
| GPU 加速 | 动画仅使用 `transform` 和 `opacity` |

---

## 6. 图标规范

- **风格**：现代线条 (stroked)，统一 `stroke-width: 1.8`
- **尺寸**：导航图标 `18×18`，内容区图标 `16×16` 或 `24×24`
- **来源**：Heroicons Outline 风格 手写内联 SVG
- **禁止**：emoji 图标 (🎨 🚀 ⚙️ ✅ ❌ ⚠️ 📌)，统一替换为 SVG

---

## 7. 前端实现规范 (Frontend Implementation Stack)
- **CSS 设计系统**：`style.css` 中定义所有 CSS 自定义属性和可复用组件类
- **TailwindCSS**：用于布局 utility（flex, grid, spacing），颜色通过自定义属性引用
- **Transitions**：CSS transition 150-300ms，`prefers-reduced-motion` 时禁用动画
- **Responsive**：侧边栏在移动设备需隐藏进汉堡菜单（后续迭代）
- **字体**：`Inter` (400, 500, 600, 700, 800)，通过 Google Fonts CDN 加载
