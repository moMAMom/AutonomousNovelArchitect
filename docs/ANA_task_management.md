# Autonomous Novel Architect (ANA) — タスク管理表

**作成日:** 2026-04-16  
**プロジェクトコード:** StoryMaker-ANA  
**目標規模:** 中編小説生成システム（2〜10万字対応）

---

## フェーズ構成

| フェーズ | 内容 | 依存 | 所要見積 |
|---|---|---|---|
| **F0** | 環境セットアップ | なし | 1日 |
| **F1** | コアデータ層 | F0 | 2日 |
| **F2** | APIクライアント層 | F0 | 2日 |
| **F3** | エージェント層 | F1, F2 | 3日 |
| **F4** | オーケストレーター | F1, F2, F3 | 4日 |
| **F5** | GUI基盤 | F0 | 2日 |
| **F6** | GUI各パネル | F4, F5 | 4日 |
| **F7** | 統合テスト | F4, F6 | 3日 |

**合計見積:** 21日（約4週間）

---

## F0: 環境セットアップ

| # | タスク | 詳細 | 優先 | 担当 | 状態 |
|---|---|---|---|---|---|
| F0-1 | 依存ライブラリ定義 | `requirements.txt`: `openai`, `PyQt6`, `tiktoken`, `PyYAML`, `pydantic` | 高 | | ⬜ |
| F0-2 | ディレクトリ構造作成 | `core/`, `gui/`, `prompts/`, `output/`, `docs/` | 高 | | ⬜ |
| F0-3 | `config.yaml` 初期版作成 | 全設定キーとデフォルト値の定義 | 高 | | ⬜ |
| F0-4 | LM Studio動作確認 | `curl http://localhost:1234/v1/models` で応答確認 | 高 | | ⬜ |

**成果物:**

- `requirements.txt`
- `config.yaml`
- ディレクトリ構造完成

---

## F1: コアデータ層

| # | タスク | 実装ファイル | 詳細 | 優先 | 担当 | 状態 |
|---|---|---|---|---|---|---|
| F1-1 | `ProjectBible` クラス | `core/bible.py` | JSON読み書き, `add_fact()`, `resolve_conflict()`, `get_facts_by_tags()` | 高 | | ⬜ |
| F1-2 | `ProgressTracker` クラス | `core/orchestrator.py` 内 | `progress.json` の読み書き, `lock()`, `get_resume_point()` | 高 | | ⬜ |
| F1-3 | `config.yaml` ローダー | `core/config.py` | `pydantic` で型バリデーション付きロード | 高 | | ⬜ |
| F1-4 | ドラフトログ管理 | `core/bible.py` 内 | `ch{N}_drafts.jsonl` への追記, ベストスコア取得 | 中 | | ⬜ |
| F1-5 | `output/` ディレクトリ初期化 | `core/bible.py` 内 | プロジェクト名から出力先生成, サブフォルダ作成 | 中 | | ⬜ |

**成果物:**

- `core/bible.py`（ProjectBible クラス）
- `core/config.py`（設定ローダー）
- `progress.json` スキーマ実装

**テスト項目:**

- [ ] Bible CRUD操作（追加・更新・削除・検索）
- [ ] conflict 検出と superseded_by 処理
- [ ] tags によるフィルタリング
- [ ] progress.json の保存・復元

---

## F2: APIクライアント層

| # | タスク | 実装ファイル | 詳細 | 優先 | 担当 | 状態 |
|---|---|---|---|---|---|---|
| F2-1 | `LMStudioClient` 基底 | `core/api_client.py` | `openai.OpenAI(base_url=..., api_key="lm-studio")` 初期化 | 高 | | ⬜ |
| F2-2 | 同期チャット呼び出し | `core/api_client.py` | タイムアウト設定, 指数バックオフリトライ3回 | 高 | | ⬜ |
| F2-3 | ストリーミング呼び出し | `core/api_client.py` | `stream=True`, チャンク単位でジェネレータ返却 | 高 | | ⬜ |
| F2-4 | JSON構造化レスポンス抽出 | `core/api_client.py` | `response_format` 対応 + 正規表現フォールバック | 高 | | ⬜ |
| F2-5 | 接続テスト関数 | `core/api_client.py` | `ping()` → `/v1/models` に疎通確認 | 中 | | ⬜ |

**成果物:**

- `core/api_client.py`（LMStudioClient クラス）

**テスト項目:**

- [ ] LM Studio への接続成功・失敗
- [ ] リトライ機能（接続失敗時の指数バックオフ）
- [ ] ストリーミングレスポンスの受信
- [ ] JSON パース成功・失敗時のフォールバック
- [ ] タイムアウト処理

---

## F3: エージェント層

| # | タスク | 実装ファイル | 詳細 | 優先 | 担当 | 状態 |
|---|---|---|---|---|---|---|
| F3-1 | `BaseAgent` クラス | `core/agents.py` | システムプロンプトファイル読込, `build_messages()` | 高 | | ⬜ |
| F3-2 | `WriterAgent` | `core/agents.py` | Bible抜粋 + 章プラン + [前ドラフト + 改善リスト] 注入 | 高 | | ⬜ |
| F3-3 | `EditorAgent` | `core/agents.py` | JSON出力指定（score, issues, summary）, パース | 高 | | ⬜ |
| F3-4 | `ProofreaderAgent` | `core/agents.py` | 文体ルール注入, 最終稿返却 | 高 | | ⬜ |
| F3-5 | `GuardAgent` | `core/agents.py` | new_facts / conflicts JSONパース → Bible更新呼び出し | 高 | | ⬜ |
| F3-6 | `ContextManager` | `core/context_manager.py` | トークン予算計算, プロンプトブロック組み立て, 圧縮ロジック | 高 | | ⬜ |
| F3-7 | `prompts/` ファイル本文 | `prompts/*.txt` | 各ロールのシステムプロンプト日本語文面 | 高 | | ⬜ |

**成果物:**

- `core/agents.py`（4エージェント + BaseAgent）
- `core/context_manager.py`（トークン予算管理）
- `prompts/writer_system.txt`
- `prompts/editor_system.txt`
- `prompts/proofreader_system.txt`
- `prompts/guard_system.txt`

**テスト項目:**

- [ ] 各エージェントのプロンプト生成
- [ ] Editor の JSON パース（score, issues）
- [ ] Guard の JSON パース（new_facts, conflicts）
- [ ] ContextManager のトークン予算計算
- [ ] 予算超過時の圧縮処理

---

## F4: オーケストレーター

| # | タスク | 実装ファイル | 詳細 | 優先 | 担当 | 状態 |
|---|---|---|---|---|---|---|
| F4-1 | `Orchestrator` 状態機械 | `core/orchestrator.py` | Phase遷移管理, `progress.json` 更新 | 高 | | ⬜ |
| F4-2 | Inceptionフロー | `core/orchestrator.py` | キーワード → Writer(Inception役) → Bible生成 | 高 | | ⬜ |
| F4-3 | Structuringフロー | `core/orchestrator.py` | Chapter Planning → Scene Breakdown | 高 | | ⬜ |
| F4-4 | Recursive Draftingサイクル | `core/orchestrator.py` | Drafting→Critiquing→Refining→Polishing→Archiving | 高 | | ⬜ |
| F4-5 | リトライ制御 | `core/orchestrator.py` | attempt管理, ベストスコア強制採用, ログ警告 | 高 | | ⬜ |
| F4-6 | 承認ゲート制御 | `core/orchestrator.py` | `approval_gate=true` 時にGUI承認待ちシグナル送出 | 中 | | ⬜ |
| F4-7 | 中断・再開ロジック | `core/orchestrator.py` | `get_resume_point()` からステータス復元 | 高 | | ⬜ |
| F4-8 | pyqtSignal 定義 | `core/orchestrator.py` | `token_received`, `phase_changed`, `score_updated`, `needs_approval`, `error_occurred`, `bible_updated` | 高 | | ⬜ |

**成果物:**

- `core/orchestrator.py`（Orchestrator クラス + ProgressTracker）

**テスト項目:**

- [ ] Inception フロー（キーワード → Bible生成）
- [ ] Structuring フロー（章プラン生成）
- [ ] 1章分の完全サイクル（drafting → final）
- [ ] リトライ機能（score < threshold）
- [ ] リトライ上限超過時の強制通過
- [ ] 中断・再開（各ステータスからの復元）
- [ ] 承認ゲートの動作

---

## F5: GUI基盤

| # | タスク | 実装ファイル | 詳細 | 優先 | 担当 | 状態 |
|---|---|---|---|---|---|---|
| F5-1 | `QApplication` 初期化 | `main.py` | フォント設定, QSS最小スタイル | 高 | | ⬜ |
| F5-2 | `MainWindow` スケルトン | `gui/main_window.py` | MenuBar, ToolBar, StatusBar, スプリッター配置 | 高 | | ⬜ |
| F5-3 | `OrchestratorWorker` | `gui/main_window.py` | `QThread` サブクラス, シグナル中継 | 高 | | ⬜ |
| F5-4 | `SettingsDialog` | `gui/settings_dialog.py` | タブ構成（生成/品質管理/接続）, `locked` フラグによる無効化 | 高 | | ⬜ |

**成果物:**

- `main.py`（エントリポイント）
- `gui/main_window.py`（メインウィンドウ）
- `gui/settings_dialog.py`（設定ダイアログ）

**テスト項目:**

- [ ] GUI起動
- [ ] メニュー・ツールバー表示
- [ ] 設定ダイアログ起動
- [ ] ロック項目の無効化

---

## F6: GUI各パネル

| # | タスク | 実装ファイル | 詳細 | 優先 | 担当 | 状態 |
|---|---|---|---|---|---|---|
| F6-1 | `InceptionDialog` | `gui/inception_dialog.py` | `QWizard` 3ページ, 入力値収集, 完了時Orchestrator呼び出し | 高 | | ⬜ |
| F6-2 | `ProjectPanel` | `gui/project_panel.py` | `QTreeWidget`, 章ステータスのアイコン表示, クリックで章プレビュー | 中 | | ⬜ |
| F6-3 | `PreviewPanel` | `gui/preview_panel.py` | `QTextEdit` readonly, `token_received` スロットでストリーミング追記 | 高 | | ⬜ |
| F6-4 | `BibleViewer` | `gui/log_panel.py` 内 | `project_bible.json` をツリー表示, 更新時に自動リフレッシュ | 中 | | ⬜ |
| F6-5 | `AgentLogPanel` | `gui/log_panel.py` 内 | ロール別色分け（Writer:青, Editor:橙, Proofreader:緑, Guard:紫）, タイムスタンプ | 中 | | ⬜ |
| F6-6 | StatusBar動的更新 | `gui/main_window.py` | ロール名, スコアプログレスバー, トークン残容量 | 中 | | ⬜ |
| F6-7 | 承認ゲートUI | `gui/preview_panel.py` | `needs_approval` シグナル受信 → [承認] [修正指示] ボタン表示 | 中 | | ⬜ |
| F6-8 | エラー通知UI | `gui/main_window.py` | `error_occurred` シグナル → `QMessageBox` + 一時停止/再試行 | 高 | | ⬜ |

**成果物:**

- `gui/inception_dialog.py`（新規プロジェクトウィザード）
- `gui/project_panel.py`（プロジェクトツリー）
- `gui/preview_panel.py`（原稿プレビュー）
- `gui/log_panel.py`（Bible + エージェントログ）

**テスト項目:**

- [ ] Inception ウィザード（3ページ遷移）
- [ ] プロジェクトツリー表示
- [ ] ストリーミング表示
- [ ] Bible Viewer 表示・更新
- [ ] AgentLog 色分け表示
- [ ] ステータスバー更新
- [ ] 承認ゲートUI表示
- [ ] エラーダイアログ表示

---

## F7: 統合テスト

| # | タスク | 詳細 | 優先 | 担当 | 状態 |
|---|---|---|---|---|---|
| F7-1 | Inception E2Eテスト | キーワード入力 → `project_bible.json` 生成まで確認 | 高 | | ⬜ |
| F7-2 | 1章分のDraftingサイクル | score<80でリトライ → score>=80で通過まで確認 | 高 | | ⬜ |
| F7-3 | リトライ上限超過テスト | `max_retry_count=1` でベストスコア強制採用を確認 | 高 | | ⬜ |
| F7-4 | 中断・再開テスト | `critiquing` 状態でプロセス終了 → 再起動で同章から再開 | 高 | | ⬜ |
| F7-5 | 設定ロックテスト | `drafting` 遷移後に設定画面でロック項目が無効か確認 | 中 | | ⬜ |
| F7-6 | Guard矛盾検出テスト | 意図的に矛盾する事実を持つ最終稿を渡し `superseded_by` がセットされるか | 中 | | ⬜ |
| F7-7 | トークン超過圧縮テスト | 予算超過するプロンプトを組んで圧縮後に予算内に収まるか | 中 | | ⬜ |
| F7-8 | 承認ゲート動作テスト | `chapter_approval_gate=true` でボタンが表示されるか | 低 | | ⬜ |
| F7-9 | 完全フローテスト | Inception → Structuring → 3章執筆 → 書き出しまで通し実行 | 高 | | ⬜ |

**成果物:**

- テストレポート
- 不具合修正
- パフォーマンス計測結果

---

## 最小動作版（MVP）タスク

以下のタスクで最小動作版を完成できる：

**Phase 0-1:**

- F0-1, F0-2, F0-3, F0-4

**Phase 1:**

- F1-1, F1-2, F1-3
- F2-1, F2-2, F2-3, F2-4

**Phase 2:**

- F3-1, F3-2, F3-3, F3-4, F3-5, F3-6, F3-7

**Phase 3:**

- F4-1, F4-2, F4-3, F4-4, F4-5, F4-7, F4-8

**Phase 4:**

- F5-1, F5-2, F5-3, F5-4

**Phase 5:**

- F6-1, F6-3, F6-8

**Phase 6:**

- F7-1, F7-2, F7-3, F7-4

**MVP 所要見積:** 約 14日

---

## 実装推奨順序

```
Phase 0: F0完了（環境構築）
  ↓ 並行可能
Phase 1: F1 + F2（データ層 + API層）
  ↓
Phase 2: F3（エージェント層）
  ↓ 並行可能
Phase 3: F4 + F5（オーケストレーター + GUI基盤）
  ↓
Phase 4: F6（GUI各パネル）
  ↓
Phase 5: F7（統合テスト）
```

---

## 進捗管理

### 凡例

- ⬜ 未着手
- 🔵 進行中
- ✅ 完了
- ⚠️ ブロック中
- ❌ スキップ

### 更新ルール

1. タスク着手時に「状態」列を 🔵 に更新
2. 完了時に ✅ に更新し、成果物をコミット
3. ブロッカーがある場合は ⚠️ に更新し、備考欄に理由を記載

---

## リスク管理

| リスク | 影響度 | 発生確率 | 対策 |
|---|---|---|---|
| LM Studio API 不安定 | 高 | 中 | リトライ機構 + タイムアウト調整可能化 |
| Qwen 3.5 の JSON 出力精度 | 中 | 高 | 正規表現フォールバック実装 |
| トークン予算の見積もり誤差 | 中 | 中 | 動的圧縮ロジック + 安全マージン確保 |
| GUI スレッド競合 | 中 | 低 | pyqtSignal による非同期通信徹底 |
| 長時間実行時のメモリリーク | 低 | 低 | 定期的なガベージコレクション + ログローテーション |

---

## 変更履歴

| 日付 | 変更内容 | 担当 |
|---|---|---|
| 2026-04-16 | 初版作成 | - |
