import os, json, re
from datetime import timedelta
from functools import lru_cache
from typing import List, Union
from videotrans.configure.config import ROOT_DIR, tr, logger
from videotrans.task.taskcfg import SrtItem
from videotrans.configure import contants

@lru_cache
def process_text_to_srt_str(input_text: str)->str:
    if is_srt_string(input_text):
        return input_text
    # 将文本按换行符切割成列表
    text_lines = [line.strip() for line in input_text.splitlines() if line.strip()]
    # 分割大于50个字符的行
    text_str_list = []
    for line in text_lines:
        if len(line) > 50:
            # 按标点符号分割为多个字符串
            # split_lines = re.split(r'[,.，。]', line)
            split_lines = re.split(r'(?<=[,.，。])', line)
            text_str_list.extend([l.strip() for l in split_lines if l.strip()])
        else:
            text_str_list.append(line)
    # 创建字幕字典对象列表
    dict_list = []
    start_time_in_seconds = 0  # 初始时间，单位秒
    for i, text in enumerate(text_str_list, start=1):
        # 计算开始时间和结束时间（每次增加1s）
        start_time = ms_to_time_string(seconds=start_time_in_seconds)
        end_time = ms_to_time_string(seconds=start_time_in_seconds + 1)
        start_time_in_seconds += 1
        # 创建字幕字典对象
        dict_list.append(f"{i}\n{start_time} --> {end_time}\n{text}")

    return "\n\n".join(dict_list)


# 判断是否是srt字符串
@lru_cache
def is_srt_string(input_text:str)->bool:
    input_text = input_text.strip()
    if not input_text:
        return False

    # 将文本按换行符切割成列表
    text_lines = input_text.splitlines()
    if len(text_lines) < 3:
        return False

    # 正则表达式：第一行应为1到2个纯数字
    first_line_pattern = r'^\d{1,2}$'

    # 正则表达式：第二行符合时间格式
    second_line_pattern = r'^\s*?\d{1,2}:\d{1,2}:\d{1,2}(\W\d+)?\s*-->\s*\d{1,2}:\d{1,2}:\d{1,2}(\W\d+)?\s*$'

    # 如果前两行符合条件，返回原字符串
    if not re.match(first_line_pattern, text_lines[0].strip()) or not re.match(second_line_pattern,
                                                                               text_lines[1].strip()):
        return False
    return True


# 删除翻译结果的特殊字符
@lru_cache
def cleartext(text: str)->str:
    res_text = text.replace('&#39;', "").replace('&quot;', '').replace("\u200b", " ").strip()
    # 删掉连续的多个标点符号，只保留一个
    res_text = re.sub(r'([，。！？,.?]\s?){2,}', ',', res_text, flags=re.I | re.S)
    return res_text


# 删掉常见标点符号
def delete_punc(text):
    # 1. 保护小数点：只匹配那些左右不全是数字的句号
    # 2. 匹配通用的常见标点：, ? / ; : ! 等（包括中英文及多语言）

    pattern = r'[,?/;\':，。？、：；！!“”‘’"()（）]+|(?<!\d)\.|\.(?!\d)'
    # 执行替换
    res = re.sub(pattern, ' ', text)

    # 最后处理一下多余的空格
    return re.sub(r'\s+', ' ', res).strip()

@lru_cache
def ms_to_time_string(*, ms:Union[int,float]=0, seconds:Union[int,None]=None, sepflag:str=',')->str:
    # 计算小时、分钟、秒和毫秒
    if seconds is None:
        td = timedelta(milliseconds=ms)
    else:
        td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000

    return f"{hours:02}:{minutes:02}:{seconds:02}{sepflag}{milliseconds:03}"


# 将不规范的 时:分:秒,|.毫秒格式为  aa:bb:cc,ddd形式
# eg  001:01:2,4500  01:54,14 等做处理
@lru_cache
def format_time(s_time="", separate=',')->str:
    if not s_time.strip():
        return f'00:00:00{separate}000'
    hou, min, sec, ms = 0, 0, 0, 0

    tmp = s_time.strip().split(':')
    if len(tmp) >= 3:
        hou, min, sec = tmp[-3].strip(), tmp[-2].strip(), tmp[-1].strip()
    elif len(tmp) == 2:
        min, sec = tmp[0].strip(), tmp[1].strip()
    elif len(tmp) == 1:
        sec = tmp[0].strip()

    if re.search(r',|\.', str(sec)):
        t = re.split(r',|\.', str(sec))
        sec = t[0].strip()
        ms = t[1].strip()
    else:
        ms = 0
    hou = f'{int(hou):02}'[-2:]
    min = f'{int(min):02}'[-2:]
    sec = f'{int(sec):02}'
    ms = f'{int(ms):03}'[-3:]
    return f"{hou}:{min}:{sec}{separate}{ms}"


def srt_str_to_listdict(srt_string: str) -> List[SrtItem]:
    """解析 SRT 字幕字符串，更精确地处理数字行和时间行之间的关系"""
    srt_list = []
    time_pattern = r'\s?(\d+):(\d+):(\d+)([,.]\d+)?\s*?-{1,2}>\s*?(\d+):(\d+):(\d+)([,.]\d+)?\n?'
    lines = srt_string.splitlines()
    i = 0

    while i < len(lines):
        time_match = re.match(time_pattern, lines[i].strip())
        if time_match:
            # 解析时间戳
            start_time_groups = time_match.groups()[0:4]
            end_time_groups = time_match.groups()[4:8]

            def parse_time(time_groups):
                h, m, s, ms = time_groups
                ms = ms.replace(',', '').replace('.', '') if ms else "0"
                try:
                    return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)
                except (ValueError, TypeError):
                    return None

            start_time = parse_time(start_time_groups)
            end_time = parse_time(end_time_groups)

            if start_time is None or end_time is None:
                i += 1
                continue

            i += 1
            text_lines = []
            while i < len(lines):
                current_line = lines[i].strip()
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""  # 获取下一行，如果没有则为空字符串

                if re.match(time_pattern, next_line):  # 判断下一行是否为时间行
                    if re.fullmatch(r'\d+', current_line):  # 如果当前行为纯数字，则跳过
                        i += 1
                        break
                    else:
                        if current_line:
                            text_lines.append(current_line)
                        i += 1
                        break

                if current_line:
                    text_lines.append(current_line)
                    i += 1
                else:
                    i += 1

            text = ('\n'.join(text_lines)).strip()
            text = re.sub(r'</?[a-zA-Z]+>', '', text.replace("\r", '').strip(), flags=re.I | re.S)
            text = re.sub(r'\n{2,}', '\n', text, flags=re.I | re.S).strip()
            _srtitem = SrtItem(
                line=len(srt_list) + 1,  # 字幕索引，转换为整数
                start_time=int(start_time),
                end_time=int(end_time),  # 起始和结束时间
                text=text if text else "",  # 字幕文本
            )
            _srtitem['startraw'] = ms_to_time_string(ms=_srtitem['start_time'])
            _srtitem['endraw'] = ms_to_time_string(ms=_srtitem['end_time'])
            _srtitem['time'] = f"{_srtitem['startraw']} --> {_srtitem['endraw']}"
            srt_list.append(_srtitem)
        else:
            i += 1  # 跳过非时间行

    return srt_list


# 将srt文件或合法srt字符串转为字典对象
def get_subtitle_from_srt(srtfile, *, is_file=True) -> List[SrtItem]:
    def _readfile(file):
        content = ""
        try:
            with open(file, 'r', encoding='utf-8-sig') as f:
                content = f.read().strip()
        except UnicodeDecodeError:
            try:
                with open(file, 'r', encoding='gbk') as f:
                    content = f.read().strip()
            except UnicodeDecodeError as e:
                logger.exception(e, exc_info=True)
                raise
        except BaseException:
            raise
        return content

    content = _readfile(srtfile) if is_file else srtfile.strip()

    if len(content) < 1:
        raise RuntimeError(
            f"The srt subtitles were not read. The file may be empty or the format does not conform to the SRT specification\n:{srtfile=}\n{content=}")

    try:
        result = srt_str_to_listdict(content)
    except Exception:
        result = srt_str_to_listdict(process_text_to_srt_str(content))

    # txt 文件转为一条字幕
    if len(result) < 1:
        result = [
            SrtItem(
                line=1,
                start_time=0,
                startraw="00:00:00,000",
                end_time=2000,
                endraw="00:00:02,000",
                time="00:00:00,000 --> 00:00:02,000",
                text="\n".join(content)
            )
        ]
    return result


# 从 字幕 对象中获取 srt 字幕串
def get_srt_from_list(srt_list: List[SrtItem]) -> str:
    txt = ""
    line = 0
    # it中可能含有完整时间戳 it['time']   00:00:01,123 --> 00:00:12,345
    # 开始和结束时间戳  it['startraw']=00:00:01,123  it['endraw']=00:00:12,345
    # 开始和结束毫秒数值  it['start_time']=126 it['end_time']=678
    for it in srt_list:
        line += 1
        if "startraw" not in it or not it['startraw']:
            # 存在完整开始和结束时间戳字符串 时:分:秒,毫秒 --> 时:分:秒,毫秒
            if 'time' in it:
                startraw, endraw = it['time'].strip().split(" --> ")
                startraw = format_time(startraw.strip().replace('.', ','), ',')
                endraw = format_time(endraw.strip().replace('.', ','), ',')
            elif 'start_time' in it and 'end_time' in it:
                # 存在开始结束毫秒数值
                startraw = ms_to_time_string(ms=it['start_time'])
                endraw = ms_to_time_string(ms=it['end_time'])
            else:
                raise Exception(
                    tr("There is no time/startraw/start_time in the subtitle in any valid timestamp form."))
        else:
            # 存在单独开始和结束  时:分:秒,毫秒 字符串
            startraw = it['startraw']
            endraw = it['endraw']

        txt += f"{line}\n{startraw} --> {endraw}\n{it['text']}\n\n"
    return txt


def set_ass_font(srtfile: str) -> str:
    from . import help_ffmpeg
    """
    将 SRT 转换为 ASS，并自定义样式：
    - 全局使用主样式（Default）
    - 若字幕文本包含 '###'，则 '###' 后的文本使用副样式（Bottom）
    - 删除 '###'
    """
    if not os.path.exists(srtfile) or os.path.getsize(srtfile) == 0:
        return os.path.basename(srtfile)

    # ---------- 1. 将 SRT 转为临时 SRT（替换换行符）并调用 ffmpeg 生成 ASS ----------
    srt_str = ""
    for it in get_subtitle_from_srt(srtfile, is_file=True):
        text = re.sub(r'\n|\\n', r'\\N', it['text'].strip())
        if text:
            # 舍弃 srt时间格式毫秒中第三位，防止转为ass时四舍五入不一致问题
            _time = f'{it["startraw"]} --> {it["endraw"]}'
            _time = re.sub(r'(\d{2}:\d{2}:\d{2}),(\d{2})\d?', r'\1,\g<2>0', _time)
            srt_str += f'{it["line"]}\n{_time}\n{text}\n\n'
    edit_srt = srtfile[:-4] + '-edit.srt'
    with open(edit_srt, 'w', encoding='utf-8') as f:
        f.write(srt_str.strip())
    ass_file_path = f'{srtfile[:-3]}ass'
    help_ffmpeg.runffmpeg(['-y', '-i', edit_srt, ass_file_path])

    # ---------- 2. 读取 JSON 样式配置 ----------
    JSON_FILE = f'{ROOT_DIR}/videotrans/ass.json'
    if not os.path.exists(JSON_FILE):
        logger.debug(f"[set_ass_font] 未修改硬字幕样式，跳过样式替换")
        return ass_file_path

    try:
        with open(JSON_FILE, 'r', encoding='utf-8-sig') as f:
            style = json.load(f)
    except Exception as e:
        logger.exception(f"[set_ass_font] 错误：无法读取或解析 JSON 文件 {JSON_FILE}: {e}", exc_info=True)
        return ass_file_path

    # ---------- 3. 构建两个 Style 行：Default（主样式）和 Bottom（副样式）----------
    # Helper: apply TextOpacity to ASS PrimaryColour using \alpha override
    def _apply_text_opacity(color_str, opacity):
        """Nếu opacity < 1.0, bọc màu với \alpha&HXX& - dùng cho Dialogue inline"""
        if opacity >= 1.0 or not color_str:
            return color_str
        alpha_hex = hex(int((1.0 - opacity) * 255))[2:].upper().zfill(2)
        return f"{{\\alpha&H{alpha_hex}&}}{color_str}{{\\alpha&H00&}}"

    # Helper: apply BackOpacity to OutlineColour (dùng làm màu nền hộp cho BorderStyle=4)
    def _opacity_color(color_str, opacity):
        """Trả về màu ASS với alpha đã nhân opacity vào kênh A"""
        if opacity >= 1.0 or not color_str or not color_str.startswith('&H'):
            return color_str
        hex_str = color_str[2:-1].upper()
        if len(hex_str) == 6:
            # Thêm kênh alpha
            a = int((1.0 - opacity) * 255)
            return f'&H{a:02X}{hex_str}&'
        elif len(hex_str) == 8:
            orig_a = int(hex_str[0:2], 16)
            new_a = int(orig_a * opacity)
            return f'&H{new_a:02X}{hex_str[2:]}&'
        return color_str

    border_style_num = style.get('BorderStyle', 1)
    text_opacity = style.get('TextOpacity', 1.0)
    back_opacity = style.get('BackOpacity', 0.35)
    use_glow = style.get('UseGlow', False)
    glow_size = style.get('GlowSize', 2.0)
    glow_color_ass = style.get('GlowColor', '&H80000000&')

    # Nếu BorderStyle=4 (glass box), OutlineColour trở thành màu nền hộp (có alpha)
    raw_outline_colour = style.get('OutlineColour', '&H00000000&')
    if border_style_num == 4:
        outline_colour_for_style = _opacity_color(raw_outline_colour, back_opacity)
        # Outline vẽ riêng bằng glow color
        outline_width_for_style = glow_size if use_glow else style.get('Outline', 1)
    else:
        outline_colour_for_style = raw_outline_colour
        outline_width_for_style = style.get('Outline', 1)

    # PrimaryColour với TextOpacity (dùng inline tag khi opacity < 1)
    raw_primary_colour = style.get('PrimaryColour', '&H00FFFFFF&')

    # 主样式属性
    default_style = (
        f"Style: {style.get('Name', 'Default')},"
        f"{style.get('Fontname', 'Arial')},"
        f"{style.get('Fontsize', 16)},"
        f"{raw_primary_colour},"
        f"{style.get('SecondaryColour', '&H00FFFFFF&')},"
        f"{outline_colour_for_style},"
        f"{style.get('BackColour', '&H00000000&')},"
        f"{style.get('Bold', 0)},"
        f"{style.get('Italic', 0)},"
        f"{style.get('Underline', 0)},"
        f"{style.get('StrikeOut', 0)},"
        f"{style.get('ScaleX', 100)},"
        f"{style.get('ScaleY', 100)},"
        f"{style.get('Spacing', 0)},"
        f"{style.get('Angle', 0)},"
        f"{border_style_num},"
        f"{outline_width_for_style},"
        f"{style.get('Shadow', 0)},"
        f"{style.get('Alignment', 2)},"
        f"{style.get('MarginL', 10)},"
        f"{style.get('MarginR', 10)},"
        f"{style.get('MarginV', 10)},"
        f"{style.get('Encoding', 1)}\n"
    )

    # 副样式：继承主样式，但 Fontsize 和 PrimaryColour 使用底部专用值
    bottom_fontsize = style.get('Bottom_Fontsize', 14)
    bottom_color = style.get('Bottom_PrimaryColour', '&H0000FFFF&')
    bottom_bold = style.get('Bottom_Bold', 0)
    bottom_italic = style.get('Bottom_Italic', 0)
    bottom_secondarycolour = style.get('Bottom_SecondaryColour', '&H00FFFFFF&')
    bottom_outlinecolour_raw = style.get('Bottom_OutlineColour', '&H00000000&')
    bottom_backcolour = style.get('Bottom_BackColour', '&H00000000&')
    bottom_back_opacity = style.get('Bottom_BackOpacity', 0.35)
    bottom_use_glow = style.get('Bottom_UseGlow', False)
    bottom_glow_size = style.get('Bottom_GlowSize', 2.0)
    bottom_glow_color_ass = style.get('Bottom_GlowColor', '&H80000000&')

    if border_style_num == 4:
        bottom_outlinecolour = _opacity_color(bottom_outlinecolour_raw, bottom_back_opacity)
        bottom_outline_width = bottom_glow_size if bottom_use_glow else style.get('Outline', 1)
    else:
        bottom_outlinecolour = bottom_outlinecolour_raw
        bottom_outline_width = style.get('Outline', 1)

    bottom_style = (
        f"Style: Bottom,"
        f"{style.get('Fontname', 'Arial')},"
        f"{bottom_fontsize},"
        f"{bottom_color},"
        f"{bottom_secondarycolour},"
        f"{bottom_outlinecolour},"
        f"{bottom_backcolour},"
        f"{bottom_bold},"
        f"{bottom_italic},"
        f"{style.get('Underline', 0)},"
        f"{style.get('StrikeOut', 0)},"
        f"{style.get('ScaleX', 100)},"
        f"{style.get('ScaleY', 100)},"
        f"{style.get('Spacing', 0)},"
        f"{style.get('Angle', 0)},"
        f"{border_style_num},"
        f"{bottom_outline_width},"
        f"{style.get('Shadow', 0)},"
        f"{style.get('Alignment', 2)},"
        f"{style.get('MarginL', 10)},"
        f"{style.get('MarginR', 10)},"
        f"{style.get('MarginV', 10)},"
        f"{style.get('Encoding', 1)}\n"
    )

    # ---------- 4. 读取 ASS 文件并替换 [V4+ Styles] 区块 ----------
    try:
        with open(ass_file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
    except Exception as e:
        logger.exception(f"[set_ass_font] 错误：无法读取 ASS 文件: {e}", exc_info=True)
        return ass_file_path

    # 匹配 [V4+ Styles] 区块，保留 Format 行，替换为两个 Style 行
    pattern = r'(^\[V4\+ Styles\]\s*\r?\n' \
              r'Format:[^\r\n]*\r?\n' \
              r'(?:Style:[^\r\n]*\r?\n)*)' \
              r'(?=\[|$)'

    def replacer(match):
        # 提取原有的 Format 行（如果没有则使用默认格式）
        format_line = None
        for line in match.group(0).splitlines():
            if line.strip().startswith("Format:"):
                format_line = line.strip() + "\n"
                break
        if not format_line:
            format_line = "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        # 返回完整的 [V4+ Styles] 区块，包含 Default 和 Bottom 两个样式
        return f"[V4+ Styles]\n{format_line}{default_style}{bottom_style}"

    try:
        new_content, _ = re.subn(pattern, replacer, content, flags=re.MULTILINE)
    except Exception as e:
        logger.exception(f"[set_ass_font] 错误：正则替换样式失败: {e}", exc_info=True)
        return ass_file_path

    # ---------- 5. 处理 [Events] 中的每一条 Dialogue，对包含 '###' 的行应用副样式 ----------
    lines = new_content.splitlines(keepends=True)
    processed_lines = []
    inside_events = False
    dialogue_pattern = re.compile(r'^(Dialogue:.*?,.*?,.*?,.*?,.*?,.*?,.*?,.*?,.*?,)(.*)$')

    # BackBlur: nếu > 0 và border_style==4, thêm \be tag để làm mềm viền nền hộp (giả lập bo cạnh)
    back_blur = style.get('BackBlur', 0)
    bottom_back_blur = style.get('Bottom_BackBlur', 0)

    for line in lines:
        # 检测是否进入 [Events] 区域
        if line.strip().startswith('[Events]'):
            inside_events = True
        elif line.strip().startswith('[') and inside_events:
            inside_events = False  # 遇到下一个节则退出

        if inside_events and line.startswith('Dialogue:'):
            match = dialogue_pattern.match(line.rstrip('\r\n'))
            if match:
                prefix = match.group(1)  # 前面固定字段
                text = match.group(2)  # 字幕文本内容

                # Thêm \be tag cho nền hộp mờ (chỉ có hiệu ứng với BorderStyle=4)
                blur_tag = ''
                if border_style_num == 4 and back_blur > 0:
                    blur_tag = f'{{\\be{back_blur}}}'
                # Bottom blur tag sẽ được áp trong phần Bottom nếu có ###
                bottom_blur_tag = ''
                if border_style_num == 4 and bottom_back_blur > 0:
                    bottom_blur_tag = f'{{\\be{bottom_back_blur}}}'

                # 检查是否包含 '###'
                if '###' in text:
                    parts = text.split('###', 1)
                    left = parts[0]
                    right = parts[1] if len(parts) > 1 else ''
                    new_text = ''
                    if left:
                        new_text += blur_tag + left
                    if right:
                        new_text += f'{{\\rBottom}}{bottom_blur_tag}{right}{{\\r}}'
                    line = f'{prefix}{new_text}\n'
                else:
                    # Không có ###: thêm blur tag vào đầu dòng
                    if blur_tag:
                        line = f'{prefix}{blur_tag}{text}\n'
            else:
                pass
        processed_lines.append(line)

    # 写回 ASS 文件
    try:
        with open(ass_file_path, 'w', encoding='utf-8', newline='') as f:
            f.writelines(processed_lines)
    except Exception as e:
        logger.exception(f"[set_ass_font] 错误：无法写入 ASS 文件: {e}", exc_info=True)

    return ass_file_path


# 简单换行，不保留换行符，用于视频翻译字幕嵌入
@lru_cache
def simple_wrap(text:str, maxlen:int=15, language:str="en")->str:
    # 标点和空格列表
    flag = [
        ",", ".", "?", "!", ";",
        "，", "。", "？", "；", "！", " "
    ]
    text = re.sub(r"\r?(\n|\\n)", ' ', text, flags=re.I).strip()
    _len = len(text)
    if _len < maxlen + 4:
        return text
    # 如果是中日韩粤语等无需空格的语言
    text_lilst = []
    current_text = ""
    offset = 2 if language[:2] in contants.CJK_LANG else 8
    maxlen = max(3, maxlen)
    offset = min(offset, maxlen // 2)

    i = 0
    while i < _len:
        current_text = current_text.lstrip()
        if i >= _len - offset:
            # 最后不足4个字符，无需区分都给最后一行
            current_text += text[i:]
            break
        if len(current_text) < maxlen - offset:
            current_text += text[i]
            i += 1
            continue
        # 判断 i+1,i+2,i+3,i+4 是否符合标点，
        if maxlen - offset <= len(current_text) <= maxlen and text[i] in flag:
            # 当前是标点，可以换行
            current_text += text[i]
            i += 1
            text_lilst.append(current_text)
            current_text = ''
            continue
        # 再判断后续4个是否符合换行条件
        raw_i = i
        for next_i in range(1, offset + 1):
            if i+next_i>=_len:
                break
            if text[i + next_i] in flag:
                pos_i = i + next_i + 1
                current_text += text[i:pos_i]
                raw_i = pos_i

                text_lilst.append(current_text)
                current_text = ''
                break
        if raw_i != i:
            i = raw_i
            continue
        # 没有找到合适标点换行，强制换行
        current_text += text[i]
        if len(current_text) >= maxlen:
            text_lilst.append(current_text)
            current_text = ''
        i += 1

    if current_text and len(current_text) < maxlen / 3 and text_lilst:
        text_lilst[-1] += current_text
    elif current_text:
        text_lilst.append(current_text)
    return ("\n".join(text_lilst)).strip()
