# Jules' Calendar (LLM-Planner)

## 概要
Jules' Calendarは、DashとPythonで構築されたインタラクティブなカレンダーアプリケーションです。月ビューと週ビューを切り替えてイベントを管理でき、ドラッグ＆ドロップによる直感的な操作、Undo/Redo機能、そしてLLM（大規模言語モデル）を活用したイベント作成支援機能を備えています。自然言語でのイベント入力に対応し、スマートなスケジュール管理を実現します。

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Dash Version](https://img.shields.io/badge/dash-latest-green.svg)](https://dash.plotly.com/)

## 機能

*   **月ビューと週ビューの切り替え**: 柔軟な表示オプションでスケジュールを俯瞰・詳細確認できます。
*   **イベントの作成、編集、削除**: モーダルダイアログを通じてイベントの詳細を簡単に管理できます。
*   **ドラッグ＆ドロップによるイベントの移動とリサイズ**: 週ビューでイベントを直感的に移動したり、期間を調整したりできます。
*   **Undo/Redo機能**: 誤操作を簡単に元に戻したり、やり直したりできます。
*   **LLMによるイベント作成支援**: 自然言語でイベントの内容を入力するだけで、タイトル、日時、コミットメントレベルを自動で解析し、イベント作成をアシストします。
*   **コミットメントレベル**: イベントの参加確度（Primary, Secondary, Observer, Tentative）を設定し、視覚的に区別できます。
*   **キーボードショートカット**:
    *   `Esc`: 月ビューに戻ります。
    *   `Ctrl/Cmd + Z`: Undo（元に戻す）
    *   `Ctrl/Cmd + Y`: Redo（やり直す）

## 使い方

### セットアップ

1.  **Python環境の準備**: Python 3.8以上の環境が必要です。`venv`などの仮想環境の利用を推奨します。
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

2.  **依存関係のインストール**: 必要なライブラリをインストールします。
    ```bash
    pip install -r requirements.txt
    ```

### アプリケーションの実行

以下のコマンドでアプリケーションを起動します。
```bash
python app.py
```
アプリケーションは通常、`http://127.0.0.1:8050/`で利用可能になります。

### 基本的な操作

*   **ビューの切り替え**: 画面上部の「Month」と「Week」ボタンで表示を切り替えます。
*   **日付の移動**: 「<」と「>」ボタンで月または週を移動します。「Today」ボタンで今日の日付に戻ります。
*   **イベントの作成**:
    *   週ビューで、イベントを追加したい時間帯のグリッドをクリックします。
    *   LLM入力欄に自然言語でイベント内容を入力し、「Create」ボタンをクリックします。（例: `"Design sync" tomorrow 3pm for 45 minutes, secondary`）
*   **イベントの編集**: 週ビューで既存のイベントバーをダブルクリックすると、編集モーダルが開きます。
*   **イベントの移動・リサイズ**: 週ビューでイベントバーをドラッグして移動したり、下部のハンドルをドラッグしてリサイズしたりできます。
*   **Undo/Redo**: 画面上部の「Undo」「Redo」ボタン、またはキーボードショートカットで操作履歴を管理します。

## 技術スタック

*   **フロントエンド**: Dash (Plotly Dash), Dash Bootstrap Components, JavaScript (Vanilla JS)
*   **バックエンド**: Python
*   **データベース**: なし (イベントデータはメモリ上で管理されます)

## システム要件

- Python 3.8以上
- pip（Pythonパッケージマネージャー）
- git（バージョン管理システム）

### 主要な依存関係

- **Dash**: Webアプリケーションフレームワーク
- **Dash Bootstrap Components**: レスポンシブなUIコンポーネント
- **pandas**: データ操作と分析
- **pytz**: タイムゾーン処理
- **gunicorn**: 本番環境用WSGIサーバー（オプション）

## インストール

```bash
# リポジトリをクローン
git clone https://github.com/contras11/LLM-Planner.git
cd LLM-Planner

# 仮想環境の作成とアクティベート
python -m venv venv
# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 依存関係のインストール
pip install -r requirements.txt

# （オプション）開発用依存関係のインストール
pip install black pylint pytest
```

## アプリケーションの実行

### 開発環境

```bash
python app.py
```

アプリケーションは `http://127.0.0.1:8050/` で利用可能になります。

### 本番環境

```bash
gunicorn app:server
```

## トラブルシューティング

### よくある問題と解決方法

1. **アプリケーションが起動しない**
   - 仮想環境が有効になっているか確認
   - 必要なパッケージがすべてインストールされているか確認
   - Pythonバージョンが3.8以上であることを確認

2. **イベントの作成/編集ができない**
   - ブラウザのJavaScriptが有効になっているか確認
   - キャッシュとクッキーをクリア
   - 別のブラウザで試してみる

3. **パフォーマンスの問題**
   - ブラウザのキャッシュをクリア
   - 同時に開いているイベントの数を減らす
   - ブラウザを最新バージョンに更新
