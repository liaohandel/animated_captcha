from PIL import Image, ImageDraw, ImageFont
import random
import string
import os
import shutil
import sys
from collections import defaultdict

# --- 設定參數 ---
IMAGE_SIZE = (800, 800)
BALL_PADDING = 20
FONT_SIZE_RATIO = 0.6

# 顏色定義
NORMAL_BALL_FILL = (70, 130, 180)
NORMAL_BALL_OUTLINE = (255, 255, 255)
NORMAL_TEXT_FILL = (255, 255, 255)
FLASH_BALL_FILL = (255, 255, 255)
FLASH_BALL_OUTLINE = (0, 0, 0)
FLASH_TEXT_FILL = (0, 0, 0)
RED_COLOR = (255, 0, 0)
SRED_COLOR = (165, 0, 0) # 深紅色，用於混淆文字

# 動畫時間定義 (毫秒)
INITIAL_PAUSE_MS = 500
SEQ_FLASH_ON_MS = 1000
SEQ_FLASH_OFF_MS = 500
ALL_FLASH_ON_MS = 500
ALL_FLASH_OFF_MS = 500
FINAL_PAUSE_MS = 200

# 干擾效果參數
ASPECT_RATIO_RANGE = (0.7, 1.4)
ROTATION_ANGLE_RANGE = (-40, 40)
NUM_NOISE_LINES_RANGE = (4, 7)
NOISE_LINE_WIDTH = 3
NOISE_DENSITY = 0.008
NOISE_BLOCK_SIZE = 4

# 背景相關參數
BG_IMAGE_DIR = "bg_image"
BACKGROUND_NOISE_DENSITY = 0.05

# 臨時資料夾
TEMP_FRAMES_DIR = "temp_char_animation_frames"


# --- 輔助函數 (與原碼一致) ---

def create_background_image(mode, size):
    if mode == 0:
        return Image.new('RGB', size, color=(0, 0, 0))
    if mode == 1:
        bg_img = Image.new('RGB', size, color=(0, 0, 0))
        draw = ImageDraw.Draw(bg_img)
        num_noise_blocks = int(size[0] * size[1] * BACKGROUND_NOISE_DENSITY)
        for _ in range(num_noise_blocks):
            x, y = random.randint(0, size[0] - NOISE_BLOCK_SIZE), random.randint(0, size[1] - NOISE_BLOCK_SIZE)
            color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
            draw.rectangle((x, y, x + NOISE_BLOCK_SIZE, y + NOISE_BLOCK_SIZE), fill=color)
        return bg_img
    if mode == 2:
        # 以絕對路徑定位 bg_image (位於本腳本所在的 static/ 目錄內)
        full_bg_image_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), BG_IMAGE_DIR)
        if not os.path.isdir(full_bg_image_dir):
            print(f"警告：找不到背景圖資料夾 '{full_bg_image_dir}'。將使用純黑背景。", file=sys.stderr)
            return create_background_image(0, size)
        logo_files = [f for f in os.listdir(full_bg_image_dir) if f.startswith('logo') and f.endswith(('.png', '.jpg', '.jpeg'))]
        if not logo_files:
            print(f"警告：在 '{full_bg_image_dir}' 中找不到 logo 圖檔。將使用純黑背景。", file=sys.stderr)
            return create_background_image(0, size)
        chosen_logo_path = os.path.join(full_bg_image_dir, random.choice(logo_files))
        try:
            logo_img = Image.open(chosen_logo_path)
        except IOError:
            print(f"警告：無法開啟圖片 '{chosen_logo_path}'。將使用純黑背景。", file=sys.stderr)
            return create_background_image(0, size)
        bg_img = Image.new('RGB', size, color=(0, 0, 0))
        logo_img.thumbnail((size[0] * 0.8, size[1] * 0.8), Image.LANCZOS)
        paste_x, paste_y = (size[0] - logo_img.width) // 2, (size[1] - logo_img.height) // 2
        if logo_img.mode == 'RGBA':
            bg_img.paste(logo_img, (paste_x, paste_y), logo_img)
        else:
            bg_img.paste(logo_img, (paste_x, paste_y))
        return bg_img
    return create_background_image(0, size)

def get_font(ball_diameter, font_size_ratio):
    font_size = int(ball_diameter * font_size_ratio)
    font_candidates = [
        "arial.ttf",                                    # Windows
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Ubuntu/Debian
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",  # CentOS/RHEL
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",    # Arch Linux
        "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",  # Fedora
    ]
    for font_path in font_candidates:
        try:
            return ImageFont.truetype(font_path, font_size)
        except (IOError, OSError):
            continue
    print("警告：找不到任何已知字體，將使用預設字體。", file=sys.stderr)
    return ImageFont.load_default()

def draw_single_ball(canvas_img, draw_obj, char_info, font, is_flashed=False, color_mode="normal", font_mode=0, showtype=0):
    char, cx, cy, radius = char_info
    
    # 決定球體和文字的顏色
    if color_mode == "red": # Phase 1 密碼球 (閃紅)
        ball_fill, ball_outline, text_fill = RED_COLOR, RED_COLOR, (0, 0, 0)
    elif color_mode == "null": # Phase 1 混淆球
        ball_fill, ball_outline, text_fill = RED_COLOR, RED_COLOR, SRED_COLOR
    elif is_flashed: # Phase 2 同時閃動 (閃白)
        ball_fill, ball_outline, text_fill = FLASH_BALL_FILL, FLASH_BALL_OUTLINE, FLASH_TEXT_FILL
    else: # 正常狀態 (藍球)
        ball_fill, ball_outline, text_fill = NORMAL_BALL_FILL, NORMAL_BALL_OUTLINE, NORMAL_TEXT_FILL
    
    # 繪製圓形球體
    draw_obj.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=ball_fill, outline=ball_outline, width=3)
    
    # 繪製字符 (省略細節，與原碼一致)
    if font_mode == 0:
        try:
            bbox = draw_obj.textbbox((0, 0), char, font=font)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            text_w, text_h = draw_obj.textsize(char, font=font)
        text_x, text_y = cx - text_w // 2, cy - text_h // 2
        draw_obj.text((text_x, text_y), char, fill=text_fill, font=font)
    elif font_mode >= 1:
        try:
            bbox = font.getbbox(char)
            char_w, char_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            padding = 20
            temp_size = (char_w + padding, char_h + padding)
            char_img = Image.new('RGBA', temp_size)
            char_draw = ImageDraw.Draw(char_img)
            
            char_draw.text((padding/2 - bbox[0], padding/2 - bbox[1]), char, font=font, fill=text_fill) 
            
        except Exception:
            char_img = Image.new('RGBA', (50, 50), (255, 255, 255, 0))
            char_draw = ImageDraw.Draw(char_img)
            char_draw.text((10, 10), char, font=font, fill=text_fill)
        
        w, h = char_img.size
        scale_w, scale_h = random.uniform(*ASPECT_RATIO_RANGE), random.uniform(*ASPECT_RATIO_RANGE)
        new_w, new_h = int(w * scale_w), int(h * scale_h)
        deformed_img = char_img.resize((new_w, new_h), resample=Image.BILINEAR)
        
        angle = random.randint(*ROTATION_ANGLE_RANGE)
        final_char_img = deformed_img.rotate(angle, resample=Image.BILINEAR, expand=True)

        paste_x, paste_y = cx - final_char_img.width // 2, cy - final_char_img.height // 2
        canvas_img.paste(final_char_img, (paste_x, paste_y), mask=final_char_img)

    # 繪製雜訊線條和雜訊塊
    if font_mode == 2:
        # 繪製雜訊線條
        for _ in range(random.randint(*NUM_NOISE_LINES_RANGE)):
            points = []
            for _ in range(2):
                while True:
                    px, py = random.randint(int(cx - radius), int(cx + radius)), random.randint(int(cy - radius), int(cy + radius))
                    if (px - cx)**2 + (py - cy)**2 <= radius**2:
                        points.append((px, py)); break
            draw_obj.line(points, fill=(random.randint(0,255), random.randint(0,255), random.randint(0,255)), width=NOISE_LINE_WIDTH)
        # 繪製雜訊塊
        for _ in range(int((radius*2)**2 * NOISE_DENSITY)):
            nx, ny = random.randint(int(cx - radius), int(cx + radius - NOISE_BLOCK_SIZE)), random.randint(int(cy - radius), int(cy + radius - NOISE_BLOCK_SIZE))
            if (nx + NOISE_BLOCK_SIZE/2 - cx)**2 + (ny + NOISE_BLOCK_SIZE/2 - cy)**2 <= radius**2:
                draw_obj.rectangle((nx, ny, nx + NOISE_BLOCK_SIZE, ny + NOISE_BLOCK_SIZE), fill=(random.randint(0,255), random.randint(0,255), random.randint(0,255)))

# --- 核心修正部分：新增 draw_captcha_frame ---

def draw_captcha_frame(background_img, char_tab_data, font, font_mode=0, showtype=0, 
                       flashing_passwords_indices=None, distracting_indices=None, all_flash=False):
    """
    從頭繪製一幀圖像，考慮所有球體的狀態和正確的遮蔽順序 (由 char_tab_data 的順序決定)。
    這確保了在 showtype=1 (隨機重疊) 模式下，閃動的球不會覆蓋掉遮蔽它的球體，從而保持遮蔽效果。
    """
    if flashing_passwords_indices is None:
        flashing_passwords_indices = set()
    if distracting_indices is None:
        distracting_indices = set()
        
    img = background_img.copy()
    draw = ImageDraw.Draw(img)
    
    # 依序繪製所有球體，以確保正確的遮蔽效果 (繪製順序即為深度順序)
    for i, char_info in enumerate(char_tab_data):
        
        is_flashed = False
        color_mode = "normal"

        if all_flash:
            # Phase 2: 同時閃動 (白色球/黑色文字)
            if i in flashing_passwords_indices:
                is_flashed = True
        elif i in distracting_indices:
            # Phase 1: 序列閃動中的混淆球 (SRED 邊框/文字)
            color_mode = "null"
        elif i in flashing_passwords_indices:
            # Phase 1: 序列閃動中的密碼球 (紅色球/黑色文字)
            color_mode = "red"
        
        # 使用計算出的狀態繪製單個球體
        draw_single_ball(img, draw, char_info, font, is_flashed=is_flashed, color_mode=color_mode, font_mode=font_mode, showtype=showtype)
        
    return img

def create_base_grid_image(background_img, char_tab_data, font, font_mode=0, showtype=0):
    # 基礎狀態 (所有球都是 normal) - 使用新函數
    return draw_captcha_frame(background_img, char_tab_data, font, font_mode, showtype)

# --- 主要生成函數 (已修改) ---

def generate_animated_char_array_gif(rc_mode, password_str, num_distractors_input, font_mode, background_mode, flash_mode, showtype):
    if rc_mode in [3, 4, 5, 6]:
        ROWS, COLS = rc_mode, rc_mode
    else:
        print(f"警告：無效的 rc_mode '{rc_mode}'，將使用預設 5x5。")
        ROWS, COLS = 5, 5

    #os.makedirs(TEMP_FRAMES_DIR, exist_ok=True)
        # *** 關鍵部分：指定 GIF 轉存目錄 ***
    # os.path.dirname(os.path.abspath(__file__)) 是 active_keyx29web.py 所在的目錄 (即 static/)
    # 向上一個目錄 (your_flask_app/)，然後再進入 static/passwd_lib/
    flask_app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_base_dir = os.path.join(flask_app_root, 'static', 'passwd_lib')
    temp_frames_full_path = os.path.join(flask_app_root, TEMP_FRAMES_DIR) # 臨時資料夾也應在根目錄下或可訪問

    os.makedirs(output_base_dir, exist_ok=True) # 確保 GIF 輸出目錄存在
    os.makedirs(temp_frames_full_path, exist_ok=True) # 確保臨時資料夾存在
    
    
    # 計算理論上的球體大小
    available_width = IMAGE_SIZE[0] - (COLS + 1) * BALL_PADDING
    available_height = IMAGE_SIZE[1] - (ROWS + 1) * BALL_PADDING
    ball_diameter = min(available_width // COLS, available_height // ROWS)
    ball_radius = ball_diameter // 2
    font = get_font(ball_diameter, FONT_SIZE_RATIO)

    password_chars = list(password_str)
    alphabet_set = set(string.ascii_uppercase)
    allowed_for_fillers = list(alphabet_set - set(password_chars))
    if not allowed_for_fillers:
        allowed_for_fillers = list(string.ascii_uppercase)
    num_fillers_needed = ROWS * COLS - len(password_chars)
    if num_fillers_needed < 0:
        print(f"錯誤：密碼長度 ({len(password_chars)}) 對於 {ROWS}x{COLS} 的陣列而言過長。")
        sys.exit(1)
    filler_chars = random.choices(allowed_for_fillers, k=num_fillers_needed)
    all_chars = password_chars + filler_chars
    random.shuffle(all_chars) # 隨機打亂，用於隨機深度 (showtype=1)

    char_tab = []
    char_locations = defaultdict(list)
    
    # --- 定位邏輯變更 ---
    if showtype == 0: # 規則網格排列 
        for i, char in enumerate(all_chars):
            r, c = i // COLS, i % COLS
            cx = BALL_PADDING + c * (ball_diameter + BALL_PADDING) + ball_radius
            cy = BALL_PADDING + r * (ball_diameter + BALL_PADDING) + ball_radius
            info = (char, cx, cy, ball_radius)
            char_tab.append(info)
            char_locations[char].append({'index': i, 'info': info})

    elif showtype == 1: # 隨機散佈重疊 (包含 50% 遮蔽限制)
        placed_centers = [] 
        min_center_distance_sq = (ball_radius * 1.3)**2 
        max_attempts = 100 

        for i, char in enumerate(all_chars):
            attempts = 0
            is_valid_placement = False
            
            while not is_valid_placement and attempts < max_attempts:
                attempts += 1
                
                cx = random.randint(ball_radius, IMAGE_SIZE[0] - ball_radius)
                cy = random.randint(ball_radius, IMAGE_SIZE[1] - ball_radius)
                
                is_valid_placement = True
                
                for old_cx, old_cy in placed_centers:
                    distance_sq = (cx - old_cx)**2 + (cy - old_cy)**2
                    
                    if distance_sq < min_center_distance_sq:
                        is_valid_placement = False
                        break
            
            if not is_valid_placement:
                # 警告：字符隨機定位嘗試失敗過多，使用強制定位。
                cx = random.randint(ball_radius, IMAGE_SIZE[0] - ball_radius)
                cy = random.randint(ball_radius, IMAGE_SIZE[1] - ball_radius)

            placed_centers.append((cx, cy))
            
            info = (char, cx, cy, ball_radius) 
            char_tab.append(info)
            char_locations[char].append({'index': i, 'info': info})
    
    # 確定密碼球的位置和序列
    passwd_balls = []
    passwd_indices_set = set()
    temp_locs = {k: v[:] for k, v in char_locations.items()}
    for char in password_str:
        if not temp_locs.get(char):
            print(f"錯誤：邏輯錯誤，找不到密碼字元 '{char}' 的位置。")
            sys.exit(1)
        loc = temp_locs[char].pop(0)
        passwd_balls.append(loc['info'])
        passwd_indices_set.add(loc['index'])
        
    # --- 關鍵修正開始：使用新的 draw_captcha_frame ---

    background_img = create_background_image(background_mode, IMAGE_SIZE)
    # base_img 仍用於 OFF 幀和初始化
    base_img = create_base_grid_image(background_img, char_tab, font, font_mode, showtype)
    
    gif_frames = [(base_img.copy(), INITIAL_PAUSE_MS)]
    
    non_passwd_ids = list(set(range(len(char_tab))) - passwd_indices_set)
    
    print("\nPhase 1: 依序閃動 (已修正遮蔽問題)...")
    if flash_mode == 0: # 單點依序閃動
        for p_ball_info in passwd_balls:
            current_passwd_index = char_tab.index(p_ball_info) # 找到該球在 char_tab 中的索引
            
            # 決定混淆球
            distract_ids = random.sample(non_passwd_ids, k=min(num_distractors_input, len(non_passwd_ids)))
            
            # On Frame: 只有當前球閃紅
            flashing_set = {current_passwd_index}
            img_flash = draw_captcha_frame(background_img, char_tab, font, font_mode, showtype, 
                                           flashing_passwords_indices=flashing_set, 
                                           distracting_indices=set(distract_ids))
            
            gif_frames.append((img_flash, SEQ_FLASH_ON_MS))
            
            # Off Frame (使用 base_img 保持遮蔽效果)
            gif_frames.append((base_img.copy(), SEQ_FLASH_OFF_MS)) 

    elif flash_mode == 1: # 接龍依序閃動
        lit_passwd_indices = set()
        for p_ball_info in passwd_balls:
            current_passwd_index = char_tab.index(p_ball_info)
            lit_passwd_indices.add(current_passwd_index) # 加入已點亮的集合
            
            # 決定混淆球
            distract_ids = random.sample(non_passwd_ids, k=min(num_distractors_input, len(non_passwd_ids)))
            
            # On Frame: 所有 lit_passwd_indices 中的球都閃紅
            img_flash = draw_captcha_frame(background_img, char_tab, font, font_mode, showtype, 
                                           flashing_passwords_indices=lit_passwd_indices, 
                                           distracting_indices=set(distract_ids))
            
            gif_frames.append((img_flash, SEQ_FLASH_ON_MS))
            # 註：接龍模式不包含 Off Frame

    print("Phase 2: 同時閃動 (已修正遮蔽問題)...")
    # 收集所有密碼球的索引
    all_passwd_indices = {char_tab.index(p) for p in passwd_balls}
    
    for _ in range(3):
        # All ON Frame (is_flashed=True)
        img_all_on = draw_captcha_frame(background_img, char_tab, font, font_mode, showtype, 
                                        flashing_passwords_indices=all_passwd_indices, 
                                        all_flash=True) # all_flash=True 觸發白色閃動
        gif_frames.append((img_all_on, ALL_FLASH_ON_MS))
        
        # All OFF Frame
        gif_frames.append((base_img.copy(), ALL_FLASH_OFF_MS))

    gif_frames.append((base_img.copy(), FINAL_PAUSE_MS))

    # --- 更新檔名 ---
    password_str = "".join(password_chars) # 確保檔名中的密碼是正確的
    #output_filename = f"act-{password_str}-rc{rc_mode}-fm{font_mode}-bg{background_mode}-fl{flash_mode}-sh{showtype}.gif"
    #full_output_path = os.path.join(output_base_dir, output_filename_only)
    numdis = num_distractors_input
    # 更新檔名以包含 flash_mode，並儲存到正確的 output_base_dir
    output_filename_only = f"act-ac{rc_mode}-pw{password_str}-di{numdis}-fm{font_mode}-bg{background_mode}-fl{flash_mode}-sh{showtype}.gif"
    full_output_path = os.path.join(output_base_dir, output_filename_only)
    
    
    frames, durations = zip(*gif_frames)
    # PIL 的 save 函數 — 存到 captcha_gui/static/passwd_lib/<output_filename_only>
    frames[0].save(full_output_path, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)
    print(f"\nGIF 動畫生成完成！ -> {full_output_path}", file=sys.stderr)
    shutil.rmtree(temp_frames_full_path, ignore_errors=True) # 清理臨時資料夾
    # 回傳給 app.py 的是相對於 static/ 的路徑
    return f"passwd_lib/{output_filename_only}" 
    
def main():
    # --- 參數數量檢查 ---
    if len(sys.argv) != 8:
        print("用法: python <腳本名> <陣列模式> <密碼> <干擾數> <字體模式> <背景模式> <閃動模式> <顯示模式>")
        print("1 陣列模式: 3 (3x3), 4 (4x4), 5 (5x5), 6 (6x6)") 
        print("2 密碼: passwd string ABCD　")
        print("3 干擾數: 0,1,2 ")
        print("4 字體模式: 0(常規), 1(變形旋轉), 2(變形旋轉+線條+雜訊塊)")
        print("5 背景模式: 0(純黑), 1(雜訊亮點), 2(隨機Logo圖)")
        print("6 閃動模式: 0(單點依序), 1(接龍依序)")
        print("7 顯示模式: 0(規則圓球陣列), 1(隨機重疊圓球(限制遮蔽率))") # 更新說明 showtype
        print("ext:  python active_keyx105web.py 3 ABCD 2 2 1 1 1 ")
        sys.exit(1)

    rc_mode_str, password, distractor_count_str, font_mode_str, background_mode_str, flash_mode_str, showtype_str = sys.argv[1:8]

    try:
        rc_mode = int(rc_mode_str)
        if rc_mode not in [3, 4, 5, 6]: raise ValueError("陣列模式錯誤")
        
        if not (3 <= len(password) <= 8 and password.isalpha() and password.isupper()):
            raise ValueError("密碼格式錯誤")
        
        distractor_count = int(distractor_count_str)
        if not (0 <= distractor_count <= 4): raise ValueError("干擾數錯誤")
        
        font_mode = int(font_mode_str)
        if font_mode not in [0, 1, 2]: raise ValueError("字體模式錯誤")
        
        background_mode = int(background_mode_str)
        if background_mode not in [0, 1, 2]: raise ValueError("背景模式錯誤")

        flash_mode = int(flash_mode_str)
        if flash_mode not in [0, 1]: raise ValueError("閃動模式錯誤")

        showtype = int(showtype_str)
        if showtype not in [0, 1]: raise ValueError("顯示模式錯誤")

    except ValueError as e:
        print(f"錯誤：參數無效。請檢查您的輸入。({e})", file=sys.stderr)
        sys.exit(1)

    generated_filename = generate_animated_char_array_gif(rc_mode, password, distractor_count, font_mode, background_mode, flash_mode, showtype)
    print(generated_filename, file=sys.stdout)  # 只將檔名列印到 stdout
    return generated_filename

if __name__ == "__main__":
    main()
