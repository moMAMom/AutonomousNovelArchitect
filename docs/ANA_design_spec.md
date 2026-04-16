# Autonomous Novel Architect (ANA) — 詳細設計書

**バージョン:** 1.0  
**対象モデル:** Qwen 3.5 9B on LM Studio 0.4.11  
**実行環境:** Python 3.12 / PyQt6 / Windows  
**生成規模:** 中編（2〜10万字、5〜15章）  
**作成日:** 2026-04-16

---

## 1. システム全体構成

```
d:\code\StoryMaker\
├── main.py                     # エントリポイント
├── config.yaml                 # 全設定（執筆開始後ロック項目あり）
├── core/
│   ├── orchestrator.py         # 状態機械 + ワークフロー制御
│   ├── agents.py               # 4ロールのプロンプトビルダー + 基底クラス
│   ├── bible.py                # ProjectBible CRUD + Guard上書きロジック
│   ├── context_manager.py      # トークン予算管理 + プロンプト組み立て
│   └── api_client.py           # LM Studio ラッパー（ストリーミング対応）
├── gui/
│   ├── main_window.py          # QMainWindow + レイアウト
│   ├── inception_dialog.py     # 新規プロジェクト ウィザード（3ページ）
│   ├── settings_dialog.py      # 設定画面（ロック制御付き）
│   ├── project_panel.py        # 左：プロジェクトツリー
│   ├── preview_panel.py        # 中：原稿プレビュー（ストリーミング）
│   └── log_panel.py            # 右：Bible Viewer + エージェントログ
├── prompts/
│   ├── writer_system.txt
│   ├── editor_system.txt
│   ├── proofreader_system.txt
│   └── guard_system.txt
└── output/
    └── {project_name}/
        ├── progress.json
        ├── project_bible.json
        ├── plot/
        │   ├── overall_plot.txt
        │   └── chapter_plans/
        │       └── ch{N:02d}_plan.txt
        └── manuscript/
            ├── ch{N:02d}_final.txt
            └── logs/
                ├── ch{N:02d}_drafts.jsonl
                └── guard_actions.jsonl
```

---

## 2. データスキーマ定義

### 2.1 `project_bible.json`

```json
{
  "meta": {
    "title": "string",
    "genre": "string",
    "created_at": "ISO8601",
    "version": 1
  },
  "world": {
    "geography": ["string"],
    "history": ["string"],
    "rules": ["string"],
    "atmosphere": "string"
  },
  "characters": [
    {
      "id": "char_001",
      "name": "string",
      "appearance": "string",
      "personality": "string",
      "motivation": "string",
      "secrets": ["string"],
      "relationships": {"char_id": "関係説明"},
      "tags": ["主人公"]
    }
  ],
  "plot": {
    "overall": {
      "premise": "string",
      "theme": "string",
      "ending_type": "string"
    },
    "beat_sheet": [
      {"act": 1, "beat": "発端", "description": "string"}
    ],
    "chapters": [
      {
        "id": 1,
        "title": "string",
        "goal": "string",
        "events": ["string"],
        "hook": "string",
        "status": "planned|drafting|final"
      }
    ]
  },
  "facts": [
    {
      "id": "fact_001",
      "content": "string",
      "chapter_introduced": 1,
      "tags": ["魔法", "主人公"],
      "category": "world|character|event",
      "superseded_by": null
    }
  ],
  "foreshadowing": [
    {
      "id": "fs_001",
      "planted_in_ch": 1,
      "payoff_in_ch": 5,
      "content": "string",
      "resolved": false
    }
  ]
}
```

### 2.2 `progress.json`

```json
{
  "phase": "inception|structuring|drafting|complete",
  "current_chapter": 3,
  "chapter_statuses": {
    "1": "final",
    "2": "final",
    "3": "critiquing"
  },
  "current_attempt": 2,
  "best_score_so_far": 74,
  "best_draft_index": 1,
  "locked": true
}
```

`locked: true` に遷移するのは `phase` が `drafting` に移行した瞬間。設定画面のロック制御はこのフラグを参照する。

### 2.3 `config.yaml`

```yaml
# --- 執筆開始後ロック ---
model_id: "qwen3-9b-instruct"
max_retry_count: 3
score_threshold: 80
sliding_window_chapters: 3
token_budgets:
  system_prompt: 500
  fixed_memory: 4000
  sliding_window: 20000
  summarized_memory: 3000
  direct_injection: 2000
  chapter_plan: 1000
  prev_draft: 8000
  editor_feedback: 500
  output_reserve: 15000
  safety_margin: 2536

# --- 執筆中も変更可 ---
chapter_approval_gate: false
lm_studio_url: "http://localhost:1234/v1"
request_timeout_sec: 800
connection_retry_count: 3
```

### 2.4 `ch{N}_drafts.jsonl`（1行1JSON）

```jsonl
{"attempt":1,"timestamp":"...","draft":"本文全文","score":72,"issues":["問題1","問題2"]}
{"attempt":2,"timestamp":"...","draft":"本文全文","score":85,"issues":[]}
```

---

## 3. エージェント仕様

### 3.1 ロール別 コンテキスト注入内容

| ロール | 注入する情報 |
|---|---|
| Writer | Bible（抜粋）+ 章プラン + [前ドラフト + 改善リスト（リトライ時）] |
| Editor | ドラフト本文 + 章プラン + スコアリング指示 |
| Proofreader | Editorパス済みドラフト + 文体ルール |
| Guard | 最終稿 + 現在の `facts` リスト |

### 3.2 Editor スコアリング出力フォーマット

`response_format` で JSON 出力を強制する：

```json
{
  "score": 78,
  "issues": [
    "主人公の動機が唐突。直前のシーンとの接続が弱い。",
    "会話文が3連続で描写がない。"
  ],
  "summary": "全体的な評価コメント"
}
```

### 3.3 Guard Bible更新フォーマット

```json
{
  "new_facts": [
    {"content":"...", "tags":["魔法"], "category":"world"}
  ],
  "conflicts": [
    {"existing_fact_id":"fact_001", "reason":"新しい描写と矛盾", "resolution":"上書き"}
  ]
}
```

矛盾検出時の処理：既存 fact の `superseded_by` に新 fact の id をセット → `guard_actions.jsonl` に記録 → AgentLogPanel に黄色警告表示。

---

## 4. ワークフロー状態機械

### 4.1 フェーズ遷移

```
[inception] → [structuring] → [drafting] → [complete]
```

`drafting` 遷移時に `progress.json` の `locked` を `true` にセット。

### 4.2 章内部サイクル（Recursive Drafting）

```
planned
  → drafting       Writer生成 (attempt=1)
  → critiquing     Editor評価
      ├── score >= threshold → refining
      └── score <  threshold かつ attempt < max_retry
              → drafting (attempt++)
      └── attempt == max_retry → ベストスコアドラフトをrefiningへ強制送出 + ログ警告
  → refining       Writer修正
  → polishing      Proofreader
      ├── approval_gate=false → archiving（自動）
      └── approval_gate=true  → [承認待ち] → archiving
                               → [修正指示入力] → refining（リトライとは別カウント）
  → archiving      Guard更新 + Bible自動上書き
  → final
```

### 4.3 再開ロジック

起動時に `progress.json` を読み込み、`final` でない最初の章から復元：

| 復元時のステータス | 処理 |
|---|---|
| `drafting` | ドラフトなし → Writerから再実行 |
| `critiquing` | `ch{N}_drafts.jsonl` の最終ドラフトを読み込み Editorへ |
| `refining` 以降 | ログから該当ドラフトを復元し、そのステップから再開 |

---

## 5. トークン予算管理

コンテキストウィンドウ上限: **65,536 トークン**  
入力上限（= 65536 - output_reserve 15000 - safety_margin 2536）: **48,000 トークン**

`context_manager.py` の `build_prompt()` が以下の順でブロックを積み、合計が 48,000 を超えた場合は `summarized_memory` を 50% 圧縮 → それでも超過なら `direct_injection` を削減：

| # | ブロック | 上限（トークン） | 備考 |
|---|---|---|---|
| 1 | system_prompt | 500 | 固定 |
| 2 | fixed_memory | 4,000 | 世界観核心 + 主人公 + 全章サマリー |
| 3 | direct_injection | 2,000 | Guard タグマッチで抽出した関連 facts |
| 4 | sliding_window | 20,000 | 直近 N 章の全文 |
| 5 | summarized_memory | 3,000 | それ以前の章要約（圧縮対象） |
| 6 | chapter_plan | 1,000 | 今書く章の設計書 |
| 7 | prev_draft | 8,000 | リトライ時のみ |
| 8 | editor_feedback | 500 | リトライ時のみ |

トークンカウント: `tiktoken` cl100k_base エンコーダを使用。

---

## 6. GUI 仕様

### 6.1 メインウィンドウ レイアウト

```
QMainWindow
├── MenuBar: [ファイル] [設定] [ヘルプ]
├── ToolBar: [新規] [開く] [▶実行] [■停止] [書き出し]
├── CentralWidget (QSplitter 水平)
│   ├── ProjectPanel     (QTreeWidget)               幅 20%
│   ├── PreviewPanel     (QTextEdit readonly)         幅 50%
│   └── RightSplitter    (QSplitter 垂直)             幅 30%
│         ├── BibleViewer (QTreeWidget + QTextEdit)
│         └── AgentLogPanel (QListWidget, 色分け)
└── StatusBar: [ロール表示] [スコアプログレスバー] [トークン残容量]
```

### 6.2 Inception ウィザード（`inception_dialog.py`）

`QWizard` 3ページ構成：

| Page | 入力フィールド |
|---|---|
| 1: 基本情報 | プロジェクト名, ジャンル（コンボ）, 雰囲気メモ |
| 2: 設定・キャラクター | 主人公イメージ, 世界観タグ（カンマ区切り）, 登場人物メモ |
| 3: プロット方向 | テーマ, 起承転結ヒント, 目標章数（スピンボックス 5〜20） |

「完了」→ `Orchestrator.start_inception()` 呼び出し → `project_bible.json` 生成 → BibleViewer で確認（この時点ではロックなし・手動編集可）。

### 6.3 設定ダイアログ（`settings_dialog.py`）

タブ構成：**生成 / 品質管理 / 接続**

`progress.json` の `locked == true` のとき、ロック対象ウィジェットに適用：

```python
widget.setEnabled(False)
widget.setToolTip("執筆開始後は変更できません。新規プロジェクトを作成してください。")
```

| 項目 | ロック |
|---|---|
| model_id, max_retry_count, score_threshold | ロック |
| sliding_window_chapters, token_budgets.* | ロック |
| chapter_approval_gate（チェックボックス） | 変更可 |
| lm_studio_url, request_timeout_sec | 変更可 |

### 6.4 ストリーミング表示

`api_client.py` が `stream=True` で受信 → `token_received` シグナル（`pyqtSignal(str)`）を emit → `PreviewPanel` スロットが `QTextEdit.insertPlainText()` で追記。Worker は `QThread` サブクラス。

### 6.5 AgentLog 色分け

| ロール | 色 |
|---|---|
| Writer | 青 |
| Editor | 橙 |
| Proofreader | 緑 |
| Guard | 紫 |
| システム警告 | 黄 |

---

## 7. エラーハンドリング

| エラー種別 | 対処 |
|---|---|
| LM Studio 接続失敗 | 指数バックオフ 3 回リトライ → GUI 通知 → 一時停止（ユーザー判断） |
| レスポンス JSON パース失敗 | 正規表現でスコア/issues 抽出を試みる → 失敗でリトライ 1 回消費 |
| トークン予算超過 | summarized_memory を 50% 圧縮 → それでも超過なら direct_injection を削減 |
| Guard 矛盾検出 | superseded_by セット + guard_actions.jsonl 記録 + AgentLog 黄色警告 |
| リトライ上限超過 | ベストスコアドラフトを強制採用 + ステータスバーに橙色警告 |

---

## 8. pyqtSignal 一覧

| シグナル名 | 型 | 発火タイミング |
|---|---|---|
| `token_received` | `str` | LLM ストリーミング 1 チャンク受信 |
| `phase_changed` | `str` | Orchestrator フェーズ遷移 |
| `score_updated` | `int` | Editor スコア確定 |
| `needs_approval` | `int` | 章完成・承認ゲート待ち |
| `error_occurred` | `str` | エラー発生 |
| `bible_updated` | - | Guard が Bible を更新 |
