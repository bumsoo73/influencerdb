import gspread
from oauth2client.service_account import ServiceAccountCredentials
import instaloader
import time
import random
import datetime

# ==========================================
# [설정]
SPREADSHEET_KEY = "1hQ1CKUWOlAZNQB3JK74hSZ3hI-QPbEpVGrn5q0PUGlg" 
TAB_NAME = "인플루언서_DB"
# ==========================================

def connect_google_sheets():
    print("📋 구글 시트에 연결 중...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("key.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_KEY).worksheet(TAB_NAME)
    return sheet

def get_instagram_data(username):
    # [수정 1] "저 로봇 아닙니다" 하고 가짜 신분증(User-Agent) 만들기
    L = instaloader.Instaloader(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        
        # 1. 기본 정보
        followers = profile.followers
        full_name = profile.full_name
        biography = profile.biography
        profile_pic = profile.profile_pic_url
        
        # 2. 화력 분석 (최근 10개)
        posts = profile.get_posts()
        count = 0
        total_likes = 0
        total_comments = 0
        total_views = 0 
        
        for post in posts:
            if count >= 10: break
            
            total_likes += post.likes
            total_comments += post.comments
            if post.is_video:
                total_views += post.video_view_count
            
            count += 1
            # [수정 2] 게시물 하나 볼 때마다 2~5초 천천히 보기
            time.sleep(random.uniform(2, 5))

        # 3. 점수 계산
        score = 0
        avg_views = 0
        if count > 0:
            score = total_likes + (total_comments * 3) + (total_views * 0.1)
            avg_views = int(total_views / count)

        return {
            "username": profile.username,
            "full_name": full_name,
            "followers": followers,
            "profile_pic": profile_pic,
            "score": int(score),
            "bio": biography,
            "avg_views": avg_views
        }

    except Exception as e:
        print(f"❌ 에러 발생 ({username}): {e}")
        
        # [수정 3] "잠깐 기다려(Please wait)" 에러 뜨면 2분 동안 죽은 척 하기
        if "401" in str(e) or "Please wait" in str(e):
            print("   🚨 인스타그램이 눈치챘습니다! 2분간 대기합니다...")
            time.sleep(120) 
        
        return None

def main():
    sheet = connect_google_sheets()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    urls = sheet.col_values(4) 
    
    for i, url in enumerate(urls[1:], start=2):
        if not url or "instagram.com" not in url: continue

        # Q열 업데이트 날짜 확인
        last_update = sheet.cell(i, 17).value 
        if last_update == today:
            print(f"PASS: {url} (오늘 이미 완료)")
            continue

        try:
            username = url.strip().split("instagram.com/")[-1].replace("/", "").split("?")[0]
        except:
            continue
        
        print(f"🔄 {username} 분석 중...")
        data = get_instagram_data(username)
        
        if data:
            # A열: ID (없으면 생성)
            current_id = sheet.cell(i, 1).value
            if not current_id:
                sheet.update_cell(i, 1, f"INF_{i:03d}") 
            
            # 저장 로직 (순서대로)
            sheet.update_cell(i, 2, data['username'])
            sheet.update_cell(i, 3, data['full_name'])
            # D열(링크) 건너뜀
            sheet.update_cell(i, 5, data['profile_pic'])
            sheet.update_cell(i, 6, data['followers'])
            sheet.update_cell(i, 7, data['score'])
            sheet.update_cell(i, 8, data['avg_views'])
            sheet.update_cell(i, 9, data['bio'])
            sheet.update_cell(i, 17, today)
            
            print(f"   ✅ 저장 완료! (점수: {data['score']})")
        
        # [수정 4] 한 명 끝나면 15~30초 푹 쉬기 (제일 중요!)
        wait_time = random.uniform(15, 30)
        print(f"   -> 인스타그램 눈치 보는 중... {int(wait_time)}초 휴식")
        time.sleep(wait_time)

if __name__ == "__main__":
    main()
