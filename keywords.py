"""
Phan tich TU KHOA CANVA cho tung canh tu loi doc.

Nguyen tac de tu khoa "sat va chinh xac" khi tim tren Canva:
- Canva tim tot nhat bang CUM DANH TU HINH ANH: [Chu the] + [Hanh dong/Hoat dong] + [Boi canh]
  vi du: "nguoi cao tuoi do huyet ap tai nha" - chu khong tim bang ca cau loi doc.
- Uu tien khai niem CU THE nhat xuat hien trong cau (do huyet ap > thuoc > suc khoe).
- Cau mo dau / cau noi chung chung khong co hinh anh cu the -> dung TU KHOA MAC DINH cua kenh.
- Moi canh co kem ban tieng Anh: tim tren Canva bang tieng Anh thuong ra nhieu anh/video dep hon.

v1.3 - hoc tu bang 19 canh mon muop da sua tay (1_Canva.srt, 2026-11-23):
- Them tu dien MON AN / NAU NUONG: ten mon, dong tac nau (ham, xao, hap, nau chung)
  va nguyen lieu (muop, xuong ong, me ga, trung ga, lac/dau phong, gung hanh tim).
- Sua loi nham nguy hiem: "xuong ong / ham xuong" (nau canh xuong) KHONG duoc roi ve
  "dau xuong khop" (benh xuong khop). Hai nghia cua chu "xuong" phai tach rieng.
- Ten mon dang "Mon N: Ten mon" duoc uu tien cao nhat: tu khoa chinh la chinh ten mon do.
- Gom canh theo y tron ven (xem merge_scenes trong app.py), khong phai theo manh phu de.
"""

import re

# (cum tu nhan dien trong loi doc, tu khoa VN, tu khoa EN) - xep tu CU THE den chung chung.
# {s} = chu the cua kenh (mac dinh: nguoi cao tuoi), {se} = chu the tieng Anh.
CONCEPTS = [
    # --- MON AN / NAU NUONG (v1.3): dong tac + nguyen lieu cu the thang trieu chung ---
    (["mướp hầm xương ống", "canh mướp hầm xương"], "nồi canh mướp hầm xương bốc khói", "luffa soup with pork bones steaming bowl", 13),
    (["mướp xào mề gà", "xào mề gà"], "mướp xào mề gà trên chảo", "stir fry luffa vegetable wok close up", 13),
    (["chén sứ hấp", "hấp 10 phút", "trứng hấp", "hấp trứng"], "hấp trứng trong nồi hấp", "steaming egg custard bowl kitchen", 13),
    (["mướp hấp trứng", "hấp trứng gà"], "hấp trứng trong nồi hấp", "steaming egg custard bowl kitchen", 13),
    (["mướp nấu lạc", "mướp nấu với lạc", "mướp nấu đậu phộng", "nấu với lạc", "nấu với đậu phộng"], "đậu phộng lạc khô cận cảnh", "peanuts and luffa soup cooking", 12),
    (["nấu chung", "lạc ngâm"], "nồi canh mướp đậu phộng nấu chung", "cooking luffa peanut soup pot", 12),
    (["hầm xương", "hầm 45 phút", "xương chần", "xương ống hầm"], "hầm xương bằng nồi trên bếp", "simmering bone broth pot ginger", 12),
    (["xương ống"], "xương ống hầm trong nồi", "pork bone broth pot cooking close up", 12),
    (["trứng gà"], "trứng gà và quả mướp trên bàn", "steamed egg with luffa dish", 12),
    (["món ăn đại bổ", "món ăn từ quả mướp", "sáu món ăn", "sáu món"], "nấu ăn với quả mướp trong bếp", "cooking luffa vegetable in kitchen", 11),
    (["đầy bụng", "khó tiêu"], "{s} bị đầy bụng khó tiêu", "{se} stomach ache digestion problem", 10),
    (["bữa cơm"], "bữa cơm gia đình có rau xanh", "elderly woman eating healthy meal smiling", 9),
    (["ăn uống lành mạnh"], "{s} ăn uống lành mạnh tại nhà", "elderly couple healthy eating at home", 8),
    (["da hồng hào", "da sáng", "làm đẹp da"], "{s} da hồng hào khỏe mạnh", "healthy elderly woman glowing skin smiling", 8),
    (["đo huyết áp"], "{s} đo huyết áp tại nhà", "{se} measuring blood pressure at home", 10),
    (["huyết áp"], "{s} đo huyết áp tại nhà", "{se} blood pressure check", 6),
    (["đường huyết", "tiểu đường", "đái tháo đường"], "{s} đo đường huyết", "{se} blood sugar test diabetes", 9),
    (["mỡ máu", "cholesterol"], "xét nghiệm mỡ máu", "cholesterol blood test", 9),
    (["đo nhịp tim", "nhịp tim"], "{s} đo nhịp tim", "{se} heart rate check", 9),
    (["tập thể dục", "thể dục buổi sáng", "vận động buổi sáng"], "{s} tập thể dục buổi sáng", "{se} morning exercise", 9),
    (["tập yoga", "yoga"], "{s} tập yoga tại nhà", "{se} yoga at home", 9),
    (["đi bộ"], "{s} đi bộ trong công viên", "{se} walking in the park", 9),
    (["tập thở", "hít thở", "thở sâu"], "{s} tập thở sâu", "{se} deep breathing exercise", 9),
    (["ngâm chân"], "{s} ngâm chân nước ấm", "{se} warm foot soak", 8),
    (["xoa bóp", "mát xa", "massage"], "xoa bóp thư giãn cho {s}", "relaxing massage for {se}", 8),
    (["uống thuốc"], "{s} uống thuốc đúng giờ", "{se} taking medicine on time", 8),
    (["hộp thuốc", "chia thuốc"], "{s} chia thuốc vào hộp thuốc", "{se} pill organizer medicine", 8),
    (["khám bệnh", "đi khám", "tái khám"], "bác sĩ khám bệnh cho {s}", "doctor examining {se} patient", 9),
    (["bệnh viện"], "{s} ở bệnh viện", "{se} at the hospital", 6),
    (["bác sĩ"], "bác sĩ tư vấn sức khỏe cho {s}", "doctor health consultation {se}", 5),
    (["xương khớp", "đau khớp", "khớp gối", "thoái hóa khớp"], "{s} bị đau xương khớp", "{se} joint pain", 6),
    (["đau lưng"], "{s} bị đau lưng", "{se} back pain", 7),
    (["đau đầu"], "{s} bị đau đầu", "{se} headache", 7),
    (["tim mạch", "đau tim", "nhồi máu", "đột quỵ", "tai biến"], "{s} tim mạch khỏe mạnh", "elderly heart health blood pressure check", 8),
    (["mất ngủ", "ngủ ngon", "giấc ngủ", "đi ngủ", "ngủ sâu"], "{s} ngủ ngon sâu giấc", "{se} sleeping well", 8),
    (["bữa ăn", "ăn uống", "dinh dưỡng", "khẩu phần ăn"], "bữa ăn dinh dưỡng cho {s}", "healthy nutritious meal for {se}", 7),
    (["rau xanh", "rau củ", "ăn rau"], "rau xanh tươi sạch", "fresh green vegetables", 8),
    (["trái cây", "hoa quả"], "trái cây tươi nhiều màu", "fresh colorful fruits", 8),
    (["uống nước"], "{s} uống nước mỗi ngày", "{se} drinking a glass of water", 8),
    (["uống trà", "tách trà", "ấm trà"], "{s} uống trà thư giãn", "{se} drinking tea relaxing", 7),
    (["vitamin", "thực phẩm bổ sung"], "vitamin và thực phẩm bổ sung", "vitamins and supplements", 8),
    # "thuoc bo" de thap: hay xuat hien trong thanh ngu ("thuoc bo khong bang an dung")
    # hoac cau canh bao, khong phai hinh anh chinh cua canh.
    (["thuốc bổ"], "vitamin và thực phẩm bổ sung", "vitamins and supplements", 5),
    (["trí nhớ", "hay quên", "não bộ", "sa sút trí tuệ"], "{s} rèn luyện trí nhớ", "{se} memory training brain exercise", 8),
    (["khám mắt", "thị lực", "đeo kính", "mắt mờ"], "{s} đi khám mắt", "{se} eye exam", 8),
    (["đọc sách", "đọc báo"], "{s} đọc sách tại nhà", "{se} reading a book at home", 8),
    (["con cháu", "gia đình"], "gia đình quây quần bên {s}", "happy family gathering with {se}", 7),
    (["giảm cân", "cân nặng", "béo phì"], "{s} kiểm soát cân nặng", "{se} weight control", 7),
    (["tắm nắng"], "{s} tắm nắng buổi sáng", "{se} morning sunbathing", 8),
    (["chăm sóc sức khỏe", "sống khỏe", "sức khỏe mỗi ngày", "khỏe mạnh"], "chăm sóc sức khỏe {s}", "{se} healthy lifestyle care", 3),
    (["sinh hoạt"], "{s} sinh hoạt tại nhà", "{se} daily life at home", 3),
    (["thuốc"], "{s} và thuốc uống hằng ngày", "{se} daily medicine pills", 4),
    (["tập luyện", "vận động"], "{s} vận động nhẹ nhàng", "{se} gentle exercise", 6),
    (["ăn sáng", "bữa sáng"], "bữa sáng lành mạnh cho {s}", "healthy breakfast for {se}", 7),
    (["siêu thị", "đi chợ", "mua sắm"], "{s} đi chợ mua thực phẩm", "{se} grocery shopping", 8),
    # "muop" de o muc thap: no chi la nguyen lieu chung, trieu chung / mon cu the thang no.
    # Vi du canh 10 noi "cho muop vao nau" nhung y chinh la "ngu ngon" -> phai ra tu khoa giac ngu.
    (["mướp", "quả mướp"], "quả mướp tươi ở chợ quê", "fresh luffa gourd vegetable market close up", 7),
]

SUBJECTS = [
    (["trẻ em", "bé ", "em bé"], "trẻ em", "children"),
    (["bà bầu", "mang thai", "thai phụ"], "phụ nữ mang thai", "pregnant woman"),
]

# Ten mon dang "Mon N: Ten mon ..." -> tu khoa chinh cua mon do.
# Thu tu: cum dai / cu the truoc.
DISHES = [
    ("canh mướp hầm xương", "nồi canh mướp hầm xương bốc khói", "luffa soup with pork bones steaming bowl"),
    ("mướp hầm xương", "nồi canh mướp hầm xương bốc khói", "luffa soup with pork bones steaming bowl"),
    ("mướp xào mề gà", "mướp xào mề gà trên chảo", "stir fry luffa vegetable wok close up"),
    ("mướp hấp trứng", "trứng gà và quả mướp trên bàn", "steamed egg with luffa dish"),
    ("mướp nấu", "đậu phộng lạc khô cận cảnh", "peanuts and luffa soup cooking"),
]

COOKING_MARKERS = ["hầm", "xào", "hấp", "nấu", "canh", "cách làm", "cách nấu",
                    "cách chế biến", "chuẩn bị", "nêm", "chần", "gọt vỏ", "cắt lát",
                    "sơ chế", "phi hành", "đảo nhanh"]


def _dish_keyword(text: str):
    """Tim 'Mon N: Ten mon' trong loi doc, tra (vn, en) neu nhan ra mon, None neu khong."""
    m = re.search(r"món\s*\d+\s*:\s*([^—.\n]+)", text, re.IGNORECASE)
    if not m:
        return None
    dish = m.group(1).strip().lower()
    for phrase, vn, en in DISHES:
        if phrase in dish:
            return vn, en
    # Mon la nhung khong co trong bang: dung chinh ten mon lam tu khoa VN,
    # tieng Anh dung cum nau an chung de van tim duoc video.
    return dish, "vietnamese home cooking dish"


def _context_keyword(t: str, subject_vn: str, subject_en: str):
    """Cac truong hop can nhin ca ngu canh, khong chi 1 cum tu.
    Tra (vn, en) hoac None."""
    # "Me ga" chi la canh nau khi cau co dong tac nau (rua, xao, phi hanh...).
    # Neu cau chi giai thich cong dung (Dong y, vi thuoc, day bung) thi khong phai
    # canh nau - de trieu chung thang. (Bang muop canh 12 vs canh 13.)
    if "mề gà" in t or "kê nội kim" in t:
        if any(mk in t for mk in COOKING_MARKERS):
            return ("sơ chế mề gà trong bếp", "cooking chicken gizzard stir fry")
    # "Da hong hao" la loi ich / ket qua thay duoc cua mon an, thang menh de canh bao
    # ("nguoi bi gout hoac mo mau cao nen han che...") o cung canh. (Bang muop canh 14.)
    if "da hồng hào" in t:
        return ("người cao tuổi da hồng hào khỏe mạnh",
                "healthy elderly woman glowing skin smiling")
    # Day bung / kho tieu thang "xuong khop / gan cot" khi ca hai cung xuat hien.
    if "đầy bụng" in t or "khó tiêu" in t:
        return (f"{subject_vn} bị đầy bụng khó tiêu",
                f"{subject_en} stomach ache digestion problem")
    # Canh noi ve "xuong khop / gan cot" NHUNG dang noi ve mon an / dinh duong,
    # khong co dong tac nau va khong noi "dau" -> hinh can la bac si tu van,
    # khong phai nguoi dau khop. (Bang muop canh 3.)
    if ("xương khớp" in t or "gân cốt" in t) and "đau" not in t \
            and ("món ăn" in t or "dinh dưỡng" in t or "đông y" in t or "thực phẩm" in t) \
            and not any(mk in t for mk in COOKING_MARKERS):
        return ("người cao tuổi khám sức khỏe xương khớp",
                "doctor consulting elderly patient healthy joints")
    return None


def canva_keywords(text: str, subject_vn: str = "người cao tuổi",
                   subject_en: str = "elderly people",
                   default_vn: str = None, default_en: str = None):
    """Tra ve (tu khoa Canva VN, tu khoa Canva EN) sat nhat cho 1 canh."""
    if default_vn is None:
        default_vn = f"{subject_vn} sinh hoạt tại nhà"
    if default_en is None:
        default_en = f"{subject_en} daily life at home"
    t = " " + (text or "").lower().strip() + " "

    s_vn, s_en = subject_vn, subject_en
    for phrases, vn, en in SUBJECTS:
        if any(p in t for p in phrases):
            s_vn, s_en = vn, en
            break

    # 1. Ten mon "Mon N: ..." thang moi thu.
    dish = _dish_keyword(text or "")
    if dish:
        return dish

    # 2. Ngu canh dac biet (xuong khop dang noi ve dinh duong, khong phai benh).
    ctx = _context_keyword(t, s_vn, s_en)
    if ctx:
        return ctx

    # 3. Khai niem cu the nhat thang.
    best = None  # (diem uu tien, do dai cum tu khop, vn, en)
    for phrases, vn, en, prio in CONCEPTS:
        for p in phrases:
            score = (prio, len(p))
            if p in t and (best is None or score > best[0]):
                best = (score, vn, en)
    if best is None:
        return default_vn, default_en
    vn = best[1].replace("{s}", s_vn)
    en = best[2].replace("{se}", s_en)
    return vn, en
