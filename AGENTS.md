# AGENTS.md — Autonomous Novel Architect (ANA)

## プロジェクト概要

Python 3.12 + PyQt6 で構築する長編小説自律生成システム。  
LM Studio 0.4.11（localhost:1234）上の **Qwen 3.5 9B**（コンテキスト 65,536 tokens）をバックエンドとして使用する。  
対象規模：中編 2〜10万字、5〜15章。

---

## ディレクトリ構成（予定）

```
d:\code\StoryMaker\
├── main.py                  # エントリポイント
├── config.yaml              # 全設定（執筆開始後ロック項目あり）
├── requirements.txt
├── core/
│   ├── orchestrator.py      # 状態機械 + ワークフロー制御
│   ├── agents.py            # 4ロール（Writer/Editor/Proofreader/Guard）
│   ├── bible.py             # ProjectBible CRUD + Guard 反映ロジック
│   ├── context_manager.py   # トークン予算管理 + プロンプト組み立て
│   ├── config.py            # pydantic ローダー
│   └── api_client.py        # LM Studio ラッパー（ストリーミング対応）
├── gui/                     # PyQt6 UI（メインウィンドウ + 各パネル/ダイアログ）
├── prompts/                 # 各ロールのシステムプロンプト（*.txt）
└── output/{project_name}/  # 生成物（Bible JSON, 原稿, ログ）
```

> 実装前は上記ディレクトリが存在しない。**F0-2** でスキャフォールドを作成すること。

---

## 開発フェーズと依存関係

| フェーズ | 内容 | 依存 |
|---|---|---|
| F0 | 環境セットアップ | — |
| F1 | コアデータ層（Bible / Config / Progress） | F0 |
| F2 | APIクライアント層（LMStudioClient） | F0 |
| F3 | エージェント層 + ContextManager | F1, F2 |
| F4 | オーケストレーター | F1–F3 |
| F5 | GUI基盤（PyQt6 MainWindow） | F0 |
| F6 | GUI各パネル | F4, F5 |
| F7 | 統合テスト | F4, F6 |

---

## 開発コマンド

| 用途 | コマンド |
|---|---|
| 依存インストール | `pip install -r requirements.txt` |
| アプリ起動 | `python main.py` |
| LM Studio 疎通確認 | `curl http://localhost:1234/v1/models` |
| Lint | 未発見/不明 |
| テスト実行 | 未発見/不明 |

---

## 主要設計ルール

### エージェント呼び出し

- 4ロール（Writer / Editor / Proofreader / Guard）は**同一モデル（Qwen 3.5）に異なるシステムプロンプトを渡す**擬似マルチエージェント構成。
- システムプロンプトは `prompts/*.txt` から読み込む。コード内にハードコードしない。
- Editor の評価スコアが **80点未満** → Writer へ差し戻し（最大リトライ数は `config.yaml` で設定）。

### コンテキスト管理

- プロンプトは **Fixed Memory / Sliding Window / Summarized Memory / Direct Injection** の4ブロックで構成。
- `ContextManager` がトークン予算を計算してブロックを切り詰める。65,536 tokens を超えないこと。
- `tiktoken` でトークン数を計測する（モデル近似は `cl100k_base` を使用）。

### 状態永続化

- `output/{project_name}/progress.json` が唯一の進捗ソース。クラッシュ後は `get_resume_point()` で復元する。
- 章の確定後は `project_bible.json` を Guard が自動更新する。**Bible の直接書き換えは行わず、必ず `add_fact()` / `resolve_conflict()` 経由で更新すること。**

### config.yaml

- 執筆開始後は「ロック項目」（モデル名・章数・出力先など）を変更しない。ロック状態の検査は `ProgressTracker.lock()` で行う。

### GUI

- PyQt6 を使用。Qt Designer の `.ui` ファイルは使用しない（コードファーストで実装）。
- 新規プロジェクト作成は `InceptionDialog`（`QDialog`）で行う。**3ページウィザードではなく単一テキスト枠**に全情報を入力する形式。「テンプレートをコピー」ボタンでフォーマットをクリップボードへ渡し、ChatGPT 等で作成した原案をそのまま貼り付けられるよう設計する。
- ストリーミングレスポンスは `preview_panel.py` にチャンク単位で表示する。

---

## 成果物スキーマ（概要）

```
output/{project_name}/
├── progress.json
├── project_bible.json
├── plot/
│   ├── overall_plot.txt
│   └── chapter_plans/ch{N:02d}_plan.txt
└── manuscript/
    ├── ch{N:02d}_final.txt
    └── logs/
        ├── ch{N:02d}_drafts.jsonl
        └── guard_actions.jsonl
```

詳細スキーマ（`project_bible.json` / `progress.json`）は [docs/ANA_design_spec.md](docs/ANA_design_spec.md) を参照。
