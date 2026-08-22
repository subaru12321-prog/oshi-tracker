# 推しトラッカー (oshi_tracker)

推し(≠MEなど)の SHOWROOM / Instagram / X / TikTok の投稿・配信情報を定期収集し、
ローカルのWeb画面で一覧表示する個人用アプリ。

## 前提として知っておくこと

- SHOWROOMとInstagramは公開情報の取得なので比較的安定します。
- XとTikTokは公式APIが個人の情報収集に向いておらず、非公式ライブラリ
  (`twikit`, `TikTokApi`) を使っています。これらは各サービスの利用規約上
  グレーな手法で、**仕様変更で突然動かなくなる・アカウントが制限される
  可能性があります**。自己責任で、頻度を上げすぎずに使ってください。
- 収集した内容は自分専用に使い、再配布・公開しないでください。

## セットアップ

1. Python 3.11+ が必要です(このPCには3.12が入っています)。

2. 依存パッケージをインストール:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

3. 設定ファイルを作成:
   ```bash
   cp config.example.yaml config.yaml
   cp .env.example .env
   ```

4. `config.yaml` はWeb検索で調べたメンバー情報を入れた状態で既に用意してあります。
   [ACCOUNTS.md](ACCOUNTS.md) のリンクを開いて、本人・公式のアカウントか確認してください。
   間違っていたら `config.yaml` を直接書き換えてください。新しく別の推しを追加する場合も
   同じ形式(`members:` の下に1ブロック追加)で書けます。
   - **SHOWROOM**: ルームURL `https://www.showroom-live.com/xxxxx` の `xxxxx` 部分
   - **Instagram / X / TikTok**: `@` を除いたユーザー名

5. XとTikTokを使う場合は `.env` に認証情報を入れる(任意。使わないプラットフォームは空でOK)。
   - `X_USERNAME` / `X_EMAIL` / `X_PASSWORD`: 自分のXアカウントのログイン情報
   - `TIKTOK_MS_TOKEN`: ブラウザでtiktok.comにログイン→開発者ツール(F12)→
     Application タブ→Cookies→`ms_token` の値をコピー
   - **`.env` は絶対に他人と共有・公開しないこと。**

## 使い方

### 1回だけ収集する

```bash
python main.py
```

新しい投稿だけが `posts.db` (SQLite) に保存されます。

### ダッシュボードを見る

```bash
python webapp.py
```

ブラウザで http://127.0.0.1:5000 を開くと一覧が見られます。
画面上部の「メンバーで絞り込み」でメンバー別、プラットフォームのタブでSHOWROOM/Instagram/X/TikTok別に絞り込めます。

### スマホから見る

同じWi-Fiに繋いだPCとスマホなら、スマホのブラウザで
`http://<PCのIPアドレス>:5000` を開くと同じ画面が見られます。

PCのIPアドレスは以下で確認できます:
```bash
ipconfig
```
「IPv4 アドレス」(例: `192.168.0.16`) を使ってください。

**注意:** この方法はパスワードなどの認証が一切ない状態で画面を公開します。
自宅などの信頼できるWi-Fi内でのみ使い、カフェ等の公衆Wi-Fiでは使わないでください。
また `python webapp.py` を実行している間・PCがスリープしていない間だけアクセスできます。

スマホから繋がらない場合、Windowsのファイアウォールがブロックしている可能性があります。
初回 `python webapp.py` 実行時に「Windows セキュリティの重要な警告」が出たら
「プライベートネットワーク」にチェックを入れて「アクセスを許可する」を選んでください。

### 定期的に自動収集する(ローカルで動かす場合)

Windowsのタスクスケジューラに `python main.py` を
`config.yaml` の `poll_interval_minutes` と同じ間隔で登録してください。
(例: 20分ごと)

## PCの電源が入っていなくてもスマホで見る(GitHub Pages)

PCを常時起動しておきたくない場合、収集(GitHub Actions)と表示(GitHub Pages)を
どちらも無料のGitHub上で動かす構成にできます。詳しい仕組みは
[.github/workflows/collect.yml](.github/workflows/collect.yml) と [docs/](docs) を参照。

### セットアップ手順

1. GitHubの自分のリポジトリ設定画面 → Settings → Secrets and variables → Actions
   → "New repository secret" で以下を登録(使わないプラットフォームは省略可):
   - `X_USERNAME` / `X_EMAIL` / `X_PASSWORD`
   - `TIKTOK_MS_TOKEN`

   **これらは自分のログイン情報なので、必ず自分で入力してください。**

2. GitHubのリポジトリ設定画面 → Settings → Actions → General →
   "Workflow permissions" で **"Read and write permissions"** を選んで保存
   (収集結果をリポジトリに書き戻すために必要)。

3. GitHubのリポジトリ設定画面 → Settings → Pages →
   "Build and deployment" の Source を **"Deploy from a branch"**、
   Branch を **`main` / `docs`** に設定して Save。
   数分後に `https://<ユーザー名>.github.io/<リポジトリ名>/` でアクセスできるようになります。
   このURLをスマホのホーム画面に追加しておくと、アプリのように使えます。

4. 初回は手動で1回動かして反映を確認できます:
   リポジトリの Actions タブ → "collect" ワークフロー → "Run workflow" ボタン。

### 注意点

- 更新は30分おきの自動実行(GitHub Actionsの仕様上、多少前後・遅延することがあります)。
- **X・TikTokは、GitHub側のサーバー(データセンターのIPアドレス)からのアクセスになるため、
  自宅PCから使う場合よりも各サービスのBot対策に引っかかりやすく、失敗しやすいです。**
  失敗しても他のプラットフォーム(SHOWROOM・Instagram)の収集は継続されるので、
  「Xだけ最近投稿が増えない」といった状態になったら、その時期は上手く取れていない可能性があります。
- 収集データ(`posts.db`・`docs/data.json`)と `config.yaml` はリポジトリにコミットされ、
  **リポジトリがPublicなので誰でも見られます**。`.env`(ログイン情報)は`.gitignore`で
  除外されており、コミットも公開もされません。

## 収集元ごとの仕組みメモ

| プラットフォーム | 方式 | 安定性 |
|---|---|---|
| SHOWROOM | 非公式の公開JSON API (ログイン不要) | 中 |
| Instagram | `instaloader` (公開プロフィールをログインなしで取得) | 中(レート制限あり) |
| X | `twikit` (要ログイン、非公式) | 低 |
| TikTok | `TikTokApi` + Playwright (要ms_token、非公式) | 低 |

うまく取得できないプラットフォームがあっても、他のプラットフォームの収集は継続されます。
