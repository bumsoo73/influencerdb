import gspread
from oauth2client.service_account import ServiceAccountCredentials
import instaloader
import time
import random
import datetime
import os

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
        if "401" in str(e) or "Please wait" in str(e):
            print("   🚨 인스타그램이 눈치챘습니다! 2분간 대기합니다...")
            time.sleep(120) 
        return None

def main():
    sheet = connect_google_sheets()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # [설정] 깃허브(앱시트)에서 보낸 타겟 URL 확인
    target_url = os.environ.get('TARGET_URL', '').strip()
    
    if target_url:
        print(f"🚀 [단건 실행 모드] '{target_url}' 계정만 업데이트합니다.")
    else:
        print(f"🔄 [전체/빈칸채우기 모드] ID가 없거나 업데이트가 필요한 항목을 찾습니다.")

    # 1. 데이터를 한 번에 다 가져오기 (속도 최적화)
    col_ids = sheet.col_values(1)    # A열 (ID)
    col_urls = sheet.col_values(4)   # D열 (링크)
    col_dates = sheet.col_values(17) # Q열 (업데이트일) - 본인 시트에 맞게 수정!
    
    # enumerate 시작값 2 (헤더 다음부터)
    for i, url in enumerate(col_urls[1:], start=2):
        if not url or "instagram.com" not in url: continue
        
        # 리스트 범위 오류 방지용 안전장치
        current_id = col_ids[i-1] if len(col_ids) > i-1 else ""
        last_update = col_dates[i-1] if len(col_dates) > i-1 else ""

        # ==================================================
        # [핵심 로직] 실행 여부 결정
        # ==================================================
        
        # 1. 단건 모드: 타겟 URL과 다르면 건너뜀
        if target_url and target_url != url:
            continue
            
        # 2. 전체 모드 (타겟 URL 없음):
        if not target_url:
            # ID가 없으면? -> 실행 (빈칸 채우기)
            if not current_id or current_id == "":
                pass 
            # ID는 있는데 오늘 이미 했다? -> 건너뜀
            elif last_update == today:
                print(f"PASS: {url} (오늘 이미 완료)")
                continue
        # ==================================================

        try:
            username = url.strip().split("instagram.com/")[-1].replace("/", "").split("?")[0]
        except:
            continue
        
        print(f"🔄 {username} 분석 중... (Row {i})")
        data = get_instagram_data(username)
        
        if data:
            # ID 생성 로직 (현재 ID가 없을 때만)
            # 데이터를 다시 읽지 않고, 위에서 읽은 current_id 변수 활용
            if not current_id:
                new_id = f"INF_{i:03d}"
                sheet.update_cell(i, 1, new_id)
                print(f"   ✨ ID 생성: {new_id}")
            
            # 데이터 저장
            sheet.update_cell(i, 2, data['username'])
            sheet.update_cell(i, 3, data['full_name'])
            # D열(링크)은 건드리지 않음
            sheet.update_cell(i, 5, data['profile_pic'])
            sheet.update_cell(i, 6, data['followers'])
            sheet.update_cell(i, 7, data['score'])
            sheet.update_cell(i, 8, data['avg_views'])
            sheet.update_cell(i, 9, data['bio'])
            sheet.update_cell(i, 17, today)
            
            print(f"   ✅ 저장 완료! (점수: {data['score']})")
        
        # 단건 모드라면 여기서 바로 종료
        if target_url:
            print("🚀 단건 업데이트 완료! 프로그램을 종료합니다.")
            break 

        # 전체 모드일 때만 휴식
        wait_time = random.uniform(15, 30)
        print(f"   -> {int(wait_time)}초 휴식...")
        time.sleep(wait_time)

if __name__ == "__main__":
    main()
