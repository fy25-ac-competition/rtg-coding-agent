# generate_command_list-2

- **メソッド**: generate_command_list
- **期待形式**: commands
- **実出力分類**: commands
- **サブラベル**: (該当なし)
- **一致**: True
- **記録日時**: 2026-07-10T23:19:40

## 入力プロンプト

以下の spec を実現するために実行すべきコマンドを、実行順に列挙してください。
--- spec ---
# spec: カテゴリ絞り込み検索

## 実現方針
商品一覧画面にカテゴリ選択のドロップダウンを追加し、選択したカテゴリに一致する商品のみを表示する。

## 変更範囲
- product_list.html: カテゴリ選択ドロップダウンの追加
- product_list.js: カテゴリ選択時の絞り込みロジック
- product_service.py: カテゴリ条件付き商品取得API

## 手順
1. product_list.html にカテゴリ選択ドロップダウンを追加する
2. product_list.js にドロップダウン変更イベントのハンドラを追加する
3. product_service.py にカテゴリ条件でフィルタする関数を実装する
4. 絞り込み結果を一覧に反映する


## 出力全文

git checkout -b feature/category-filter
pytest tests/unit/product_service_test.py
npm run build
npm run dev
git add product_list.html product_list.js product_service.py
git commit -m "feat: Implement category filter for product list"
git push origin feature/category-filter
