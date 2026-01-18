import gspread
from oauth2client.service_account import ServiceAccountCredentials
import instaloader
import time
import random
import datetime
import os

# ==========================================
# [설정] 알려주신 1~18번 구조에 완벽 매칭
# ==========================================
SPREADSHEET_KEY = "1hQ1CKUWOlAZNQB3JK74hSZ3hI-QPbEpVGrn5q0PUGlg" 
TAB_NAME = "인플루언서_DB"

# 열 번호 매칭 (말씀하신 번호 그대로 적용)
COL_ID = 1            # 1: ID (A열)
COL_INSTA_ID = 2      # 2: 인스타ID (B열)
COL_CHANNEL_NAME = 3  # 3: 채널명 (C열)
COL_LINK = 4          # 4: 링크 (D열)
COL_PROFILE_PIC = 5   # 5: 프로필사진 (E열)
COL_FOLLOWERS = 6     # 6: 팔로워 (F열)
COL_SCORE = 7         # 7: 🔥화력점수 (G열)
COL_AVG_VIEWS = 8     # 8: 평균조회수 (H열)
COL_BIO = 9           # 9: 소개글(Bio) (I열)
COL_UPDATE_DATE = 17  # 17: 업데이트일 (Q열)
# ==========================================

def connect_google_sheets():
    print("📋 구글 시트에 연결 중...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("key.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_KEY).worksheet(TAB_NAME)
    return sheet

def get_instagram_data(username):
    L = instaloader.Instaloader(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        
        followers = profile.followers
        full_name = profile.full_name
        biography = profile.biography
        profile_pic = profile.profile_pic_url
        
        posts = profile.get_posts()
        count, total_likes, total_comments, total_views = 0, 0, 0, 0
        
        for post in posts:
            if count >= 10: break
            total_likes += post.likes
            total_comments += post.comments
            if post.is_video: total_views += post.video_view_count
            count += 1
            time.sleep(random.uniform(1, 3))

        score = total_likes + (total_comments * 3) + (total_views * 0.1)
        avg_views = int(total_views / count) if count > 0 else 0

        return {
            "username": profile.username, "full_name": full_name, "followers": followers,
            "profile_pic": profile_pic, "score": int(score), "bio": biography, "avg_views": avg_views
        }
    except Exception as e:
        print(f"❌ 에러 발생 ({username}): {e}")
        return None

def main():
    sheet = connect_google_sheets()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    target_id = os.environ.get('TARGET_ID', '').strip()

    # 데이터 읽어오기 (2번 열: 인스타ID 기준)
    col_ids = sheet.col_values(COL_ID)
    col_insta_ids = sheet.col_values(COL_INSTA_ID)
    col_dates = sheet.col_values(COL_UPDATE_DATE)
    
    for i, insta_id in enumerate(col_insta_ids[1:], start=2):
        if not insta_id: continue
        
        # [단건 실행] 입력된 ID와 다르면 패스
        if target_id and target_id != insta_id: continue
            
        # [자동 실행] 이미 오늘 업데이트했으면 패스
        last_update = col_dates[i-1] if len(col_dates) > i-1 else ""
        if not target_id and last_update == today: continue

        print(f"🔎 분석 시작: {insta_id} (Row {i})")
        
        # ★ 아이디로 URL 자동 생성 (4번 열 저장용) ★
        generated_url = f"https://www.instagram.com/{insta_id}/"
        
        data = get_instagram_data(insta_id)
        
        if data:
            # 1. 시트 데이터 업데이트 (1번 열 ID 생성)
            current_id = col_ids[i-1] if len(col_ids) > i-1 else ""
            if not current_id:
                sheet.update_cell(i, COL_ID, f"INF_{i:03d}")
            
            # 2. 크롤링 데이터 저장 (알려주신 열 번호 그대로)
            sheet.update_cell(i, COL_CHANNEL_NAME, data['full_name'])  # 3번 열
            sheet.update_cell(i, COL_LINK, generated_url)              # 4번 열
            sheet.update_cell(i, COL_PROFILE_PIC, data['profile_pic'])  # 5번 열
            sheet.update_cell(i, COL_FOLLOWERS, data['followers'])      # 6번 열
            sheet.update_cell(i, COL_SCORE, data['score'])              # 7번 열
            sheet.update_cell(i, COL_AVG_VIEWS, data['avg_views'])      # 8번 열
            sheet.update_cell(i, COL_BIO, data['bio'])                  # 9번 열
            sheet.update_cell(i, COL_UPDATE_DATE, today)                # 17번 열
            
            print(f"   ✅ {insta_id} 저장 완료!")

        # 차단 방지 휴식
        wait_time = random.uniform(10, 20)
        time.sleep(wait_time)

if __name__ == "__main__":
    main()
