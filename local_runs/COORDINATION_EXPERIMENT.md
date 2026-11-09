# DexMimicGen 双臂协同时序实验

## 0. 下载完整官方数据

下载脚本使用临时文件，并同时检查官方文件大小和 SHA-256；只有验证通过才会改名为正式数据集：

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\pyke\Desktop\上交\local_runs\download_two_arm_threading.ps1
```

## 实验问题

在保持单臂动作序列完整的条件下，仅改变左右臂相对时序，任务成功率是否下降？哪些阶段对双臂同步最敏感？

旧版“冻结窗口”会直接删除一段 delta 动作，使末端位姿和动作幅度同时变化，不能把失败唯一归因于协同。本流程采用 **suffix delay**：在指定阶段插入等待，之后完整执行被延迟手臂的剩余动作。

## 1. 检查数据

必须通过 ASCII 路径运行 MuJoCo，避免 Windows 中文路径导致 mesh 加载失败：

```powershell
cd C:\Users\pyke\dexmg_workspace\local_runs\dexmimicgen-src\dexmimicgen-main
C:\Users\pyke\dexmg_workspace\local_runs\.venv310\Scripts\python.exe C:\Users\pyke\dexmg_workspace\local_runs\coordination_pipeline.py --dataset C:\Users\pyke\dexmg_workspace\local_runs\datasets\generated\two_arm_threading.hdf5 --inspect-only --deep-verify
```

## 2. 小规模预实验

```powershell
C:\Users\pyke\dexmg_workspace\local_runs\.venv310\Scripts\python.exe C:\Users\pyke\dexmg_workspace\local_runs\coordination_pipeline.py `
  --dataset C:\Users\pyke\dexmg_workspace\local_runs\datasets\generated\two_arm_threading.hdf5 `
  --output C:\Users\pyke\dexmg_workspace\local_runs\results\threading_batch.jsonl `
  --max-demos 10 --arms left right --delays 2 4 6 10 --onsets 0 0.25 0.5 0.75 --settle-steps 20
```

程序每完成一个条件就追加一行 JSONL 并 `fsync`。命令中断后原样重跑会自动跳过已完成条件。

## 3. 汇总

```powershell
C:\Users\pyke\dexmg_workspace\local_runs\.venv310\Scripts\python.exe C:\Users\pyke\dexmg_workspace\local_runs\analyze_coordination_results.py `
  --input C:\Users\pyke\dexmg_workspace\local_runs\results\threading_batch.jsonl `
  --output-dir C:\Users\pyke\dexmg_workspace\local_runs\results\threading_batch_summary
```

优先报告 `success_after_settle`。`success_any` 只表示轨迹中曾短暂满足成功条件，不能代表物理稳定。

## 4. 渲染基线与干预对比

输出 GIF 的左侧是原始轨迹，右侧是同一示范的 suffix-delay 干预：

```powershell
C:\Users\pyke\dexmg_workspace\local_runs\.venv310\Scripts\python.exe C:\Users\pyke\dexmg_workspace\local_runs\render_coordination_comparison.py `
  --dataset C:\Users\pyke\dexmg_workspace\local_runs\datasets\generated\two_arm_threading.hdf5 `
  --demo demo_0 --arm left --delay 5 --onset 0.5 `
  --output C:\Users\pyke\dexmg_workspace\local_runs\results\demo0_left_delay5.gif
```

## 建议实验层级

1. 先用 10 条示范筛选延迟范围和敏感阶段。
2. 再固定 2–3 个最有区分度的延迟，在全部示范上验证。
3. 报告左右臂、阶段、延迟三个因素，并将 baseline 与干预结果按 demo 配对比较。
