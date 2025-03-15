import re
import json
import os
import requests
import base64
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# GitHub API 관련 환경 변수 (Heroku Config Vars 또는 로컬 환경 변수에 설정)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO_OWNER = os.environ.get("GITHUB_REPO_OWNER")
GITHUB_REPO_NAME = os.environ.get("GITHUB_REPO_NAME")
FILE_PATH = "posts_data.json"

# 셀레니엄 크롬 드라이버 설정 (headless 모드)
def get_chrome_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # 필요시 Heroku 등 환경에 맞게 추가 옵션을 설정할 수 있습니다.
    driver = webdriver.Chrome(options=options)
    return driver

# 실제 게시물만 추출하는 헬퍼 함수: id가 "post_" 뒤에 숫자로만 이루어졌는지 확인
def is_valid_post_id(post_id):
    return re.match(r"^post_\d+$", post_id) is not None

# 기본 구조를 갖는 블로그의 크롤링 함수
def crawl_blog_default(blog_url, blog_id):
    driver = get_chrome_driver()
    driver.get(blog_url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[id^='post_']"))
        )
    except Exception as e:
        print(f"Error loading {blog_id}: {e}")
        driver.quit()
        return []
    posts = []
    post_elements = driver.find_elements(By.CSS_SELECTOR, "div[id^='post_']")
    for elem in post_elements:
        try:
            post_id = elem.get_attribute("id")
            if not is_valid_post_id(post_id):
                continue
            try:
                title_elem = elem.find_element(By.CSS_SELECTOR, "p.se-text-paragraph")
            except:
                title_elem = elem.find_element(By.TAG_NAME, "a")
            title = title_elem.text.strip()
            if title:
                posts.append({"id": post_id, "title": title})
        except Exception:
            continue
    driver.quit()
    return posts

# ranto28 전용 크롤러 (구조가 다르면 CSS 선택자 등을 조정)
def crawl_blog_ranto28(blog_url, blog_id):
    driver = get_chrome_driver()
    driver.get(blog_url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[id^='post_']"))
        )
    except Exception as e:
        print(f"Error loading {blog_id}: {e}")
        driver.quit()
        return []
    posts = []
    post_elements = driver.find_elements(By.CSS_SELECTOR, "div[id^='post_']")
    for elem in post_elements:
        try:
            post_id = elem.get_attribute("id")
            if not is_valid_post_id(post_id):
                continue
            try:
                title_elem = elem.find_element(By.CSS_SELECTOR, "p.se-text-paragraph")
            except:
                title_elem = elem.find_element(By.TAG_NAME, "a")
            title = title_elem.text.strip()
            if title:
                posts.append({"id": post_id, "title": title})
        except Exception:
            continue
    driver.quit()
    return posts

# 이전 크롤링 결과 로드 (블로그별로 저장)
def load_previous_data():
    if os.path.exists("posts_data.json"):
        with open("posts_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# 현재 크롤링 결과 저장
def save_data(data):
    with open("posts_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 이전 결과와 비교하여 새 게시물만 반환
# id가 없으면 새로운 게시물이고, id가 동일해도 제목(title)이 변경되었으면 새로운 게시물로 판단합니다.
def get_new_posts(current, previous):
    prev_map = {post["id"]: post for post in previous}
    new_posts = []
    for post in current:
        pid = post["id"]
        if pid not in prev_map:
            new_posts.append(post)
        else:
            # 제목이 변경된 경우
            if post["title"] != prev_map[pid].get("title", ""):
                new_posts.append(post)
    return new_posts

# 텔레그램 메시지 전송 함수
def send_telegram_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    r = requests.post(url, data=payload)
    return r

# 텔레그램 봇 토큰과 채팅 ID들 (여러 개 지정)
TELEGRAM_TOKEN = "7867142124:AAGASrA9H9fpwL8VnIGkT211ucBLzAIsiKw"
TELEGRAM_CHAT_IDS = ["7692140662", "6192459712"]

# 블로그 아이디와 텔레그램 메시지에 사용할 별칭(블로그 제목) 매핑
blog_names = {
    "chamberine3": "전황의 주식홈트",
    "ranto28": "메르",
    "going_tothe_moon": "고잉투더문",
    "lhd1371": "한걸음",
    "ldhwc": "시황맨의 시장이야기"
}

# 각 블로그 정보 및 사용할 크롤링 함수를 지정
blogs = [
    {"blog_id": "chamberine3", "url": "https://blog.naver.com/PostList.naver?blogId=chamberine3&categoryNo=0&from=postList", "crawler": crawl_blog_default},
    {"blog_id": "ranto28", "url": "https://blog.naver.com/PostList.naver?blogId=ranto28&categoryNo=21&from=postList", "crawler": crawl_blog_ranto28},
    {"blog_id": "going_tothe_moon", "url": "https://blog.naver.com/PostList.naver?blogId=going_tothe_moon&categoryNo=0&from=postList", "crawler": crawl_blog_default},
    {"blog_id": "lhd1371", "url": "https://blog.naver.com/PostList.naver?blogId=lhd1371&categoryNo=0&from=postList", "crawler": crawl_blog_default},
    {"blog_id": "ldhwc", "url": "https://blog.naver.com/PostList.naver?blogId=ldhwc&categoryNo=0&from=postList", "crawler": crawl_blog_default},
]

# GitHub API를 사용해 posts_data.json 파일을 업데이트하는 함수
def update_file_on_github(commit_message="Update posts_data.json"):
    """GitHub API를 이용하여 파일 내용을 업데이트"""
    if not GITHUB_TOKEN or not GITHUB_REPO_OWNER or not GITHUB_REPO_NAME:
        print("❌ GitHub 관련 환경 변수가 설정되어 있지 않습니다.")
        return

    # 1. 현재 파일 내용을 base64 인코딩
    with open("posts_data.json", "r", encoding="utf-8") as f:
        file_content = f.read()
    encoded_content = base64.b64encode(file_content.encode("utf-8")).decode("utf-8")

    # 2. 기존 파일 정보를 조회하여 SHA 값 가져오기
    url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    get_resp = requests.get(url, headers=headers)
    if get_resp.status_code == 200:
        file_info = get_resp.json()
        sha = file_info["sha"]
    elif get_resp.status_code == 404:
        # 파일이 없으면 새로 생성할 수 있음
        sha = None
    else:
        print("❌ 파일 정보를 가져오지 못했습니다:", get_resp.text)
        return

    # 3. 파일 업데이트 API 호출 (PUT)
    data = {
        "message": commit_message,
        "content": encoded_content,
    }
    if sha:
        data["sha"] = sha

    put_resp = requests.put(url, headers=headers, json=data)
    if put_resp.status_code in (200, 201):
        print("✅ GitHub 파일 업데이트 성공!")
    else:
        print("❌ GitHub 파일 업데이트 실패:", put_resp.text)

def main():
    previous_data = load_previous_data()
    all_new_posts = []
    current_data = {}
    for blog in blogs:
        blog_id = blog["blog_id"]
        display_name = blog_names.get(blog_id, blog_id)
        print(f"📌 {blog_id} 크롤링 중...")
        posts = blog["crawler"](blog["url"], blog_id)
        print(f"🚀 {blog_id}에서 {len(posts)}개의 게시물 발견")
        current_data[blog_id] = posts
        prev_posts = previous_data.get(blog_id, [])
        new_posts = get_new_posts(posts, prev_posts)
        if new_posts:
            print(f"새로운 게시물 {len(new_posts)}개 발견:")
            for post in new_posts:
                print(f"  - Post ID: {post['id']} | Title: {post['title']}")
                # 게시물 링크 생성: "post_" 뒤의 숫자만 사용 (예: post_123 -> https://blog.naver.com/{blog_id}/123)
                numeric_id = post["id"].replace("post_", "")
                post_link = f"https://blog.naver.com/{blog_id}/{numeric_id}"
                # 텔레그램 메시지 구성
                message = (f"📌 '{display_name}' 블로그에 새로운 게시물이 올라왔습니다!\n"
                           f"{post['title']}\n"
                           f"{post_link}")
                # 각 채팅 아이디로 메시지 전송
                for chat_id in TELEGRAM_CHAT_IDS:
                    send_telegram_message(TELEGRAM_TOKEN, chat_id, message)
                all_new_posts.append({
                    "blog_id": blog_id,
                    "display_name": display_name,
                    "id": post["id"],
                    "title": post["title"],
                    "link": post_link
                })
        print("----------------------------------------")
    if not all_new_posts:
        print("🚀 모든 블로그에서 새로운 게시물 없음")
    save_data(current_data)
    print("✅ 스크립트 실행 완료")
    
    # GitHub API를 통해 posts_data.json 파일 업데이트
    update_file_on_github("자동 업데이트: posts_data.json 변경")

if __name__ == "__main__":
    main()
