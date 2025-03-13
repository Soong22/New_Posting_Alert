import json
import os
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 셀레니엄 크롬 드라이버 설정 (headless 모드)
def get_chrome_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # 필요에 따라 HEROKU 환경에서는 binary_location이나 기타 옵션을 추가할 수 있습니다.
    driver = webdriver.Chrome(options=options)
    return driver

# 기본 구조를 갖는 블로그의 크롤링 함수 (예: chamberine3, going_tothe_moon, lhd1371, ldhwc)
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
            # 게시물 제목 추출 (구조에 따라 CSS 선택자를 조정)
            try:
                title_elem = elem.find_element(By.CSS_SELECTOR, "p.se-text-paragraph")
            except:
                title_elem = elem.find_element(By.TAG_NAME, "a")
            title = title_elem.text.strip()
            posts.append({"id": post_id, "title": title})
        except Exception:
            continue
    driver.quit()
    return posts

# ranto28은 구조가 약간 다르다고 가정하여 별도의 함수 (구조가 다르다면 CSS 선택자 등을 조정)
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
            try:
                title_elem = elem.find_element(By.CSS_SELECTOR, "p.se-text-paragraph")
            except:
                title_elem = elem.find_element(By.TAG_NAME, "a")
            title = title_elem.text.strip()
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
def get_new_posts(current, previous):
    prev_ids = {post["id"] for post in previous}
    return [post for post in current if post["id"] not in prev_ids]

# 텔레그램 메시지 전송 함수
def send_telegram_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    r = requests.post(url, data=payload)
    return r

# 텔레그램 봇 토큰과 채팅 ID (여기에 본인의 값을 입력)
TELEGRAM_TOKEN = "YOUR_TELEGRAM_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

# 각 블로그 정보 및 사용할 크롤링 함수를 지정
blogs = [
    {"blog_id": "chamberine3", "url": "https://blog.naver.com/PostList.naver?blogId=chamberine3&categoryNo=0&from=postList", "crawler": crawl_blog_default},
    {"blog_id": "ranto28", "url": "https://blog.naver.com/PostList.naver?blogId=ranto28&categoryNo=21&from=postList", "crawler": crawl_blog_ranto28},
    {"blog_id": "going_tothe_moon", "url": "https://blog.naver.com/PostList.naver?blogId=going_tothe_moon&categoryNo=0&from=postList", "crawler": crawl_blog_default},
    {"blog_id": "lhd1371", "url": "https://blog.naver.com/PostList.naver?blogId=lhd1371&categoryNo=0&from=postList", "crawler": crawl_blog_default},
    {"blog_id": "ldhwc", "url": "https://blog.naver.com/PostList.naver?blogId=ldhwc&categoryNo=0&from=postList", "crawler": crawl_blog_default},
]

def main():
    previous_data = load_previous_data()
    all_new_posts = []
    current_data = {}
    for blog in blogs:
        blog_id = blog["blog_id"]
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
            for post in new_posts:
                all_new_posts.append({"blog_id": blog_id, "id": post["id"], "title": post["title"]})
        print("----------------------------------------")
    if all_new_posts:
        message = "새로운 게시물이 발견되었습니다:\n"
        for p in all_new_posts:
            message += f"{p['blog_id']} - {p['title']} (ID: {p['id']})\n"
        send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, message)
    else:
        print("🚀 모든 블로그에서 새로운 게시물 없음")
    save_data(current_data)
    print("✅ 스크립트 실행 완료")

if __name__ == "__main__":
    main()
