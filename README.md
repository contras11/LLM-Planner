# Jules' Calendar (`app.py`)

## 概要
このアプリは、DashとDash Bootstrap Componentsを使ったインタラクティブなカレンダーWebアプリです。週・月単位ビューでイベントを管理でき、ドラッグ＆ドロップやリサイズ、LLMによる自然言語イベント追加、コミットメント分類など多彩な機能を備えています。  
（例: "Design sync tomorrow 3pm for 45 minutes, secondary" のような入力で自動イベント登録が可能）

## 主な機能
- **週・月ビュー切り替え**（月: バッジ表示／週: 時間軸＋イベントバー）
- **イベント追加・編集・削除**（モーダルからや、バーのドラッグ/リサイズ）
- **ドラッグ＆ドロップ/リサイズ**（JSによる直感的な操作）
- **LLM入力によるイベント自動生成**（自然言語→日時・タイトル・コミットメント推定）
- **コミットメント（Primary/Secondary/Observer/Tentative）色分け表示**
- **日跨りイベント対応・最大24時間まで**
- **ユーザーIDサンプル（実装例: user_a, user_b, all）**

## セットアップ方法

1. 必要なPythonパッケージをインストール：
    ```bash
    pip install dash dash-bootstrap-components pandas pytz
    ```

2. `app.py` を実行：
    ```bash
    python app.py
    ```
    - デフォルトで `localhost:8050` で起動します。

## 画面構成・操作方法

- **月ビュー**：各日付セルにイベントバッジ。セルクリックで週ビューにジャンプ。
- **週ビュー**：時間軸に沿ってイベントバー表示。バーはドラッグ＆リサイズ可能。
- **イベント追加**：日付セルクリックや「Create」ボタンでモーダル表示し、イベント入力。
- **LLM入力**：下部のテキストボックスに自然言語で入力→「Create」を押すと解析・モーダルに反映。
- **ドラッグ/リサイズ操作**：バーを直接ドラッグで時間・日付変更、下辺ドラッグで長さ変更。

## 主要ライブラリ
- [Dash](https://dash.plotly.com/)
- [Dash Bootstrap Components](https://dash-bootstrap-components.opensource.faculty.ai/)
- [pandas](https://pandas.pydata.org/)
- [pytz](https://pythonhosted.org/pytz/)

## ファイル構成
- `app.py` : メインアプリケーション（本ファイル）
- `README.md` : プロジェクト概要（本ファイルから内容を充実させることも推奨）

## 補足
- サンプルイベントデータ（`events_init`）が初期ロードされます。
- 本アプリは複数ユーザへの拡張、外部DB連携、認証機能追加なども容易です。
- LLM部分は `dummy_llm_api()` のサンプル実装となっています（外部API連携可能）。

## ライセンス
MITライセンス（内容はプロジェクトの `LICENSE` ファイルを参照してください）

---

ご不明点や機能追加要望があればIssueでお知らせください。
