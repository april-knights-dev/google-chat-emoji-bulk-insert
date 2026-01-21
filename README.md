# Google Chat Emoji Bulk Uploader

Slackからエクスポートした絵文字をGoogle Chatに一括登録するツール。

## 機能

- Slackエクスポートの絵文字画像を自動検出
- Google Chat APIの制約に基づく自動バリデーション
- 制約違反の絵文字はスキップしてログ出力
- 有効な絵文字をすべて一括登録
- 既存の絵文字はスキップ（オプション）
- **エラーファイルの自動分類**: バリデーションエラー・アップロードエラーをカテゴリ別にフォルダ分け

## Google Chat 絵文字の制約

| 項目 | 制約 |
|------|------|
| ファイルサイズ | 256KB以下 |
| 寸法 | 64px〜500pxの正方形 |
| 形式 | PNG, JPG, GIF |
| 命名規則 | 小文字英数字、ハイフン、アンダースコアのみ |

## ディレクトリ構造

```
google-chat-emoji-bulk-insert/
├── main.py
├── requirements.txt
├── credentials.json      # Google Cloud からダウンロード（要作成）
├── emojis/               # ここに絵文字画像を配置（要作成）
│   ├── party-parrot.gif
│   ├── shipit.png
│   ├── thumbsup.png
│   └── ...
└── src/
    ├── auth.py
    ├── validator.py
    └── emoji_uploader.py
```

## 絵文字の配置

1. プロジェクトルートに `emojis/` ディレクトリを作成
2. Slackからエクスポートした絵文字画像を配置

```bash
mkdir emojis
# Slackエクスポートした画像をコピー
cp /path/to/slack-export/*.png emojis/
cp /path/to/slack-export/*.gif emojis/
```

**ファイル名 = 絵文字名** になります。例：`party-parrot.gif` → `:party-parrot:`

## セットアップ

### 1. Google Cloud Console での設定

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. プロジェクトを作成または選択
3. 「APIとサービス」→「有効なAPIとサービス」で **Google Chat API** を有効化
4. 「APIとサービス」→「OAuth同意画面」を設定
   - スコープに `https://www.googleapis.com/auth/chat.customemojis` を追加
5. 「APIとサービス」→「認証情報」→「認証情報を作成」→「OAuthクライアントID」を選択
6. アプリケーションの種類: **デスクトップアプリ**
7. 作成後、JSONをダウンロードして `credentials.json` として保存
8. **Google Chat アプリの設定**（重要）
   - Google Cloud Console → 「Google Chat API」→「構成」
   - アプリ名、アバターURL、説明を入力（必須項目）

### 2. 依存関係のインストール

```bash
pip install -r requirements.txt
```

## 使い方

### 基本的な使い方

```bash
# emojis/ ディレクトリの絵文字をアップロード
python main.py emojis/
```

初回実行時にブラウザが開き、Googleアカウントでの認証を求められます。

### オプション

```bash
# ドライラン（バリデーションのみ、アップロードしない）
python main.py emojis/ --dry-run

# カスタム認証ファイルの指定
python main.py emojis/ --credentials my-creds.json --token my-token.pickle

# 既存の絵文字をスキップしない
python main.py emojis/ --no-skip-existing

# アップロード間隔の調整（秒）
python main.py emojis/ --delay 1.0

# エラーファイルをカテゴリ別にフォルダ分け
python main.py emojis/ --organize-errors errors/
```

### エラーファイルの分類

`--organize-errors` オプションを使うと、エラーファイルがカテゴリ別にフォルダ分けされます。

```
errors/
├── invalid_dimension/     # サイズが64-500px範囲外
├── invalid_format/        # PNG/JPEG/GIF以外の形式
├── not_square/            # 正方形でない画像
├── too_large/             # 256KB超過
├── invalid_name/          # 無効な絵文字名
└── upload_errors/         # アップロード時のAPIエラー
    ├── invalid_payload/   # GIFエンコード問題
    ├── reserved_name/     # 予約語・禁止ワード
    ├── name_too_long/     # 名前が長すぎる
    └── invalid_name_api/  # APIが拒否した無効な名前
```

### 出力例

```
Scanning directory: emojis/
Found 150 image files

Validating emojis...

============================================================
VALIDATION SUMMARY
============================================================
Total files: 150
Valid:       142
Invalid:     8

--- SKIPPED (Invalid) ---
  [NG] Party-Parrot: Invalid name 'Party-Parrot': only lowercase letters, numbers, hyphens, underscores allowed
  [NG] huge_image: File too large: 320.5KB (max: 256KB)
  [NG] tiny: Invalid dimension: 32px (must be 64-500px)
============================================================

Authenticating with Google...
Checking existing emojis...
Found 50 existing emojis

Uploading 142 emojis...
[1/142] SKIP (exists): thumbsup
[2/142] Uploading: party-parrot... OK
[3/142] Uploading: shipit... OK
...

============================================================
UPLOAD SUMMARY
============================================================
Attempted: 140
Success:   138
Failed:    2

--- FAILED UPLOADS ---
  [FAILED] some-emoji: API error (409): Emoji already exists
============================================================
```

## Slackからの絵文字エクスポート

Slackの絵文字をエクスポートするには：

1. Slack管理画面の「カスタム絵文字」ページにアクセス
2. ブラウザの開発者ツールを使用してエクスポート、または
3. サードパーティツール（slack-emoji-exporterなど）を使用

## 注意事項

- **OAuth 2.0認証必須**: サービスアカウントは使用できません
- **権限**: 絵文字を登録するには、組織のGoogle Workspace管理者権限が必要な場合があります
- **レート制限**: API呼び出しにはレート制限があります。`--delay` オプションで調整してください
- **credentials.json はコミットしない**: `.gitignore` に含まれていますが、確認してください
- **Google Chat アプリの設定が必要**: Google Cloud ConsoleでChat APIを有効化した後、Chat アプリの設定（アバターURL、説明文）も必要です

## トラブルシューティング

### "Google Chat app not found" エラー

- Google Cloud Console で Chat API の「構成」を設定してください
- アバターURL と説明 は必須項目です

### "Access denied" エラー

- Google Workspaceの管理者に連絡して、Chat APIへのアクセス権限を確認してください

### "Quota exceeded" エラー

- `--delay` オプションの値を増やしてください
- 時間をおいて再実行してください

### 認証エラー

- `token.pickle` を削除して再認証してください
- credentials.json が正しいか確認してください

### "Invalid payload" エラー（GIFファイル）

- 一部のGIFファイルはGoogle Chat APIで処理できません
- PNGに変換するか、GIFを再エンコードしてください

### "Malformed custom emoji name" エラー

- 絵文字名が以下の条件に違反しています：
  - 小文字英数字、ハイフン、アンダースコアのみ使用可能
  - 予約語（atom, biohazard, skip など）は使用不可
  - 1文字の名前は使用不可
  - 末尾に特殊文字の連続は不可

## ライセンス

MIT
