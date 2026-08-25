# 20260825 日报 TMWebDriver 引擎 - 调试记录
## 根因链(已全部修复)
1. d.goto 不存在 → jump() (location.href)
2. CARD_JS 等是未调用箭头函数, remote 桥 eval 不自动调用 → 序列化 None → 全部改 IIFE
3. gnews: fetch_google_news 定义在 if __name__ 守卫(L551)之前? 实为 run 时 NameError(fail-soft), 本次用 --no-google-news 绕开
## 环境
- daemon: streamlit 内嵌 18765(WS)+18766(HTTP); 会话: HTTP /link get_all_sessions; d.sessions property 在 remote 下为空(坑)
- set_session('www.bing.com') 按 URL 子串钉会话; 工作 tab 351892547
- Bing News 卡片: div.news-card + data-url/data-title 属性健在
