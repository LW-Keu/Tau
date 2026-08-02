# PONYTAIL-DEBT

Ponytail 刻意简化的台账。每处保留已知上限的捷径在代码里就地标记:

    # ponytail: <ceiling>, <upgrade trigger>

其它语言用对应注释前缀(如 `// ponytail:`)。跑 `/ponytail:ponytail-debt`
会把全仓库的标记汇总回本表。

## 台账

_空 —— 还没有 `ponytail:` 标记。第一处出现后更新本表。_

每行格式:`<file>:<line>, <what was simplified>. ceiling: <limit>. upgrade: <trigger>.`
未命名升级触发条件的标 `no-trigger`(会静默腐烂,优先补触发条件或转直接修复)。
