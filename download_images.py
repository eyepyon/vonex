#!/usr/bin/env python3
"""
readdy.ai の画像をダウンロードして web/img/ に保存し、HTMLを更新するスクリプト
"""

import os
import re
import requests
import hashlib
from urllib.parse import unquote

# 画像保存先
IMG_DIR = "web/img"

# HTMLファイル
HTML_FILES = ["web/index.html", "web/faq.html", "web/kiyaku.html", "web/pp.html"]

def extract_image_urls(html_content):
    """HTMLからreaddy.aiの画像URLを抽出"""
    pattern = r'https://readdy\.ai/api/search-image\?[^"\'\s)>]+'
    urls = re.findall(pattern, html_content)
    return list(set(urls))  # 重複を除去

def generate_filename(url):
    """URLからファイル名を生成"""
    # seqパラメータを抽出
    seq_match = re.search(r'seq=([^&]+)', url)
    if seq_match:
        seq = seq_match.group(1)
        return f"{seq}.jpg"
    
    # seqがない場合はハッシュを使用
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    return f"img_{url_hash}.jpg"

def download_image(url, filepath):
    """画像をダウンロード"""
    try:
        print(f"ダウンロード中: {url[:80]}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        print(f"  -> 保存: {filepath}")
        return True
    except Exception as e:
        print(f"  -> エラー: {e}")
        return False

def main():
    # 画像ディレクトリを作成
    os.makedirs(IMG_DIR, exist_ok=True)
    
    # URL -> ローカルパスのマッピング
    url_mapping = {}
    
    # 全HTMLファイルからURLを収集
    all_urls = set()
    for html_file in HTML_FILES:
        if os.path.exists(html_file):
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            urls = extract_image_urls(content)
            all_urls.update(urls)
            print(f"{html_file}: {len(urls)} 個の画像URL")
    
    print(f"\n合計: {len(all_urls)} 個のユニークな画像URL\n")
    
    # 画像をダウンロード
    for url in all_urls:
        filename = generate_filename(url)
        filepath = os.path.join(IMG_DIR, filename)
        local_path = f"img/{filename}"  # HTMLからの相対パス
        
        if download_image(url, filepath):
            url_mapping[url] = local_path
    
    print(f"\n{len(url_mapping)} 個の画像をダウンロードしました\n")
    
    # HTMLファイルを更新
    for html_file in HTML_FILES:
        if not os.path.exists(html_file):
            continue
        
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        updated = False
        for url, local_path in url_mapping.items():
            if url in content:
                content = content.replace(url, local_path)
                updated = True
        
        if updated:
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"更新: {html_file}")
    
    print("\n完了!")

if __name__ == "__main__":
    main()
