# ============================================================
#  醫療病人安全互動式視覺化儀表板  v3.1
#  修正：所有圖表 X/Y 軸標題顏色統一為深色高對比
#  SAC 定義：1=死亡、2=重大傷害、3=輕中度、4=無傷害
# ============================================================

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="病人安全事件儀表板",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── 全域樣式 ─────────────────────────────────────────────────
st.markdown("""
<style>
    * { font-family: Arial, 'Helvetica Neue', sans-serif !important; }
    .stApp { background-color: #F8F9FA; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a2e3d 0%, #2C3E50 100%);
    }
    [data-testid="stSidebar"] * { color: #D6EAF8 !important; }
    [data-testid="stSidebar"] label { color: #AED6F1 !important; font-weight: 600; }

    .kpi-card {
        background: #FFFFFF; border-radius: 10px; padding: 18px 22px;
        box-shadow: 0 1px 8px rgba(0,0,0,0.09);
        border-left: 5px solid #3498DB; margin-bottom: 10px; min-height: 108px;
    }
    .kpi-card.danger  { border-left-color: #E74C3C; }
    .kpi-card.warning { border-left-color: #F39C12; }
    .kpi-card.death   { border-left-color: #C0392B; }

    .kpi-label {
        font-size: 11px; color: #2C3E50; font-weight: 700;
        letter-spacing: 0.6px; margin-bottom: 5px; text-transform: uppercase;
    }
    .kpi-value { font-size: 36px; font-weight: 900; color: #1C2833; line-height: 1.1; }
    .kpi-card.danger  .kpi-value { color: #922B21; }
    .kpi-card.warning .kpi-value { color: #7D6608; }
    .kpi-card.death   .kpi-value { color: #7B241C; }
    .kpi-sub { font-size: 11px; color: #4D5656; margin-top: 4px; font-weight: 500; }

    .chart-container {
        background: #FFFFFF; border-radius: 10px; padding: 20px;
        box-shadow: 0 1px 8px rgba(0,0,0,0.07); margin-bottom: 16px;
    }
    .section-title {
        font-size: 15px; font-weight: 700; color: #2C3E50; margin-bottom: 4px;
    }
    hr { border-color: #EAECEE; }
</style>
""", unsafe_allow_html=True)


# ── 軸標題統一樣式（深色，確保可讀）────────────────────────
# 所有圖表軸標題使用此字典，確保顏色一致
AXIS_TITLE_FONT  = dict(size=13, color="#1C2833", family="Arial")   # 深黑，最高對比
AXIS_TICK_FONT   = dict(size=10, color="#2C3E50", family="Arial")   # 深藍灰
TITLE_FONT       = dict(size=16, color="#2C3E50", family="Arial")
GRID_COLOR       = "#EAECEE"
ZERO_LINE_COLOR  = "#BDC3C7"
PLOT_BG          = "#FFFFFF"
PAPER_BG         = "#FFFFFF"

# ── 常數 ─────────────────────────────────────────────────────
TIMESLOT_MAP = {
    "00:01-02:00":"00-02時","00:00-02:00":"00-02時",
    "02:01-04:00":"02-04時","02:00-04:00":"02-04時",
    "04:01-06:00":"04-06時","04:00-06:00":"04-06時",
    "06:01-08:00":"06-08時","06:00-08:00":"06-08時",
    "08:01-10:00":"08-10時","08:00-10:00":"08-10時",
    "10:01-12:00":"10-12時","10:00-12:00":"10-12時",
    "12:01-14:00":"12-14時","12:00-14:00":"12-14時",
    "14:01-16:00":"14-16時","14:00-16:00":"14-16時",
    "16:01-18:00":"16-18時","16:00-18:00":"16-18時",
    "18:01-20:00":"18-20時","18:00-20:00":"18-20時",
    "20:01-22:00":"20-22時","20:00-22:00":"20-22時",
    "22:01-24:00":"22-24時","22:00-24:00":"22-24時",
}
TIMESLOT_ORDER = [
    "00-02時","02-04時","04-06時","06-08時","08-10時","10-12時",
    "12-14時","14-16時","16-18時","18-20時","20-22時","22-24時",
]
CATEGORY_COLORS = {
    "跌倒":"#003f5c","藥物":"#444e86","管路":"#955196",
    "傷害":"#dd5182","醫療":"#ff6e54","治安":"#ffa600","其他":"#7F8C8D",
}
SAC_DESC   = {1:"死亡", 2:"重大傷害", 3:"輕中度", 4:"無傷害"}
SAC_COLORS = {1:"#7B241C", 2:"#C0392B", 3:"#F39C12", 4:"#1E8449"}
HIGH_SAC   = [1, 2]

CTRL_CL_COLOR   = "#5D6D7E"
CTRL_UCL_COLOR  = "#E74C3C"
CTRL_BAND_FILL  = "rgba(44,62,80,0.06)"
OUTLIER_COLOR   = "#C0392B"


# ── 資料載入 ─────────────────────────────────────────────────
@st.cache_data(show_spinner="📂 載入資料中...")
def load_data(path):
    xl  = pd.ExcelFile(path)
    df  = pd.read_excel(xl, sheet_name="109-113全部")
    df["發生日期"] = pd.to_datetime(df["發生日期"], errors="coerce")
    df  = df[df["發生日期"].notna()].copy()
    df["年月"]    = df["發生日期"].dt.to_period("M").astype(str)
    df["SAC_num"] = pd.to_numeric(df["SAC"], errors="coerce")
    df["單位"]    = (df["通報者資料-通報者服務單位"]
                     .astype(str).str.strip().str.upper()
                     .replace({"NAN":"未知","":"未知"}))
    df["時段標準"] = df["發生時段"].map(TIMESLOT_MAP)
    cat_map = {
        "跌倒事件":"跌倒","藥物事件":"藥物","管路事件":"管路",
        "傷害行為":"傷害","醫療事件":"醫療","治安事件":"治安",
        "手術事件":"醫療","麻醉事件":"醫療","輸血事件":"醫療",
        "不預期心跳停止":"醫療","檢查檢驗":"其他","檢驗檢查":"其他",
        "公共意外":"其他","其他事件":"其他",
    }
    df["事件大類"] = df["事件類別"].map(cat_map).fillna("其他")

    # ── 診斷分類函數 (classify_dx) ──────────────────────────
    def classify_dx(text):
        if pd.isna(text): return "其他"
        t = str(text).lower()
        if any(k in t for k in ["思覺失調","精神病","psycho","schizo"]):
            return "思覺失調/精神病"
        if any(k in t for k in ["雙相","躁症","bipolar","manic"]):
            return "雙相/躁症"
        if any(k in t for k in ["憂鬱","depression","depressive"]):
            return "憂鬱症"
        if any(k in t for k in ["失智","dementia"]):
            return "失智症"
        if any(k in t for k in ["帕金森","parkinson"]):
            return "帕金森氏症"
        if any(k in t for k in ["腦梗","中風","stroke","i63","i64",
                                  "腦血管","腦出血","ich"]):
            return "腦血管病"
        if any(k in t for k in ["骨折","fr.","fracture"," # "]):
            return "骨折相關"
        if any(k in t for k in ["糖尿病","diabetes"," dm","dm ","dm,","dm."]):
            return "糖尿病"
        if any(k in t for k in ["腎病","ckd","腎衰","腎功能"]):
            return "腎病"
        if any(k in t for k in ["肝病","肝炎","肝硬化","肝衰"]):
            return "肝病"
        if any(k in t for k in ["心臟","心衰","心肌","冠狀動脈","心房","心室"]):
            return "心臟病"
        if any(k in t for k in ["肺炎","呼吸","copd","氣喘","支氣管"]):
            return "呼吸系統"
        if any(k in t for k in ["癌","腫瘤","惡性","malignant","carcinoma","lymphoma"]):
            return "腫瘤/癌症"
        return "其他"

    df["診斷分類"] = df["發生者資料-診斷"].apply(classify_dx)

    # ── 跌倒深度分析資料（跌倒工作表 merge 全部工作表科別與影響程度）
    df_fall = pd.read_excel(xl, sheet_name="109-113跌倒")
    df_fall["發生日期"] = pd.to_datetime(df_fall["發生日期"], errors="coerce")
    df_fall = df_fall[df_fall["發生日期"].notna()].copy()
    df_fall["年月"] = df_fall["發生日期"].dt.to_period("M").astype(str)
    cols_from_all = [
        "通報案號",
        "病人/住民-所在科別",
        "病人/住民-事件發生後對病人健康的影響程度",
        "病人/住民-事件發生後對病人健康的影響程度(彙總)"
    ]
    # 去除空白避免比對失敗
    for col in cols_from_all[1:]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    df_fall = df_fall.merge(df[cols_from_all], on="通報案號", how="left")

    # ── 事件說明特徵萃取 (extract_fall_features) ─────────────
    FALL_FEATURES = {
        "地點_床邊下床":     ["下床","床邊","起床","離床","坐起"],
        "地點_浴廁":        ["廁所","洗手間","浴室","如廁","洗澡"],
        "地點_走廊行走":     ["走廊","走路","行走","散步"],
        "地點_椅子輪椅":     ["椅子","輪椅","便盆椅"],
        "機轉_滑倒":        ["滑","打滑","濕"],
        "機轉_頭暈血壓低":   ["頭暈","暈","血壓低","姿位性"],
        "機轉_自行起身未告知":["自行","未按鈴","未通知","未叫護"],
        "機轉_站不穩腳軟":   ["站不穩","腳軟","無力","腿軟"],
        "發現_護理人員巡視":  ["巡房","巡視","護士發現","護理師發現"],
        "發現_聲響":        ["聲音","聲響","跌倒聲"],
        "傷害_頭部":        ["頭","額頭","頭皮"],
        "傷害_下肢":        ["腳","膝蓋","足部","下肢","腳踝"],
        "傷害_臀髖":        ["臀","髖"],
        "病況_精神症狀":     ["幻覺","妄想","躁動","激動","衝動"],
        "病況_約束相關":     ["約束","保護帶","掙脫","解開"],
    }
    def extract_fall_features(text):
        t = str(text) if not pd.isna(text) else ""
        return {feat: any(k in t for k in kws)
                for feat, kws in FALL_FEATURES.items()}

    feat_df = df_fall["事件說明"].apply(
        lambda x: pd.Series(extract_fall_features(x)))
    df_fall = pd.concat([df_fall.reset_index(drop=True),
                         feat_df.reset_index(drop=True)], axis=1)

    db  = pd.read_excel(xl, sheet_name="住院人日數")
    db["年月"] = pd.to_datetime(db["年月"]).dt.to_period("M").astype(str)
    db["單位"] = db["單位"].astype(str).str.strip().str.upper()
    tot = db.groupby("年月", as_index=False)["住院人日數"].sum()
    tot["單位"] = "全院"
    db  = pd.concat([db, tot], ignore_index=True)
    return df, db, df_fall

EXCEL_PATH = "109-113全部_藥物跌倒管路傷害醫療治安__115_02_01.xlsx"
try:
    df_all, df_bed, df_fall_base = load_data(EXCEL_PATH)
except FileNotFoundError:
    st.error(f"❌ 找不到資料檔：{EXCEL_PATH}，請確認與 app.py 在同一資料夾。")
    st.stop()
except Exception as e:
    st.error(f"❌ 載入失敗：{e}")
    st.stop()


# ── 側邊欄 ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏥 病人安全儀表板")
    st.markdown("**國軍花蓮總醫院**")
    st.markdown("---")

    all_months = sorted(df_all["年月"].dropna().unique())
    st.markdown("### 📅 時間區間")
    month_range = st.select_slider("月份", options=all_months,
        value=(all_months[0], all_months[-1]), label_visibility="collapsed")
    start_m, end_m = month_range

    st.markdown("---")
    st.markdown("### 🏬 發生單位")
    unit_opts = ["全院"] + sorted(
        [u for u in df_all["單位"].dropna().unique() if u not in ["未知",""]])
    sel_unit = st.selectbox("單位", unit_opts, index=0, label_visibility="collapsed")

    st.markdown("---")
    st.markdown("### 📋 事件類別")
    cat_opts = ["全部"] + sorted(df_all["事件大類"].unique())
    sel_cat  = st.selectbox("類別", cat_opts, index=0, label_visibility="collapsed")

    st.markdown("---")
    st.markdown("### ⚠️ SAC 嚴重度")
    sac_sel = st.multiselect("SAC", options=[1,2,3,4], default=[1,2,3,4],
        format_func=lambda x: {1:"SAC 1 死亡",2:"SAC 2 重大傷害",
                                3:"SAC 3 輕中度",4:"SAC 4 無傷害"}[x],
        label_visibility="collapsed")
    if not sac_sel:
        sac_sel = [1,2,3,4]

    st.markdown("---")
    st.markdown("### 🏥 診斷科別篩選")
    dept_all_opts = ["全部科別"] + sorted(
        [d for d in df_all["病人/住民-所在科別"].dropna().unique()
         if str(d).strip() not in ["", "nan"]])
    sel_dept = st.selectbox("診斷科別", dept_all_opts, index=0,
                            label_visibility="collapsed",
                            help="用於診斷特徵分析區塊")

    st.markdown("---")
    st.markdown("""<div style='font-size:11px;color:#85C1E9;line-height:2.0'>
    📌 資料來源：病人安全通報系統<br>
    📆 資料期間：109–113 年<br>
    🔄 最後更新：115/02/01<br>
    🔖 版本：v3.2</div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("""<div style='font-size:10px;color:#AED6F1;line-height:2.0'>
    <b>SAC 嚴重度定義</b><br>
    🔴 SAC 1：死亡<br>
    🟠 SAC 2：重大傷害<br>
    🟡 SAC 3：輕中度傷害<br>
    🟢 SAC 4：無傷害</div>""", unsafe_allow_html=True)


# ── 過濾 ─────────────────────────────────────────────────────
mask = (df_all["年月"] >= start_m) & (df_all["年月"] <= end_m)
dff  = df_all[mask].copy()
if sel_unit != "全院":
    dff = dff[dff["單位"] == sel_unit]
if sel_cat != "全部":
    dff = dff[dff["事件大類"] == sel_cat]
dff = dff[dff["SAC_num"].isin(sac_sel) | dff["SAC_num"].isna()]

bed_key  = "全院" if sel_unit == "全院" else sel_unit
df_bed_f = df_bed[df_bed["單位"] == bed_key].copy()
mc = dff.groupby("年月").size().reset_index(name="件數").sort_values("年月")
mc = mc.merge(df_bed_f[["年月","住院人日數"]], on="年月", how="left")
mc["發生率"] = (mc["件數"] / mc["住院人日數"] * 1000).round(2).fillna(0)

# ── 年月顯示格式：2025-01 → 2025/01（所有圖表 X 軸統一使用）
mc["年月顯示"] = mc["年月"].str.replace("-", "/", regex=False)
dff = dff.copy()
dff["年月顯示"] = dff["年月"].str.replace("-", "/", regex=False)

# ── 跌倒深度分析資料：依時間區間篩選（與主篩選器連動）
dff_fall = df_fall_base[
    (df_fall_base["年月"] >= start_m) & (df_fall_base["年月"] <= end_m)
].copy()

# ── 診斷特徵分析資料：完全繼承主篩選器（時間+單位+類別+SAC）+ 科別篩選
dff_dx = dff.copy()   # dff 已套用所有主篩選器
if sel_dept != "全部科別":
    dff_dx = dff_dx[dff_dx["病人/住民-所在科別"] == sel_dept]


# ════════════════════════════════════════════════════════════
#  📅 年度比較分析（2024 vs 2025）— 固定全院層級
#  不受科別篩選器影響；使用 df_fall_base（全量跌倒資料）
# ════════════════════════════════════════════════════════════

# ── 住院 / 含護理之家 切換 ────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📅 年度比較範圍")
    inc_ltc = st.radio("跌倒統計範圍", ["只看住院", "含護理之家"],
                       index=0, horizontal=True,
                       label_visibility="collapsed")

EXCLUDE_DEPT = [] if inc_ltc == "含護理之家" else ["護理之家"]

# 全量跌倒資料（含年份欄位）—— 年度比較專用
_fb = df_fall_base.copy()
_fb["年"]  = pd.to_datetime(_fb["年月"], format="%Y-%m").dt.year
_fb["月"]  = pd.to_datetime(_fb["年月"], format="%Y-%m").dt.month
if EXCLUDE_DEPT:
    _fb = _fb[~_fb["病人/住民-所在科別"].isin(EXCLUDE_DEPT)]

_fb24 = _fb[_fb["年"] == 2024]
_fb25 = _fb[_fb["年"] == 2025]

INJ_COL_SUM  = "病人/住民-事件發生後對病人健康的影響程度(彙總)"
INJ_COL_DET  = "病人/住民-事件發生後對病人健康的影響程度"
DEPT_COL_YR  = "病人/住民-所在科別"

# 全院事件（傷害行為）
_all_yr = df_all.copy()
_all_yr["年"] = pd.to_datetime(
    _all_yr["年月"], format="%Y-%m", errors="coerce").dt.year
_all_yr["月"] = pd.to_datetime(
    _all_yr["年月"], format="%Y-%m", errors="coerce").dt.month
_harm24 = _all_yr[(_all_yr["年"]==2024) & (_all_yr["事件大類"]=="傷害")]
_harm25 = _all_yr[(_all_yr["年"]==2025) & (_all_yr["事件大類"]=="傷害")]
_harm25_last_m = int(_harm25["月"].max()) if not _harm25.empty else 1

def _safe_pct(num, den):
    return round(num / den * 100, 1) if den > 0 else 0.0

def _inj_rate(df):
    if INJ_COL_SUM not in df.columns: return 0.0
    n = len(df)
    return _safe_pct((df[INJ_COL_SUM] == "有傷害").sum(), n)

def _psych_pct(df):
    if DEPT_COL_YR not in df.columns: return 0.0
    return _safe_pct((df[DEPT_COL_YR] == "精神科").sum(), len(df))

def _mid_above_rate(df):
    if INJ_COL_DET not in df.columns: return 0.0
    sub = df[df[DEPT_COL_YR].isin(["外科","內科"])]
    return _safe_pct(
        sub[INJ_COL_DET].isin(["中度","重度","極重度","死亡"]).sum(),
        len(sub))

# 指標計算
v24_inj    = _inj_rate(_fb24)
v25_inj    = _inj_rate(_fb25)
v24_psych  = _psych_pct(_fb24)
v25_psych  = _psych_pct(_fb25)
v24_mid    = _mid_above_rate(_fb24)
v25_mid    = _mid_above_rate(_fb25)
n24_harm   = len(_harm24)
n25_harm   = len(_harm25)
harm25_est = round(n25_harm / _harm25_last_m * 12) if _harm25_last_m > 0 else n25_harm

# ── 頁首 ─────────────────────────────────────────────────────
st.markdown(f"""
<div style='background:linear-gradient(135deg,#1a2e3d,#2C3E50);
            padding:20px 28px;border-radius:10px;margin-bottom:20px'>
  <h2 style='color:#FFFFFF;margin:0;font-size:21px;font-weight:700'>
    🏥 醫療病人安全事件互動式儀表板
  </h2>
  <p style='color:#AED6F1;margin:5px 0 0;font-size:12px'>
    國軍花蓮總醫院｜{start_m} ～ {end_m}｜單位：{sel_unit}｜類別：{sel_cat}
  </p>
</div>""", unsafe_allow_html=True)

if dff.empty:
    st.markdown('<div style="background:#FFF3CD;border-left:4px solid #F39C12;padding:10px 14px;border-radius:4px;color:#7D4700;font-size:13px">⚠️ 目前篩選條件下無資料，請調整側邊欄設定。</div>', unsafe_allow_html=True)
    st.stop()



# ── 年度比較區塊 ─────────────────────────────────────────
st.markdown('<div class="chart-container">', unsafe_allow_html=True)
st.markdown(f"""
<div style='background:linear-gradient(135deg,#1a2e3d,#2C3E50);
            padding:12px 20px;border-radius:8px;margin-bottom:14px'>
  <h3 style='color:#FFFFFF;margin:0;font-size:17px;font-weight:700'>
    📅 年度比較分析（2024 vs 2025）
  </h3>
  <p style='color:#AED6F1;margin:4px 0 0;font-size:11px'>
    全院層級・不受科別篩選影響・範圍：{inc_ltc}
  </p>
</div>""", unsafe_allow_html=True)

# ── 4個指標卡（含紅綠燈警示 + Tooltip 定義）────────────────
def _kpi_card(label, value, delta_val, delta_txt, up_is_bad=True, tooltip=""):
    """
    醫療專業 KPI 卡片
    - 越低越好 (up_is_bad=True)：上升→紅燈、下降→綠燈
    - 越高越好 (up_is_bad=False)：上升→綠燈、下降→紅燈
    - tooltip: 右上角懸停說明（分子分母定義）
    """
    if delta_val > 0:
        arrow  = "▲"
        d_color = "#C0392B" if up_is_bad else "#1E8449"
        d_bg    = "#FADBD8" if up_is_bad else "#D5F5E3"
        led     = "#E74C3C" if up_is_bad else "#27AE60"   # 左邊指示條顏色
        status  = "⛔" if up_is_bad else "✅"
    elif delta_val < 0:
        arrow  = "▼"
        d_color = "#1E8449" if up_is_bad else "#C0392B"
        d_bg    = "#D5F5E3" if up_is_bad else "#FADBD8"
        led     = "#27AE60" if up_is_bad else "#E74C3C"
        status  = "✅" if up_is_bad else "⛔"
    else:
        arrow, d_color, d_bg = "─", "#7F8C8D", "#F2F3F4"
        led    = "#AEB6BF"
        status = "➖"

    # 數值字體在指標惡化時加粗強調
    val_weight = "900" if (up_is_bad and delta_val > 0) or (not up_is_bad and delta_val < 0) else "800"
    val_color  = "#C0392B" if (up_is_bad and delta_val > 0) else "#1C2833"

    tooltip_html = f"""
<div class='kpi-tooltip-icon' title='{tooltip}'
     style='position:absolute;top:10px;right:12px;
            width:18px;height:18px;background:#EBF5FB;border-radius:50%;
            display:flex;align-items:center;justify-content:center;
            font-size:11px;color:#2E86C1;cursor:help;
            border:1px solid #AED6F1;font-weight:700'>ℹ</div>
""" if tooltip else ""

    return f"""
<div style='background:#FFFFFF;border-left:5px solid {led};border-radius:10px;
            padding:16px 18px 14px;box-shadow:0 2px 8px rgba(0,0,0,0.09);
            position:relative;min-height:110px'>
  {tooltip_html}
  <div style='font-size:11px;color:#5D6D7E;font-weight:700;
              letter-spacing:0.4px;margin-bottom:8px;padding-right:24px'>
    {status} {label}
  </div>
  <div style='font-size:32px;font-weight:{val_weight};color:{val_color};
              line-height:1.1;letter-spacing:-0.5px'>{value}</div>
  <div style='font-size:11px;font-weight:700;color:{d_color};
              background:{d_bg};border-radius:4px;
              padding:3px 8px;display:inline-block;margin-top:8px'>
    {arrow} {delta_txt}
  </div>
</div>"""

# 指標定義 Tooltip
TOOLTIP_INJ   = "跌倒有傷害率 = 有傷害件數 ÷ 跌倒總件數\n傷害判斷：病人健康影響程度(彙總) = 有傷害"
TOOLTIP_PSYCH = "精神科跌倒占比 = 精神科跌倒件數 ÷ 全院跌倒總件數"
TOOLTIP_MID   = "中度以上傷害率 = 外科+內科中，中度/重度/極重度/死亡件數 ÷ 外科+內科跌倒總件數"
TOOLTIP_HARM  = "傷害行為件數 = 事件大類為「傷害」的通報件數（全院）"

mk1, mk2, mk3, mk4 = st.columns(4)
with mk1:
    delta_inj = round(v25_inj - v24_inj, 2)
    st.markdown(_kpi_card(
        "跌倒有傷害率",
        f"{v25_inj:.2f}%",
        delta_inj,
        f"{delta_inj:+.2f}% vs 2024（{v24_inj:.2f}%）",
        up_is_bad=True, tooltip=TOOLTIP_INJ,
    ), unsafe_allow_html=True)
with mk2:
    delta_psych = round(v25_psych - v24_psych, 2)
    st.markdown(_kpi_card(
        "精神科跌倒占比",
        f"{v25_psych:.2f}%",
        delta_psych,
        f"{delta_psych:+.2f}% vs 2024（{v24_psych:.2f}%）",
        up_is_bad=True, tooltip=TOOLTIP_PSYCH,
    ), unsafe_allow_html=True)
with mk3:
    delta_mid = round(v25_mid - v24_mid, 2)
    st.markdown(_kpi_card(
        "中度以上傷害率（外科+內科）",
        f"{v25_mid:.2f}%",
        delta_mid,
        f"{delta_mid:+.2f}% vs 2024（{v24_mid:.2f}%）",
        up_is_bad=True, tooltip=TOOLTIP_MID,
    ), unsafe_allow_html=True)
with mk4:
    delta_harm = n25_harm - n24_harm
    st.markdown(_kpi_card(
        "傷害行為年件數",
        f"{n25_harm} 件",
        delta_harm,
        f"{delta_harm:+d} 件 vs 2024（{n24_harm}件）",
        up_is_bad=True, tooltip=TOOLTIP_HARM,
    ), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 圖①：跌倒月份趨勢比較折線圖 ─────────────────────────
st.markdown('<p class="section-title">① 跌倒事件月份趨勢比較（2024 vs 2025 vs 歷年均值）</p>',
            unsafe_allow_html=True)

# 各年月份件數
def _monthly_counts(df, yr):
    sub = df[df["年"] == yr]
    return sub.groupby("月").size().reindex(range(1,13), fill_value=0)

cnt24  = _monthly_counts(_fb, 2024)
cnt25  = _monthly_counts(_fb, 2025)
# 2020-2023 歷年平均
hist_mean = pd.Series(0.0, index=range(1,13))
hist_yrs  = [y for y in [2020,2021,2022,2023] if y in _fb["年"].values]
if hist_yrs:
    hist_mean = pd.concat(
        [_monthly_counts(_fb, y) for y in hist_yrs], axis=1
    ).mean(axis=1)

MONTHS_ZH = ["1月","2月","3月","4月","5月","6月",
             "7月","8月","9月","10月","11月","12月"]

fig_yr1 = go.Figure()
# 歷年均值（灰色虛線）
fig_yr1.add_trace(go.Scatter(
    x=MONTHS_ZH, y=hist_mean.values, name="2020–2023 均值",
    mode="lines", line=dict(color="#AEB6BF", dash="dash", width=2),
    hovertemplate="<b>%{x}</b><br>歷年均值：%{y:.1f} 件<extra></extra>",
))
# 2024（藍色實線）
fig_yr1.add_trace(go.Scatter(
    x=MONTHS_ZH, y=cnt24.values, name="2024 實際",
    mode="lines+markers",
    line=dict(color="#2471A3", width=2.5),
    marker=dict(size=7, color="#2471A3"),
    hovertemplate="<b>%{x}</b><br>2024：%{y} 件<extra></extra>",
))
# 2025（紅色實線，只畫有資料的月份）
last_m25 = int(_fb25["月"].max()) if not _fb25.empty else 0
cnt25_plot = cnt25.copy().astype(float)
if last_m25 < 12:
    cnt25_plot.iloc[last_m25:] = None   # 截斷之後月份
fig_yr1.add_trace(go.Scatter(
    x=MONTHS_ZH, y=cnt25_plot.values, name="2025 實際",
    mode="lines+markers",
    line=dict(color="#C0392B", width=2.5),
    marker=dict(size=7, color="#C0392B"),
    hovertemplate="<b>%{x}</b><br>2025：%{y:.0f} 件<extra></extra>",
    connectgaps=False,
))
fig_yr1.update_layout(
    title=None,
    height=380,
    plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
    legend=dict(orientation="h", y=1.12, x=1, xanchor="right",
                font=dict(size=11, color="#2C3E50")),
    xaxis=dict(
        title=dict(text="月份", font=AXIS_TITLE_FONT),
        tickfont=AXIS_TICK_FONT, showgrid=False,
    ),
    yaxis=dict(
        title=dict(text="跌倒件數", font=AXIS_TITLE_FONT),
        tickfont=AXIS_TICK_FONT,
        gridcolor=GRID_COLOR, griddash="dot",
        zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
        rangemode="tozero",
    ),
    hovermode="x unified",
    margin=dict(t=70, b=60, l=60, r=20),
)
st.plotly_chart(fig_yr1, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── 圖②：各科別 2024 vs 2025 分組橫條圖 ────────────
st.markdown('<p class="section-title">② 各科別跌倒件數：2024 vs 2025</p>',
            unsafe_allow_html=True)

CMP_DEPTS   = ["精神科","外科","內科","復健科"]
last_m25_fb = int(_fb25["月"].max()) if not _fb25.empty else 1

cmp_data = []
for dept in CMP_DEPTS:
    n24 = (_fb24[DEPT_COL_YR] == dept).sum()
    n25 = (_fb25[DEPT_COL_YR] == dept).sum()
    cmp_data.append({"科別": dept, "2024": n24, "2025": n25})
df_cmp = pd.DataFrame(cmp_data).sort_values("2024", ascending=True)

fig_yr2 = go.Figure()
# 2024（藍色）
fig_yr2.add_trace(go.Bar(
    name="2024",
    y=df_cmp["科別"],
    x=df_cmp["2024"],
    orientation="h",
    marker_color="#2471A3",
    marker_opacity=0.85,
    text=df_cmp["2024"].astype(str) + " 件",
    textposition="outside",
    textfont=dict(size=10, color="#1C2833", family="Arial"),
    hovertemplate="<b>%{y}</b><br>2024：%{x} 件<extra></extra>",
))
# 2025（紅色）
fig_yr2.add_trace(go.Bar(
    name="2025",
    y=df_cmp["科別"],
    x=df_cmp["2025"],
    orientation="h",
    marker_color="#C0392B",
    marker_opacity=0.80,
    text=df_cmp["2025"].astype(str) + " 件",
    textposition="outside",
    textfont=dict(size=10, color="#C0392B", family="Arial Bold"),
    hovertemplate="<b>%{y}</b><br>2025：%{x} 件<extra></extra>",
))
max_val = max(df_cmp["2024"].max(), df_cmp["2025"].max())
fig_yr2.update_layout(
    title=None,
    barmode="group",
    height=380,
    plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
    legend=dict(orientation="h", y=1.12, x=1, xanchor="right",
                font=dict(size=11, color="#2C3E50")),
    xaxis=dict(
        title=dict(text="跌倒件數", font=AXIS_TITLE_FONT),
        tickfont=AXIS_TICK_FONT,
        range=[0, max_val * 1.4],
        gridcolor=GRID_COLOR, griddash="dot",
        zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
    ),
    yaxis=dict(
        title=dict(text="科別", font=AXIS_TITLE_FONT),
        tickfont=dict(size=12, color="#2C3E50", family="Arial"),
        automargin=True,
    ),
    margin=dict(t=70, b=60, l=80, r=120),
    hovermode="y unified",
)
st.plotly_chart(fig_yr2, use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)




# ── KPI ──────────────────────────────────────────────────────
total    = len(dff)
avg_rate = mc["發生率"].replace(0, np.nan).mean()
rate_str = f"{avg_rate:.2f}‰" if pd.notna(avg_rate) else "N/A"
high_sac = int(dff["SAC_num"].isin(HIGH_SAC).sum())
high_pct = f"{high_sac/total*100:.2f}%" if total else "0.00%"
sac1_cnt = int((dff["SAC_num"] == 1).sum())
sac1_pct = f"{sac1_cnt/total*100:.2f}%" if total else "0.00%"
top_cat  = dff["事件大類"].value_counts().idxmax()
top_cnt  = int(dff["事件大類"].value_counts().max())
months_n = mc["年月"].nunique()

c1,c2,c3,c4 = st.columns(4)
c1.markdown(f"""<div class="kpi-card">
  <div class="kpi-label">📊 總發生件數</div>
  <div class="kpi-value">{total:,}</div>
  <div class="kpi-sub">共 {months_n} 個月份</div>
</div>""", unsafe_allow_html=True)
c2.markdown(f"""<div class="kpi-card warning">
  <div class="kpi-label">📈 平均月發生率</div>
  <div class="kpi-value">{rate_str}</div>
  <div class="kpi-sub">每千住院人日</div>
</div>""", unsafe_allow_html=True)
c3.markdown(f"""<div class="kpi-card danger">
  <div class="kpi-label">🚨 高嚴重度（SAC 1+2）</div>
  <div class="kpi-value">{high_sac:,}</div>
  <div class="kpi-sub">死亡+重大傷害，佔 {high_pct}</div>
</div>""", unsafe_allow_html=True)
c4.markdown(f"""<div class="kpi-card death">
  <div class="kpi-label">💀 SAC 1 死亡件數</div>
  <div class="kpi-value">{sac1_cnt:,}</div>
  <div class="kpi-sub">佔總件數 {sac1_pct}</div>
</div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  圖A：每月件數 + 發生率（雙軸）
#  軸標題：深色 #1C2833，字體 13px Bold
# ════════════════════════════════════════════════════════════
st.markdown('<div class="chart-container">', unsafe_allow_html=True)
fig_a = make_subplots(specs=[[{"secondary_y": True}]])
fig_a.add_trace(go.Bar(
    x=mc["年月顯示"], y=mc["件數"], name="發生件數",
    marker_color="#2C3E50", marker_opacity=0.75,
    text=mc["件數"],
    textposition="outside",
    textfont=dict(size=8, color="#2C3E50", family="Arial"),
    hovertemplate="<b>%{x}</b><br>件數：%{y} 件<extra></extra>",
), secondary_y=False)
fig_a.add_trace(go.Scatter(
    x=mc["年月顯示"], y=mc["發生率"], name="發生率(‰)",
    mode="lines+markers", line=dict(color="#E74C3C", width=2.5),
    marker=dict(size=5, color="#E74C3C"),
    hovertemplate="<b>%{x}</b><br>發生率：%{y:.2f}‰<extra></extra>",
), secondary_y=True)
fig_a.update_layout(
    title=dict(text="📊 每月發生件數與發生率趨勢", font=TITLE_FONT),
    height=420, plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
    hovermode="x unified",
    legend=dict(orientation="h", y=1.1, x=1, xanchor="right",
                font=dict(size=11, color="#2C3E50")),
    xaxis=dict(
        title=dict(text="年月", font=AXIS_TITLE_FONT),
        tickangle=-45, showgrid=False, tickfont=AXIS_TICK_FONT,
        linecolor="#BDC3C7", linewidth=1,
    ),
    margin=dict(t=60, b=50),
    uniformtext=dict(mode="hide", minsize=7),  # 月份過密時自動隱藏標籤
)
fig_a.update_yaxes(
    title_text="發生件數",
    title_font=AXIS_TITLE_FONT,
    tickfont=AXIS_TICK_FONT,
    secondary_y=False,
    gridcolor=GRID_COLOR, gridwidth=1, griddash="dot",
    zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
)
fig_a.update_yaxes(
    title_text="發生率 (‰)",
    title_font=dict(size=13, color="#C0392B", family="Arial"),  # 右軸與折線同色
    tickfont=dict(size=10, color="#C0392B", family="Arial"),
    secondary_y=True,
)
st.plotly_chart(fig_a, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  圖B：管制圖
#  軸標題：深色，控制線標籤各自使用線條顏色
# ════════════════════════════════════════════════════════════
st.markdown('<div class="chart-container">', unsafe_allow_html=True)
rates = mc["發生率"].replace(0, np.nan).dropna()
if len(rates) >= 3:
    cl  = float(rates.mean())
    std = float(rates.std())
    ucl = cl + 3 * std
    lcl = max(0.0, cl - 3 * std)
    mc["異常點"] = mc["發生率"].apply(lambda x: (x > ucl) or (0 < x < lcl))

    fig_b = go.Figure()
    fig_b.add_trace(go.Scatter(
        x=list(mc["年月顯示"]) + list(mc["年月顯示"])[::-1],
        y=[ucl]*len(mc) + [lcl]*len(mc),
        fill="toself", fillcolor=CTRL_BAND_FILL,
        line=dict(color="rgba(0,0,0,0)"),
        name="管制區間", hoverinfo="skip"))
    fig_b.add_trace(go.Scatter(
        x=mc["年月顯示"], y=mc["發生率"],
        mode="lines+markers", name="月發生率",
        line=dict(color="#3498DB", width=2),
        marker=dict(size=7,
            color=mc["異常點"].map({True: OUTLIER_COLOR, False: "#3498DB"}),
            symbol=mc["異常點"].map({True: "diamond", False: "circle"}),
            line=dict(width=1.5, color="white")),
        hovertemplate="<b>%{x}</b><br>%{y:.2f}‰<extra></extra>"))
    outliers = mc[mc["異常點"]]
    if not outliers.empty:
        fig_b.add_trace(go.Scatter(
            x=outliers["年月顯示"], y=outliers["發生率"],
            mode="markers+text", name="⚠️ 超出管制",
            marker=dict(size=13, color=OUTLIER_COLOR, symbol="diamond",
                        line=dict(width=2, color="white")),
            text=outliers["發生率"].round(2).astype(str) + "‰",
            textposition="top center",
            textfont=dict(size=10, color="#7B241C", family="Arial Bold"),
            hovertemplate="⚠️ <b>%{x}</b>：%{y:.2f}‰<extra></extra>"))
    for y_val, lbl, clr, ds in [
        (ucl, f"UCL = {ucl:.2f}‰", "#E74C3C", "dash"),
        (cl,  f"CL  = {cl:.2f}‰",  "#5D6D7E", "solid"),
        (lcl, f"LCL = {lcl:.2f}‰", "#E74C3C", "dash"),
    ]:
        fig_b.add_hline(y=y_val, line_dash=ds, line_color=clr, line_width=2,
            annotation_text=f"  {lbl}", annotation_position="right",
            annotation_font=dict(size=11, color=clr, family="Arial Bold"))
    fig_b.update_layout(
        title=dict(text="📉 病安發生率統計管制圖（X̄ ± 3σ）", font=TITLE_FONT),
        height=380, plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        hovermode="x unified",
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right",
                    font=dict(size=11, color="#2C3E50")),
        xaxis=dict(
            title=dict(text="年月", font=AXIS_TITLE_FONT),
            tickangle=-45, showgrid=False, tickfont=AXIS_TICK_FONT,
        ),
        yaxis=dict(
            title=dict(text="發生率 (‰)", font=AXIS_TITLE_FONT),
            tickfont=AXIS_TICK_FONT,
            gridcolor=GRID_COLOR, griddash="dot",
            zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
        ),
        margin=dict(t=60, b=50, r=140))
    st.plotly_chart(fig_b, use_container_width=True)

    r1, r2, r3 = st.columns(3)
    r1.markdown(f"""
<div style='background:#FFFFFF;border:1px solid #D5D8DC;border-radius:10px;
            padding:14px 18px;box-shadow:0 2px 6px rgba(0,0,0,0.08);text-align:center'>
  <div style='font-size:12px;color:#5D6D7E;font-weight:600;margin-bottom:6px'>📏 中心線 CL</div>
  <div style='font-size:28px;font-weight:900;color:#1C2833'>{cl:.2f}‰</div>
</div>""", unsafe_allow_html=True)
    r2.markdown(f"""
<div style='background:#FFFFFF;border:2px solid #E74C3C;border-radius:10px;
            padding:14px 18px;box-shadow:0 2px 6px rgba(0,0,0,0.08);text-align:center'>
  <div style='font-size:12px;color:#922B21;font-weight:600;margin-bottom:6px'>🔴 上管制線 UCL</div>
  <div style='font-size:28px;font-weight:900;color:#C0392B'>{ucl:.2f}‰</div>
</div>""", unsafe_allow_html=True)
    r3.markdown(f"""
<div style='background:#FFFFFF;border:2px solid #1E8449;border-radius:10px;
            padding:14px 18px;box-shadow:0 2px 6px rgba(0,0,0,0.08);text-align:center'>
  <div style='font-size:12px;color:#1A5276;font-weight:600;margin-bottom:6px'>🟢 下管制線 LCL</div>
  <div style='font-size:28px;font-weight:900;color:#1E8449'>{lcl:.2f}‰</div>
</div>""", unsafe_allow_html=True)
    if not outliers.empty:
        st.markdown(f'<div style="background:#FFF3CD;border-left:4px solid #F39C12;padding:10px 14px;border-radius:4px;color:#7D4700;font-size:13px">⚠️ 共 <b>{len(outliers)}</b> 個月份超出管制界限，請重點追蹤！</div>', unsafe_allow_html=True)
else:
    st.info("📌 管制圖需要至少 3 個月資料，請擴大時間區間。")
st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  圖C：時段 + 圖D：SAC 環圈（並排）
#  軸標題深色，刻度深色
# ════════════════════════════════════════════════════════════
col_c, col_d = st.columns([1.2, 1])

with col_c:
    st.markdown('<p class="section-title">🕐 事件發生時段分佈（每2小時）</p>',
                unsafe_allow_html=True)
    ts_raw = dff["時段標準"].dropna()
    if ts_raw.empty:
        st.info("無時段資料")
    else:
        ts_cnt = ts_raw.value_counts().reindex(TIMESLOT_ORDER, fill_value=0)
        max_v  = max(int(ts_cnt.max()), 1)
        clrs = []
        for v in ts_cnt.values:
            r = v / max_v
            if r < 0.4:
                clrs.append(f"rgba(192,57,43,{0.25 + 0.30*(r/0.4)})")
            else:
                clrs.append(f"rgba(192,57,43,{0.55 + 0.43*((r-0.4)/0.6)})")

        peak   = ts_cnt.idxmax()
        peak_v = int(ts_cnt.max())

        # 次高峰：排除最高峰後的最大值
        ts_no_peak = ts_cnt.drop(index=peak)
        sec_peak   = ts_no_peak.idxmax()
        sec_peak_v = int(ts_no_peak.max())

        fig_c = go.Figure(go.Bar(
            x=TIMESLOT_ORDER, y=ts_cnt.values,
            marker_color=clrs, marker_line=dict(width=0),
            text=ts_cnt.values, textposition="outside",
            textfont=dict(size=11, color="#1C2833"),
            hovertemplate="<b>%{x}</b><br>%{y} 件<extra></extra>",
        ))
        # 最高峰標註
        fig_c.add_annotation(
            x=peak, y=peak_v, text=f"▲ 高峰<br>{peak}",
            showarrow=True, arrowhead=2, arrowcolor="#E74C3C",
            font=dict(size=11, color="#7B241C", family="Arial Bold"),
            yshift=25, ax=0, ay=-45)
        # 次高峰標註
        fig_c.add_annotation(
            x=sec_peak, y=sec_peak_v, text=f"△ 次高峰<br>{sec_peak}",
            showarrow=True, arrowhead=2, arrowcolor="#F39C12",
            font=dict(size=10, color="#7D6608", family="Arial Bold"),
            yshift=25, ax=0, ay=-45)
        fig_c.update_layout(
            height=460, plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            xaxis=dict(
                title=dict(text="發生時段", font=AXIS_TITLE_FONT),
                tickangle=-30, tickfont=AXIS_TICK_FONT, showgrid=False,
            ),
            yaxis=dict(
                title=dict(text="事件件數", font=AXIS_TITLE_FONT),
                tickfont=AXIS_TICK_FONT,
                gridcolor=GRID_COLOR, griddash="dot",
                range=[0, peak_v * 1.45],   # 加大上界，讓兩個標註都有空間
                zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
            ),
            margin=dict(t=30, b=60, l=60, r=20), bargap=0.18)
        st.plotly_chart(fig_c, use_container_width=True)

with col_d:
    st.markdown('<p class="section-title">⚠️ SAC 嚴重度分佈</p>',
                unsafe_allow_html=True)
    sac_d = dff["SAC_num"].dropna()
    sac_d = sac_d[sac_d.isin([1,2,3,4])]
    if sac_d.empty:
        st.info("無 SAC 資料")
    else:
        sc   = sac_d.value_counts().sort_index()
        lbls = [f"SAC {int(k)}<br>{SAC_DESC.get(int(k),'')} ({v}件)"
                for k, v in zip(sc.index, sc.values)]
        clrs = [SAC_COLORS.get(int(k), "#aaa") for k in sc.index]
        hp   = sac_d.isin(HIGH_SAC).sum() / len(sac_d) * 100

        # pull：讓 SAC 1（死亡）扇形稍微突出，強調最高嚴重度
        pull_vals = [0.06 if int(k)==1 else 0 for k in sc.index]

        fig_d = go.Figure(go.Pie(
            labels=lbls, values=sc.values, hole=0.52,
            pull=pull_vals,
            marker=dict(colors=clrs, line=dict(color="white", width=3)),
            textinfo="percent+label",
            textfont=dict(size=10, color="#1C2833", family="Arial"),
            hovertemplate="<b>%{label}</b><br>%{value} 件 (%{percent})<extra></extra>",
            direction="clockwise", sort=False,
            insidetextorientation="horizontal",
            textposition="outside",          # 所有標籤統一放外側，不被截斷
        ))
        fig_d.add_annotation(
            text=f"<b>SAC 1+2</b><br>死亡+重大<br>{hp:.2f}%",
            x=0.5, y=0.5,
            font=dict(size=12, color="#7B241C", family="Arial Bold"),
            showarrow=False)
        fig_d.update_layout(
            height=480, paper_bgcolor=PAPER_BG,
            legend=dict(orientation="h", y=-0.12, xanchor="center", x=0.5,
                        font=dict(size=10, color="#2C3E50")),
            margin=dict(t=40, b=80, l=80, r=80))   # 四周充足空間
        st.plotly_chart(fig_d, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  圖E：各類別堆疊趨勢
# ════════════════════════════════════════════════════════════
st.markdown('<div class="chart-container">', unsafe_allow_html=True)
cat_m = dff.groupby(["年月顯示","事件大類"]).size().reset_index(name="件數")
if not cat_m.empty:
    piv = cat_m.pivot(index="年月顯示", columns="事件大類", values="件數").fillna(0)
    fig_e = go.Figure()
    for cat in piv.columns:
        fig_e.add_trace(go.Bar(
            x=piv.index, y=piv[cat], name=cat,
            marker_color=CATEGORY_COLORS.get(cat, "#7F8C8D"),
            hovertemplate=f"<b>%{{x}}</b><br>{cat}：%{{y}} 件<extra></extra>"))
    fig_e.update_layout(
        title=dict(text="📊 各類別事件每月趨勢（堆疊）", font=TITLE_FONT),
        barmode="stack", height=380,
        plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right",
                    font=dict(size=11, color="#2C3E50")),
        xaxis=dict(
            title=dict(text="年月", font=AXIS_TITLE_FONT),
            tickangle=-45, showgrid=False, tickfont=AXIS_TICK_FONT,
        ),
        yaxis=dict(
            title=dict(text="事件件數", font=AXIS_TITLE_FONT),
            tickfont=AXIS_TICK_FONT,
            gridcolor=GRID_COLOR, griddash="dot",
            zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
        ),
        hovermode="x unified", margin=dict(t=60, b=60))
    st.plotly_chart(fig_e, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  圖H：通報者工作年資分析
# ════════════════════════════════════════════════════════════
SENIORITY_ORDER = ["未滿1年","1-5年","6-10年","11-15年","16-20年","21-25年","26年以上"]
SENIORITY_COLORS = ["#003f5c","#2f6a8f","#3498DB","#5dade2","#85c1e9","#aed6f1","#d6eaf8"]

st.markdown('<div class="chart-container">', unsafe_allow_html=True)
seniority_col = "通報者資料-工作年資"

if seniority_col in dff.columns:
    sen_raw = dff[seniority_col].dropna().astype(str).str.strip()
    # 只保留有效的年資標籤
    sen_raw = sen_raw[sen_raw.isin(SENIORITY_ORDER)]

    if not sen_raw.empty:
        col_h1, col_h2 = st.columns([1.3, 1])

        # ── 左：各年資層事件件數（橫向長條，按年資順序排列）
        with col_h1:
            st.markdown('<p class="section-title">👷 通報者工作年資 — 事件件數分佈</p>',
                        unsafe_allow_html=True)
            sen_cnt = (sen_raw.value_counts()
                       .reindex(SENIORITY_ORDER, fill_value=0)
                       .reset_index())
            sen_cnt.columns = ["年資", "件數"]
            sen_cnt["佔比"] = (sen_cnt["件數"] / sen_cnt["件數"].sum() * 100).round(1)

            fig_h1 = go.Figure(go.Bar(
                x=sen_cnt["件數"],
                y=sen_cnt["年資"],
                orientation="h",
                marker=dict(
                    color=SENIORITY_COLORS,
                    line=dict(width=0),
                ),
                text=[f"{v} 件 ({p:.2f}%)"
                      for v, p in zip(sen_cnt["件數"], sen_cnt["佔比"])],
                textposition="outside",
                textfont=dict(size=11, color="#1C2833", family="Arial"),
                hovertemplate="<b>%{y}</b><br>件數：%{x} 件<br>佔比：%{customdata:.2f}%<extra></extra>",
                customdata=sen_cnt["佔比"],
            ))
            fig_h1.update_layout(
                height=340,
                plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
                xaxis=dict(
                    title=dict(text="事件件數", font=AXIS_TITLE_FONT),
                    tickfont=AXIS_TICK_FONT,
                    gridcolor=GRID_COLOR, griddash="dot",
                    zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
                ),
                yaxis=dict(
                    title=dict(text="工作年資", font=AXIS_TITLE_FONT),
                    tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                    categoryorder="array",
                    categoryarray=SENIORITY_ORDER,
                    automargin=True,
                ),
                margin=dict(t=20, b=50, l=80, r=120),
            )
            st.plotly_chart(fig_h1, use_container_width=True)

        # ── 右：各年資層 SAC 嚴重度堆疊（比較不同年資的嚴重度分布）
        with col_h2:
            st.markdown('<p class="section-title">⚠️ 各年資層 SAC 嚴重度比較</p>',
                        unsafe_allow_html=True)
            sen_sac = (dff[[seniority_col, "SAC_num"]]
                       .dropna()
                       .copy())
            sen_sac[seniority_col] = sen_sac[seniority_col].astype(str).str.strip()
            sen_sac = sen_sac[
                sen_sac[seniority_col].isin(SENIORITY_ORDER) &
                sen_sac["SAC_num"].isin([1,2,3,4])
            ]

            if not sen_sac.empty:
                sac_cross = (sen_sac.groupby([seniority_col, "SAC_num"])
                             .size().reset_index(name="件數"))
                sac_piv   = (sac_cross.pivot(
                                index=seniority_col,
                                columns="SAC_num",
                                values="件數")
                             .reindex(SENIORITY_ORDER)
                             .fillna(0))

                fig_h2 = go.Figure()
                for sac_lv in [1, 2, 3, 4]:
                    if sac_lv in sac_piv.columns:
                        fig_h2.add_trace(go.Bar(
                            name=f"SAC {sac_lv} {SAC_DESC[sac_lv]}",
                            y=sac_piv.index,
                            x=sac_piv[sac_lv],
                            orientation="h",
                            marker_color=SAC_COLORS[sac_lv],
                            marker_opacity=0.85,
                            hovertemplate=(
                                f"<b>%{{y}}</b><br>"
                                f"SAC {sac_lv} {SAC_DESC[sac_lv]}：%{{x}} 件"
                                f"<extra></extra>"
                            ),
                        ))
                fig_h2.update_layout(
                    barmode="stack",
                    height=340,
                    plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
                    legend=dict(orientation="h", y=-0.22, x=0.5,
                                xanchor="center",
                                font=dict(size=10, color="#2C3E50")),
                    xaxis=dict(
                        title=dict(text="事件件數", font=AXIS_TITLE_FONT),
                        tickfont=AXIS_TICK_FONT,
                        gridcolor=GRID_COLOR, griddash="dot",
                    ),
                    yaxis=dict(
                        title=dict(text="工作年資", font=AXIS_TITLE_FONT),
                        tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                        categoryorder="array",
                        categoryarray=SENIORITY_ORDER,
                        automargin=True,
                    ),
                    margin=dict(t=20, b=80, l=80, r=20),
                )
                st.plotly_chart(fig_h2, use_container_width=True)

    else:
        st.info("目前篩選條件下無工作年資資料。")
else:
    st.markdown(f'<div style="background:#FFF3CD;border-left:4px solid #F39C12;padding:10px 14px;border-radius:4px;color:#7D4700;font-size:13px">⚠️ 找不到欄位：{seniority_col}</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  🔬 診斷特徵分析
#  資料：df_all["診斷分類"]  + 傷害程度
#  篩選器：時間區間 + 側邊欄科別篩選器
# ════════════════════════════════════════════════════════════

# 診斷分類顯示順序與配色
DX_ORDER = ["思覺失調/精神病","雙相/躁症","憂鬱症","失智症","帕金森氏症",
            "腦血管病","骨折相關","糖尿病","腎病","肝病",
            "心臟病","呼吸系統","腫瘤/癌症","其他"]
DX_COLORS = {
    "思覺失調/精神病": "#7B241C",
    "雙相/躁症":      "#C0392B",
    "憂鬱症":         "#E74C3C",
    "失智症":         "#E59866",
    "帕金森氏症":      "#F39C12",
    "腦血管病":        "#2471A3",
    "骨折相關":        "#1ABC9C",
    "糖尿病":          "#27AE60",
    "腎病":            "#117A65",
    "肝病":            "#7D6608",
    "心臟病":          "#6C3483",
    "呼吸系統":        "#2C3E50",
    "腫瘤/癌症":       "#5D6D7E",
    "其他":            "#AEB6BF",
}
# 傷害程度顏色（與科別分析共用）
DX_INJ_ORDER  = ["無傷害","輕度","中度","重度","極重度","無法判定傷害嚴重程度"]
DX_INJ_COLORS = {
    "無傷害":              "#1E8449",
    "輕度":               "#F39C12",
    "中度":               "#E67E22",
    "重度":               "#C0392B",
    "極重度":              "#7B241C",
    "無法判定傷害嚴重程度":  "#7F8C8D",
}
INURY_COL_DX = "病人/住民-事件發生後對病人健康的影響程度"
# 中度以上傷害：中度、重度、極重度、死亡
HIGH_INJURY   = ["中度","重度","極重度","死亡"]

st.markdown('<div class="chart-container">', unsafe_allow_html=True)
dept_label = sel_dept if sel_dept != "全部科別" else "全院"
st.markdown(f"""
<div style='background:linear-gradient(135deg,#1a2e3d,#2C3E50);
            padding:14px 20px;border-radius:8px;margin-bottom:16px'>
  <h3 style='color:#FFFFFF;margin:0;font-size:17px;font-weight:700'>
    🔬 診斷特徵分析
  </h3>
  <p style='color:#AED6F1;margin:4px 0 0;font-size:11px'>
    資料期間：{start_m} ～ {end_m}　科別：{dept_label}　共 {len(dff_dx)} 筆
  </p>
</div>""", unsafe_allow_html=True)

if dff_dx.empty or "診斷分類" not in dff_dx.columns:
    st.info("目前篩選條件下無診斷資料。")
else:
    dx_inj = dff_dx[["診斷分類", INURY_COL_DX]].copy()

    # ── 圖1：Treemap（方塊大小=件數，顏色=中度以上傷害率）──
    st.markdown('<p class="section-title">① 診斷分類 Treemap（方塊大小=件數，顏色深=傷害率高）</p>',
                unsafe_allow_html=True)

    dx_summary = []
    for dx in DX_ORDER:
        sub  = dx_inj[dx_inj["診斷分類"] == dx]
        n    = len(sub)
        if n == 0:
            continue
        hi   = sub[INURY_COL_DX].isin(HIGH_INJURY).sum()
        rate = round(hi / n * 100, 1)
        dx_summary.append({"診斷分類": dx, "件數": n,
                            "中度以上傷害件數": hi, "傷害率": rate})
    df_dx_sum = pd.DataFrame(dx_summary)

    if not df_dx_sum.empty:
        fig_dx1 = go.Figure(go.Treemap(
            labels=df_dx_sum["診斷分類"],
            parents=["診斷分類"] * len(df_dx_sum),
            values=df_dx_sum["件數"],
            customdata=df_dx_sum[["件數","中度以上傷害件數","傷害率"]].values,
            hovertemplate=(
                "<b>%{label}</b><br>"
                "件數：%{customdata[0]}<br>"
                "中度以上傷害：%{customdata[1]} 件<br>"
                "傷害率：%{customdata[2]:.2f}%<extra></extra>"
            ),
            marker=dict(
                colors=df_dx_sum["傷害率"],
                colorscale=[
                    [0.0, "#D5E8D4"],   # 低傷害率→淺綠
                    [0.3, "#FFE6CC"],   # 中低→淺橙
                    [0.6, "#F39C12"],   # 中→橙
                    [1.0, "#7B241C"],   # 高→深紅
                ],
                showscale=True,
                colorbar=dict(
                    title=dict(text="中度以上<br>傷害率(%)",
                               font=dict(size=11, color="#1C2833")),
                    tickfont=dict(size=10, color="#2C3E50"),
                    thickness=14, len=0.7,
                ),
                line=dict(width=2, color="white"),
            ),
            textfont=dict(size=13, color="white", family="Arial Bold"),
            textinfo="label+value",
        ))
        fig_dx1.update_layout(
            height=420, paper_bgcolor=PAPER_BG,
            margin=dict(t=10, b=10, l=10, r=120),
        )
        st.plotly_chart(fig_dx1, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── 圖2：100% 堆疊橫條圖（傷害程度分布，件數>=3）────────
    st.markdown('<p class="section-title">② 各診斷分類傷害程度分布（100% 堆疊，件數 ≥ 3）</p>',
                unsafe_allow_html=True)

    dx_valid = dx_inj.groupby("診斷分類").filter(
        lambda x: len(x) >= 3)
    if not dx_valid.empty:
        inj2 = (dx_valid.groupby(["診斷分類", INURY_COL_DX])
                .size().reset_index(name="件數"))
        inj2_piv = (inj2.pivot(index="診斷分類",
                                columns=INURY_COL_DX, values="件數")
                    .fillna(0))
        # 排序：依總件數升序
        inj2_piv["_tot"] = inj2_piv.sum(axis=1)
        inj2_piv = inj2_piv.sort_values("_tot", ascending=True)
        tot2     = inj2_piv["_tot"].astype(int)
        inj2_piv = inj2_piv.drop(columns="_tot")
        # 轉百分比
        inj2_pct = inj2_piv.div(inj2_piv.sum(axis=1), axis=0) * 100

        fig_dx2 = go.Figure()
        for inj_lv in DX_INJ_ORDER:
            if inj_lv in inj2_pct.columns:
                fig_dx2.add_trace(go.Bar(
                    name=inj_lv,
                    y=inj2_pct.index,
                    x=inj2_pct[inj_lv].round(1),
                    orientation="h",
                    marker_color=DX_INJ_COLORS[inj_lv],
                    marker_opacity=0.85,
                    hovertemplate=(
                        f"<b>%{{y}}</b><br>{inj_lv}：%{{x:.1f}}%<extra></extra>"
                    ),
                ))
        # 右側 n= 標籤
        fig_dx2.add_trace(go.Scatter(
            y=inj2_pct.index,
            x=[102] * len(inj2_pct),
            mode="text",
            text=["n=" + str(t) for t in tot2],
            textfont=dict(size=10, color="#2C3E50", family="Arial"),
            showlegend=False, hoverinfo="skip",
        ))
        fig_dx2.update_layout(
            barmode="stack",
            height=max(320, len(inj2_pct) * 38 + 80),
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center",
                        font=dict(size=11, color="#2C3E50")),
            xaxis=dict(
                title=dict(text="百分比 (%)", font=AXIS_TITLE_FONT),
                tickfont=AXIS_TICK_FONT, range=[0, 115],
                gridcolor=GRID_COLOR, griddash="dot", ticksuffix="%",
            ),
            yaxis=dict(
                title=dict(text="診斷分類", font=AXIS_TITLE_FONT),
                tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                automargin=True,
            ),
            margin=dict(t=40, b=60, l=100, r=60),
            hovermode="y unified",
        )
        st.plotly_chart(fig_dx2, use_container_width=True)



st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  圖F：各單位熱力圖
# ════════════════════════════════════════════════════════════
st.markdown('<div class="chart-container">', unsafe_allow_html=True)
top_u = dff["單位"].value_counts().head(15).index.tolist()
um = (dff[dff["單位"].isin(top_u)]
      .groupby(["年月顯示","單位"]).size().reset_index(name="件數"))
if not um.empty:
    hp_piv = um.pivot(index="單位", columns="年月顯示", values="件數").fillna(0)
    fig_f = go.Figure(go.Heatmap(
        z=hp_piv.values, x=hp_piv.columns.tolist(), y=hp_piv.index.tolist(),
        colorscale=[
            [0.0,"#F4F6F6"],[0.35,"#E6B0AA"],
            [0.70,"#C0392B"],[1.0,"#78281F"],
        ],
        hovertemplate="<b>%{y}</b><br>%{x}<br>件數：%{z:.0f}<extra></extra>",
        colorbar=dict(
            title=dict(text="件數", font=dict(size=12, color="#1C2833")),
            tickfont=dict(size=10, color="#2C3E50"),
            thickness=15, len=0.8),
        xgap=1, ygap=1))
    fig_f.update_layout(
        title=dict(text="🗺️ 各單位每月事件熱力圖（Top 15）", font=TITLE_FONT),
        height=460, paper_bgcolor=PAPER_BG,
        xaxis=dict(
            title=dict(text="年月", font=AXIS_TITLE_FONT),
            tickangle=-45, tickfont=dict(size=9, color="#2C3E50"),
            showgrid=False,
        ),
        yaxis=dict(
            title=dict(text="病房 / 單位", font=AXIS_TITLE_FONT),
            tickfont=dict(size=11, color="#2C3E50"),
        ),
        margin=dict(t=60, b=80, l=90, r=90))
    st.plotly_chart(fig_f, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)


# ── 明細表 ───────────────────────────────────────────────────
with st.expander("📋 查看事件明細資料表", expanded=False):
    cols = [c for c in [
        "編號","事件大類","事件類別","發生日期","年月","單位","SAC_num",
        "發生時段","時段標準","發生者資料-年齡","發生者資料-性別",
        "病人/住民-事件發生後對病人健康的影響程度(彙總)",
    ] if c in dff.columns]
    df_show = dff[cols].copy().rename(columns={
        "SAC_num":"SAC","事件大類":"類別",
        "發生者資料-年齡":"年齡","發生者資料-性別":"性別",
        "病人/住民-事件發生後對病人健康的影響程度(彙總)":"影響程度"})

    def _hl(val):
        if val in [1, 1.0]:
            return "background-color:#FADBD8;color:#7B241C;font-weight:bold"
        elif val in [2, 2.0]:
            return "background-color:#FDEBD0;color:#784212;font-weight:bold"
        elif val in [3, 3.0]:
            return "background-color:#FEF9E7;color:#6D4C00"
        return "color:#1C2833"

    st.dataframe(df_show.style.applymap(_hl, subset=["SAC"]),
                 use_container_width=True, height=400)
    st.caption("🔴 SAC 1 死亡　🟠 SAC 2 重大傷害　🟡 SAC 3 輕中度　⬜ SAC 4 無傷害")




# ════════════════════════════════════════════════════════════
#  📋 科別深度分析（跌倒事件）
#  資料來源：109-113跌倒工作表 merge 全部工作表
#  時間區間與主篩選器連動
# ════════════════════════════════════════════════════════════
st.markdown('<div class="chart-container">', unsafe_allow_html=True)
st.markdown("""
<div style='background:linear-gradient(135deg,#1a2e3d,#2C3E50);
            padding:14px 20px;border-radius:8px;margin-bottom:16px'>
  <h3 style='color:#FFFFFF;margin:0;font-size:17px;font-weight:700'>
    📋 跌倒事件 — 科別深度分析
  </h3>
  <p style='color:#AED6F1;margin:4px 0 0;font-size:11px'>
    資料期間：{start_m} ～ {end_m}　共 {n_fall} 件跌倒事件
  </p>
</div>
""".format(start_m=start_m, end_m=end_m, n_fall=len(dff_fall)),
unsafe_allow_html=True)

DEPT_COL    = "病人/住民-所在科別"
INJURY_COL  = "病人/住民-事件發生後對病人健康的影響程度"
HIGHRISK_COL= "跌倒事件發生對象-事件發生前是否為跌倒高危險群"
MOBILITY_COL= "跌倒事件發生對象-事件發生前的獨立活動能力"
CONSCI_COL  = "跌倒事件發生對象-當事人當時意識狀況"
GETUP_COL   = "可能原因-高危險群病人執意自行下床或活動"

# 傷害程度顏色對應（由輕到重）
INJURY_ORDER  = ["無傷害", "輕度", "中度", "重度", "極重度", "無法判定傷害嚴重程度"]
INJURY_COLORS_MAP = {
    "無傷害":              "#1E8449",
    "輕度":               "#F39C12",
    "中度":               "#E67E22",
    "重度":               "#C0392B",
    "極重度":              "#7B241C",
    "無法判定傷害嚴重程度":  "#7F8C8D",
}

if not dff_fall.empty and DEPT_COL in dff_fall.columns:

    # 只取件數 >= 5 的科別
    dept_counts = dff_fall[DEPT_COL].value_counts()
    valid_depts = dept_counts[dept_counts >= 5].index.tolist()
    df_dept = dff_fall[dff_fall[DEPT_COL].isin(valid_depts)].copy()

    if df_dept.empty:
        st.info("目前期間內無足夠資料進行科別分析（各科需至少 5 件）。")
    else:
        # ── 圖1：堆疊百分比橫條圖（傷害程度）─────────────────
        st.markdown('<p class="section-title">① 各科別傷害程度分布（堆疊百分比）</p>',
                    unsafe_allow_html=True)

        inj_cross = (df_dept.groupby([DEPT_COL, INJURY_COL])
                     .size().reset_index(name="件數"))
        inj_piv   = (inj_cross.pivot(index=DEPT_COL, columns=INJURY_COL, values="件數")
                     .fillna(0))
        # 計算各科總件數並排序
        inj_piv["_total"] = inj_piv.sum(axis=1)
        inj_piv = inj_piv.sort_values("_total", ascending=True)
        totals   = inj_piv["_total"].astype(int)
        inj_piv  = inj_piv.drop(columns="_total")
        # 轉換為百分比
        inj_pct  = inj_piv.div(inj_piv.sum(axis=1), axis=0) * 100

        fig_dept1 = go.Figure()
        for injury in INJURY_ORDER:
            if injury in inj_pct.columns:
                fig_dept1.add_trace(go.Bar(
                    name=injury,
                    y=inj_pct.index,
                    x=inj_pct[injury].round(1),
                    orientation="h",
                    marker_color=INJURY_COLORS_MAP[injury],
                    marker_opacity=0.85,
                    hovertemplate=(
                        f"<b>%{{y}}</b><br>{injury}：%{{x:.1f}}%"
                        f"<extra></extra>"
                    ),
                ))
        # 右側總件數標籤
        fig_dept1.add_trace(go.Scatter(
            y=inj_pct.index,
            x=[102] * len(inj_pct),
            mode="text",
            text=["n=" + str(t) for t in totals],
            textfont=dict(size=10, color="#2C3E50", family="Arial"),
            showlegend=False, hoverinfo="skip",
        ))
        fig_dept1.update_layout(
            barmode="stack",
            height=max(320, len(inj_pct) * 38 + 80),
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center",
                        font=dict(size=11, color="#2C3E50")),
            xaxis=dict(
                title=dict(text="百分比 (%)", font=AXIS_TITLE_FONT),
                tickfont=AXIS_TICK_FONT,
                range=[0, 115],
                gridcolor=GRID_COLOR, griddash="dot",
                ticksuffix="%",
            ),
            yaxis=dict(
                title=dict(text="科別", font=AXIS_TITLE_FONT),
                tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                automargin=True,
            ),
            margin=dict(t=40, b=60, l=90, r=60),
            hovermode="y unified",
        )
        st.plotly_chart(fig_dept1, use_container_width=True)

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── 圖2：分組橫條圖（三項特徵比率比較）────────────────
        st.markdown('<p class="section-title">② 各科別風險特徵比率比較</p>',
                    unsafe_allow_html=True)

        # 排序依總件數降序（讓大科在上方）
        dept_order = dept_counts[dept_counts >= 5].sort_values(ascending=True).index.tolist()

        feat_data = []
        for dept in dept_order:
            sub = dff_fall[dff_fall[DEPT_COL] == dept]
            n   = len(sub)
            if n == 0:
                continue
            # ① 跌倒高危險群佔比（「是」）
            r1 = (sub[HIGHRISK_COL] == "是").sum() / n * 100
            # ② 需協助或完全依賴活動者佔比
            r2 = (sub[MOBILITY_COL].isin(["需協助","完全依賴"])).sum() / n * 100
            # ③ 意識混亂或嗜睡佔比
            r3 = (sub[CONSCI_COL].isin(["意識混亂","嗜睡"])).sum() / n * 100
            feat_data.append({"科別": dept, "跌倒高危險群": r1,
                               "需協助/完全依賴": r2, "意識混亂/嗜睡": r3})

        df_feat = pd.DataFrame(feat_data)

        FEAT_COLORS = {
            "跌倒高危險群":    "#C0392B",
            "需協助/完全依賴": "#3498DB",
            "意識混亂/嗜睡":  "#F39C12",
        }
        fig_dept2 = go.Figure()
        for feat, clr in FEAT_COLORS.items():
            fig_dept2.add_trace(go.Bar(
                name=feat,
                y=df_feat["科別"],
                x=df_feat[feat].round(1),
                orientation="h",
                marker_color=clr,
                marker_opacity=0.80,
                hovertemplate=f"<b>%{{y}}</b><br>{feat}：%{{x:.1f}}%<extra></extra>",
            ))
        fig_dept2.update_layout(
            barmode="group",
            height=max(340, len(df_feat) * 55 + 80),
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center",
                        font=dict(size=11, color="#2C3E50")),
            xaxis=dict(
                title=dict(text="佔比 (%)", font=AXIS_TITLE_FONT),
                tickfont=AXIS_TICK_FONT,
                range=[0, 110],
                gridcolor=GRID_COLOR, griddash="dot",
                ticksuffix="%",
            ),
            yaxis=dict(
                title=dict(text="科別", font=AXIS_TITLE_FONT),
                tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                automargin=True,
                categoryorder="array",
                categoryarray=dept_order,
            ),
            margin=dict(t=40, b=60, l=90, r=30),
            hovermode="y unified",
        )
        st.plotly_chart(fig_dept2, use_container_width=True)

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── 圖3：執意自行下床比率（由高到低，超過40%紅色）────
        st.markdown('<p class="section-title">③ 各科別「執意自行下床」比率（由高到低）</p>',
                    unsafe_allow_html=True)

        getup_data = []
        for dept in valid_depts:
            sub = dff_fall[dff_fall[DEPT_COL] == dept]
            n   = len(sub)
            if n == 0:
                continue
            rate = sub[GETUP_COL].eq(1).sum() / n * 100
            getup_data.append({"科別": dept, "比率": round(rate, 1), "總件數": n})

        df_getup = (pd.DataFrame(getup_data)
                    .sort_values("比率", ascending=True))   # 水平圖低→高由下而上

        bar_colors = [
            "#C0392B" if r >= 40 else "#3498DB"
            for r in df_getup["比率"]
        ]
        fig_dept3 = go.Figure(go.Bar(
            y=df_getup["科別"],
            x=df_getup["比率"],
            orientation="h",
            marker_color=bar_colors,
            marker_opacity=0.85,
            text=[f"{r:.2f}%" for r in df_getup["比率"]],
            textposition="outside",
            textfont=dict(size=11, color="#1C2833", family="Arial"),
            customdata=df_getup["總件數"],
            hovertemplate=(
                "<b>%{y}</b><br>執意自行下床：%{x:.2f}%<br>"
                "科別總件數：%{customdata} 件<extra></extra>"
            ),
        ))
        # 40% 警戒線
        fig_dept3.add_vline(
            x=40, line_dash="dash", line_color="#E74C3C", line_width=2,
            annotation_text="  40% 警戒線",
            annotation_position="top right",
            annotation_font=dict(size=11, color="#E74C3C", family="Arial Bold"),
        )
        fig_dept3.update_layout(
            height=max(300, len(df_getup) * 40 + 80),
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            xaxis=dict(
                title=dict(text="執意自行下床比率 (%)", font=AXIS_TITLE_FONT),
                tickfont=AXIS_TICK_FONT,
                range=[0, max(df_getup["比率"].max() * 1.25, 55)],
                gridcolor=GRID_COLOR, griddash="dot",
                ticksuffix="%",
            ),
            yaxis=dict(
                title=dict(text="科別", font=AXIS_TITLE_FONT),
                tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                automargin=True,
            ),
            margin=dict(t=40, b=60, l=90, r=60),
        )
        st.plotly_chart(fig_dept3, use_container_width=True)

        # 超過40%提示
        high_depts = df_getup[df_getup["比率"] >= 40]["科別"].tolist()
        if high_depts:
            st.markdown(
                f'<div style="background:#FFF3CD;border-left:4px solid #F39C12;'
                f'padding:10px 14px;border-radius:4px;color:#7D4700;font-size:13px">'
                f'⚠️ 以下科別執意自行下床比率超過 40%，建議加強衛教與防跌措施：'
                f'<b>{"、".join(high_depts)}</b></div>',
                unsafe_allow_html=True)

else:
    st.info("目前期間內無跌倒事件資料，或科別欄位缺失。")

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="chart-container">', unsafe_allow_html=True)
st.markdown('<p class="section-title">🏆 各病房 / 單位事件件數排名（Top 20）</p>',
            unsafe_allow_html=True)

unit_stats = (dff.groupby("單位")
              .agg(總件數=("編號","count"),
                   高嚴重度=("SAC_num", lambda x: x.isin(HIGH_SAC).sum()))
              .reset_index()
              .sort_values("總件數", ascending=True)
              .tail(20))

if not unit_stats.empty:
    unit_stats["高嚴重度佔比"] = (
        unit_stats["高嚴重度"] / unit_stats["總件數"] * 100).round(1)
    fig_g = go.Figure()
    fig_g.add_trace(go.Bar(
        y=unit_stats["單位"], x=unit_stats["總件數"],
        orientation="h", name="總件數",
        marker_color="#3498DB", marker_opacity=0.45,
        hovertemplate="<b>%{y}</b><br>總件數：%{x} 件<extra></extra>"))
    fig_g.add_trace(go.Bar(
        y=unit_stats["單位"], x=unit_stats["高嚴重度"],
        orientation="h", name="SAC 1+2（死亡+重大傷害）",
        marker_color="#E74C3C", marker_opacity=0.85,
        customdata=unit_stats["高嚴重度佔比"],
        hovertemplate=(
            "<b>%{y}</b><br>死亡+重大傷害：%{x} 件<br>"
            "佔比：%{customdata:.2f}%<extra></extra>")))
    fig_g.add_trace(go.Scatter(
        y=unit_stats["單位"], x=unit_stats["總件數"],
        mode="text", text=unit_stats["總件數"].astype(str) + " 件",
        textposition="middle right",
        textfont=dict(size=10, color="#1C2833", family="Arial"),
        showlegend=False, hoverinfo="skip"))
    fig_g.update_layout(
        barmode="overlay",
        height=max(420, len(unit_stats) * 28 + 120),
        plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        legend=dict(orientation="h", y=1.06, x=1, xanchor="right",
                    font=dict(size=11, color="#2C3E50")),
        xaxis=dict(
            title=dict(text="件數", font=AXIS_TITLE_FONT),
            tickfont=AXIS_TICK_FONT,
            gridcolor=GRID_COLOR, griddash="dot",
            zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
        ),
        yaxis=dict(
            title=dict(text="病房 / 單位", font=AXIS_TITLE_FONT),
            tickfont=dict(size=11, color="#2C3E50", family="Arial"),
            automargin=True,
        ),
        margin=dict(t=50, b=60, l=90, r=90),
        hovermode="y unified")
    st.plotly_chart(fig_g, use_container_width=True)

    top10 = (unit_stats.sort_values("總件數", ascending=False)
             .head(10).reset_index(drop=True))
    top10.index += 1
    top10 = top10.rename(columns={
        "單位":"病房/單位","高嚴重度":"SAC 1+2 件數",
        "高嚴重度佔比":"死亡+重大佔比(%)"})
    st.caption("📋 Top 10 單位詳細數據")
    st.dataframe(top10, use_container_width=True, height=310)
st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
#  📝 事件說明特徵萃取分析
#  資料：dff_fall（已含 extract_fall_features 布林欄位）
#  篩選器：時間區間 + 科別篩選器連動
# ════════════════════════════════════════════════════════════
FALL_FEAT_NAMES = [
    "地點_床邊下床","地點_浴廁","地點_走廊行走","地點_椅子輪椅",
    "機轉_滑倒","機轉_頭暈血壓低","機轉_自行起身未告知","機轉_站不穩腳軟",
    "發現_護理人員巡視","發現_聲響",
    "病況_精神症狀","病況_約束相關",
]
# 依科別篩選 dff_fall（繼承時間篩選）
if sel_dept != "全部科別":
    dff_fall_feat = dff_fall[
        dff_fall["病人/住民-所在科別"] == sel_dept].copy()
else:
    dff_fall_feat = dff_fall.copy()

st.markdown('<div class="chart-container">', unsafe_allow_html=True)
dept_label_feat = sel_dept if sel_dept != "全部科別" else "全院"
st.markdown(f"""
<div style='background:linear-gradient(135deg,#1a2e3d,#2C3E50);
            padding:14px 20px;border-radius:8px;margin-bottom:16px'>
  <h3 style='color:#FFFFFF;margin:0;font-size:17px;font-weight:700'>
    📝 事件說明特徵萃取分析
  </h3>
  <p style='color:#AED6F1;margin:4px 0 0;font-size:11px'>
    資料期間：{start_m} ～ {end_m}　科別：{dept_label_feat}
    　共 {len(dff_fall_feat)} 件跌倒事件
  </p>
</div>""", unsafe_allow_html=True)

feat_cols_exist = [f for f in FALL_FEAT_NAMES if f in dff_fall_feat.columns]

if dff_fall_feat.empty or not feat_cols_exist:
    st.info("目前篩選條件下無跌倒事件說明資料。")
else:
    n_total = len(dff_fall_feat)

    # ── 圖1：QCC 柏拉圖（遞減排序 + 80/20 累積折線 + 點擊下鑽）─
    st.markdown('<p class="section-title">① 跌倒特徵柏拉圖（QCC 80/20 法則）</p>',
                unsafe_allow_html=True)
    st.caption("💡 點擊任一長條，下方將顯示該特徵在各病房的分佈（RCA 根本原因分析）")

    feat_counts = []
    for feat in feat_cols_exist:
        cnt = int(dff_fall_feat[feat].sum())
        pct = round(cnt / n_total * 100, 2)
        feat_counts.append({"特徵": feat, "件數": cnt, "佔比": pct})
    df_feat_cnt = (pd.DataFrame(feat_counts)
                   .sort_values("件數", ascending=False)   # 柏拉圖遞減
                   .reset_index(drop=True))

    # 累積百分比
    df_feat_cnt["累積佔比"] = df_feat_cnt["件數"].cumsum() / df_feat_cnt["件數"].sum() * 100

    # 柏拉圖顏色：80%前=深藍（重要），80%後=淺藍
    cutoff_idx = int((df_feat_cnt["累積佔比"] <= 80).sum())
    bar_colors = ["#1A5276" if i <= cutoff_idx else "#85C1E9"
                  for i in range(len(df_feat_cnt))]

    fig_pareto = go.Figure()
    # 長條圖（主Y軸）
    fig_pareto.add_trace(go.Bar(
        x=df_feat_cnt["特徵"],
        y=df_feat_cnt["件數"],
        name="件數",
        marker_color=bar_colors,
        marker_opacity=0.88,
        text=df_feat_cnt["件數"],
        textposition="outside",
        textfont=dict(size=10, color="#1C2833"),
        customdata=df_feat_cnt[["佔比","累積佔比"]].values,
        hovertemplate=(
            "<b>%{x}</b><br>件數：%{y}<br>"
            "佔比：%{customdata[0]:.2f}%<br>"
            "累積：%{customdata[1]:.2f}%<extra></extra>"
        ),
        yaxis="y",
    ))
    # 累積折線（次Y軸）
    fig_pareto.add_trace(go.Scatter(
        x=df_feat_cnt["特徵"],
        y=df_feat_cnt["累積佔比"],
        name="累積百分比",
        mode="lines+markers",
        line=dict(color="#E74C3C", width=2.5),
        marker=dict(size=7, color="#E74C3C", symbol="circle"),
        hovertemplate="<b>%{x}</b><br>累積：%{y:.2f}%<extra></extra>",
        yaxis="y2",
    ))
    # 80% 基準線
    fig_pareto.add_hline(
        y=80, line_dash="dash", line_color="#C0392B", line_width=1.8,
        annotation_text=" 80% 法則基準線",
        annotation_position="top left",
        annotation_font=dict(size=11, color="#C0392B", family="Arial Bold"),
        secondary_y=True if False else False,
        yref="y2",
    )
    fig_pareto.update_layout(
        height=440,
        plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right",
                    font=dict(size=11, color="#2C3E50")),
        xaxis=dict(
            title=dict(text="跌倒特徵項目", font=AXIS_TITLE_FONT),
            tickfont=dict(size=10, color="#2C3E50", family="Arial"),
            tickangle=-30, showgrid=False,
        ),
        yaxis=dict(
            title=dict(text="件數", font=AXIS_TITLE_FONT),
            tickfont=AXIS_TICK_FONT,
            gridcolor=GRID_COLOR, griddash="dot",
            zeroline=True, zerolinecolor=ZERO_LINE_COLOR,
        ),
        yaxis2=dict(
            title=dict(text="累積百分比 (%)", font=AXIS_TITLE_FONT),
            tickfont=AXIS_TICK_FONT,
            overlaying="y", side="right",
            range=[0, 110], ticksuffix="%",
            showgrid=False,
        ),
        margin=dict(t=50, b=80, l=60, r=70),
        hovermode="x unified",
        bargap=0.25,
    )

    # 點擊事件 → session_state 存選中特徵
    pareto_event = st.plotly_chart(
        fig_pareto, use_container_width=True,
        on_select="rerun", key="pareto_select"
    )

    # ── 下鑽：選中特徵後顯示各單位分佈 ────────────────────────
    selected_feat = None
    if pareto_event and pareto_event.get("selection"):
        pts = pareto_event["selection"].get("points", [])
        if pts:
            selected_feat = pts[0].get("x")

    if selected_feat and selected_feat in dff_fall_feat.columns:
        st.markdown(f"""
<div style='background:#EBF5FB;border-left:4px solid #2E86C1;
            padding:10px 14px;border-radius:4px;margin:8px 0 12px 0;
            font-size:13px;color:#1A5276'>
  🔍 <b>下鑽分析：「{selected_feat}」各病房 / 單位件數排名 Top 20</b>
  　｜ RCA 根本原因分析
</div>""", unsafe_allow_html=True)

        drill_df = dff_fall_feat[dff_fall_feat[selected_feat] == True].copy()
        if "單位" not in drill_df.columns and "病人/住民-所在科別" in drill_df.columns:
            drill_df = drill_df.rename(columns={"病人/住民-所在科別": "單位"})

        unit_col = "單位" if "單位" in drill_df.columns else drill_df.columns[0]
        unit_cnt = (drill_df[unit_col].value_counts()
                    .head(20).reset_index()
                    .rename(columns={"index": unit_col, unit_col: "件數",
                                     "count": "件數"}))
        # pandas value_counts() 回傳格式相容
        if "件數" not in unit_cnt.columns:
            unit_cnt.columns = [unit_col, "件數"]
        unit_cnt = unit_cnt.sort_values("件數", ascending=True)
        total_feat = int(dff_fall_feat[selected_feat].sum())

        fig_drill = go.Figure(go.Bar(
            x=unit_cnt["件數"],
            y=unit_cnt[unit_col],
            orientation="h",
            marker_color="#1A5276",
            marker_opacity=0.82,
            text=[f"{v} 件 ({v/total_feat*100:.1f}%)" for v in unit_cnt["件數"]],
            textposition="outside",
            textfont=dict(size=10, color="#1C2833", family="Arial"),
            hovertemplate="<b>%{y}</b>：%{x} 件<extra></extra>",
        ))
        fig_drill.update_layout(
            height=max(280, len(unit_cnt) * 32 + 80),
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            xaxis=dict(title=dict(text="件數", font=AXIS_TITLE_FONT),
                       tickfont=AXIS_TICK_FONT,
                       gridcolor=GRID_COLOR, griddash="dot",
                       range=[0, unit_cnt["件數"].max() * 1.35]),
            yaxis=dict(title=dict(text=unit_col, font=AXIS_TITLE_FONT),
                       tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                       automargin=True),
            margin=dict(t=20, b=40, l=90, r=120),
        )
        st.plotly_chart(fig_drill, use_container_width=True)
        st.caption(f"共 {total_feat} 件具備「{selected_feat}」特徵，顯示 Top {len(unit_cnt)} 個單位")
    elif not selected_feat:
        st.caption("👆 點擊上方柏拉圖的任一長條，即可下鑽查看該特徵的單位分佈")

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── 圖2：「自行起身未告知」各科別比率（分組橫條）─────────
    st.markdown('<p class="section-title">② 「自行起身未告知」各科別比率比較</p>',
                unsafe_allow_html=True)

    FOCUS_DEPTS = ["精神科","外科","內科","復健科","護理之家","骨科","其他"]
    DEPT_COLORS_MAP = {
        "精神科":  "#C0392B",
        "外科":    "#3498DB",
        "內科":    "#27AE60",
        "復健科":  "#F39C12",
        "護理之家": "#8E44AD",
        "骨科":    "#2C3E50",
        "其他":    "#7F8C8D",
    }

    getup_feat = "機轉_自行起身未告知"
    dept_col_f = "病人/住民-所在科別"
    dept_rate  = []
    for dept in FOCUS_DEPTS:
        sub = dff_fall[  # 用全院跌倒資料（只套時間篩選）
            dff_fall[dept_col_f] == dept]
        n = len(sub)
        if n < 3:
            continue
        rate = round(sub[getup_feat].sum() / n * 100, 1) if getup_feat in sub else 0
        dept_rate.append({"科別": dept, "比率": rate, "總件數": n})

    df_dept_rate = pd.DataFrame(dept_rate).sort_values("比率", ascending=True)

    if not df_dept_rate.empty:
        bar_clrs2 = [DEPT_COLORS_MAP.get(d, "#7F8C8D")
                     for d in df_dept_rate["科別"]]
        warn_text = ["⚠️" if r >= 40 else "" for r in df_dept_rate["比率"]]

        fig_fe2 = go.Figure()
        fig_fe2.add_trace(go.Bar(
            y=df_dept_rate["科別"],
            x=df_dept_rate["比率"],
            orientation="h",
            marker_color=bar_clrs2,
            marker_opacity=0.85,
            text=[f"{r:.2f}% {w}"
                  for r, w in zip(df_dept_rate["比率"], warn_text)],
            textposition="outside",
            textfont=dict(size=11, color="#1C2833", family="Arial"),
            customdata=df_dept_rate["總件數"],
            hovertemplate=(
                "<b>%{y}</b><br>自行起身未告知：%{x:.2f}%<br>"
                "科別總件數：%{customdata} 件<extra></extra>"
            ),
        ))
        fig_fe2.add_vline(
            x=40, line_dash="dash", line_color="#E74C3C", line_width=2,
            annotation_text="  40% 警戒線",
            annotation_position="top right",
            annotation_font=dict(size=11, color="#E74C3C", family="Arial Bold"),
        )
        fig_fe2.update_layout(
            height=max(300, len(df_dept_rate) * 52 + 80),
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            xaxis=dict(
                title=dict(text="自行起身未告知 比率 (%)", font=AXIS_TITLE_FONT),
                tickfont=AXIS_TICK_FONT,
                range=[0, max(df_dept_rate["比率"].max() * 1.35, 55)],
                gridcolor=GRID_COLOR, griddash="dot", ticksuffix="%",
            ),
            yaxis=dict(
                title=dict(text="科別", font=AXIS_TITLE_FONT),
                tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                automargin=True,
            ),
            margin=dict(t=40, b=60, l=80, r=120),
        )
        st.plotly_chart(fig_fe2, use_container_width=True)

        warn_depts = df_dept_rate[df_dept_rate["比率"] >= 40]["科別"].tolist()
        if warn_depts:
            st.markdown(
                f'<div style="background:#FFF3CD;border-left:4px solid #F39C12;'
                f'padding:10px 14px;border-radius:4px;color:#7D4700;font-size:13px">'
                f'⚠️ <b>{"、".join(warn_depts)}</b> 的「自行起身未告知」比率超過 40%，'
                f'建議加強病人安全教育與護理巡視頻率。</div>',
                unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── 圖3：地點 × 傷害程度 交叉熱力圖 ────────────────────
    st.markdown('<p class="section-title">③ 發生地點 × 傷害程度 交叉熱力圖</p>',
                unsafe_allow_html=True)

    LOC_FEATS = {
        "床邊下床": "地點_床邊下床",
        "浴廁":    "地點_浴廁",
        "走廊行走": "地點_走廊行走",
        "椅子輪椅": "地點_椅子輪椅",
    }
    INJ_ORDER_HM = ["無傷害","輕度","中度","重度","極重度","無法判定傷害嚴重程度"]
    inj_col_f    = "病人/住民-事件發生後對病人健康的影響程度"

    # 建立地點欄位：取第一個命中的地點，未命中標「其他地點」
    def get_location(row):
        for lbl, feat in LOC_FEATS.items():
            if feat in row and row[feat]:
                return lbl
        return None   # 排除無地點標記的資料

    dff_fall_feat2 = dff_fall_feat.copy()
    dff_fall_feat2["地點"] = dff_fall_feat2.apply(get_location, axis=1)
    hm_data = dff_fall_feat2[
        dff_fall_feat2["地點"].notna() &
        dff_fall_feat2[inj_col_f].notna()
    ].copy()

    if not hm_data.empty:
        # 只保留有資料的傷害程度
        valid_inj = [i for i in INJ_ORDER_HM
                     if i in hm_data[inj_col_f].unique()]
        loc_order  = list(LOC_FEATS.keys())

        hm_cross = (hm_data.groupby(["地點", inj_col_f])
                    .size().reset_index(name="件數"))
        hm_piv   = (hm_cross.pivot(index=inj_col_f, columns="地點",
                                    values="件數")
                    .reindex(index=valid_inj, columns=loc_order)
                    .fillna(0).astype(int))

        # 格子內文字
        text_matrix = [[str(v) if v > 0 else "" for v in row]
                       for row in hm_piv.values]

        fig_fe3 = go.Figure(go.Heatmap(
            z=hm_piv.values,
            x=hm_piv.columns.tolist(),
            y=hm_piv.index.tolist(),
            text=text_matrix,
            texttemplate="%{text}",
            textfont=dict(size=14, color="white", family="Arial Bold"),
            colorscale=[
                [0.0, "#F4F6F6"],
                [0.3, "#AED6F1"],
                [0.6, "#3498DB"],
                [1.0, "#1A5276"],
            ],
            hovertemplate=(
                "<b>地點：%{x}</b><br>"
                "傷害程度：%{y}<br>"
                "件數：%{z}<extra></extra>"
            ),
            colorbar=dict(
                title=dict(text="件數",
                           font=dict(size=12, color="#1C2833")),
                tickfont=dict(size=10, color="#2C3E50"),
                thickness=14, len=0.7,
            ),
            xgap=3, ygap=3,
        ))
        fig_fe3.update_layout(
            height=360,
            paper_bgcolor=PAPER_BG,
            plot_bgcolor=PAPER_BG,
            xaxis=dict(
                title=dict(text="發生地點", font=AXIS_TITLE_FONT),
                tickfont=dict(size=12, color="#2C3E50", family="Arial"),
                side="bottom",
            ),
            yaxis=dict(
                title=dict(text="傷害程度", font=AXIS_TITLE_FONT),
                tickfont=dict(size=11, color="#2C3E50", family="Arial"),
                automargin=True,
            ),
            margin=dict(t=20, b=60, l=110, r=80),
        )
        st.plotly_chart(fig_fe3, use_container_width=True)
        st.caption("💡 格子內數字為該組合的事件件數；顏色越深代表件數越多")
    else:
        st.info("目前資料不足以產生交叉熱力圖。")

st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
#  ⚠️ 高風險因子綜合分析
#  資料：dff_fall（時間篩選連動）
# ════════════════════════════════════════════════════════════
RISK_DEPTS       = ["精神科","外科","內科","復健科"]
RISK_FACTOR_DEFS = {
    "鎮靜安眠藥":   lambda s: s["可能原因-鎮靜安眠藥"].eq(1),
    "執意自行下床": lambda s: s["可能原因-高危險群病人執意自行下床或活動"].eq(1),
    "步態不穩":    lambda s: s["可能原因-步態不穩"].eq(1),
    "意識混亂":    lambda s: s["跌倒事件發生對象-當事人當時意識狀況"].isin(["意識混亂","嗜睡"]),
    "無陪伴者":    lambda s: s["跌倒事件發生對象-事件發生時有無陪伴者"].eq("無"),
    "跌倒高危群":  lambda s: s["跌倒事件發生對象-事件發生前是否為跌倒高危險群"].eq("是"),
    "曾跌倒史":    lambda s: s["跌倒事件發生對象-最近一年是否曾經跌倒"].eq("有"),
}
DRUG_FACTOR_DEFS = {
    "鎮靜安眠藥": "可能原因-鎮靜安眠藥",
    "降壓藥":    "可能原因-降壓藥",
    "止痛麻醉劑": "可能原因-止痛麻醉劑",
    "降血糖藥":  "可能原因-降血糖藥",
    "抗癲癇藥":  "可能原因-抗癲癇藥",
    "肌肉鬆弛劑": "可能原因-肌肉鬆弛劑",
}

st.markdown('<div class="chart-container">', unsafe_allow_html=True)
st.markdown(f"""
<div style='background:linear-gradient(135deg,#1a2e3d,#2C3E50);
            padding:14px 20px;border-radius:8px;margin-bottom:16px'>
  <h3 style='color:#FFFFFF;margin:0;font-size:17px;font-weight:700'>
    ⚠️ 高風險因子綜合分析
  </h3>
  <p style='color:#AED6F1;margin:4px 0 0;font-size:11px'>
    資料期間：{start_m} ～ {end_m}　共 {len(dff_fall)} 件跌倒事件（全院）
  </p>
</div>""", unsafe_allow_html=True)

if dff_fall.empty:
    st.info("目前期間內無跌倒事件資料。")
else:
    # ── 圖1：科別 × 高風險因子 熱力矩陣 ────────────────────
    st.markdown('<p class="section-title">① 各科別高風險因子比率熱力矩陣 (%)</p>',
                unsafe_allow_html=True)
    st.markdown(
        '<p style="font-size:12px;color:#5D6D7E;margin:-4px 0 10px 0">'
        '顏色越深代表該科別病人具有此風險因子的比率越高</p>',
        unsafe_allow_html=True)

    hm_rows, hm_text = [], []
    valid_depts_risk = []
    for dept in RISK_DEPTS:
        sub = dff_fall[dff_fall["病人/住民-所在科別"] == dept]
        n   = len(sub)
        if n < 3:
            continue
        valid_depts_risk.append(dept)
        row, txt = [], []
        for fname, func in RISK_FACTOR_DEFS.items():
            try:
                rate = round(func(sub).sum() / n * 100, 1)
            except Exception:
                rate = 0.0
            row.append(rate)
            txt.append(f"{rate:.2f}%<br>(n={n})")
        hm_rows.append(row)
        hm_text.append(txt)

    if valid_depts_risk:
        factor_names = list(RISK_FACTOR_DEFS.keys())

        fig_risk1 = go.Figure(go.Heatmap(
            z=hm_rows,
            x=factor_names,
            y=valid_depts_risk,
            text=hm_text,
            texttemplate="%{text}",
            textfont=dict(size=12, color="white", family="Arial Bold"),
            colorscale=[
                [0.0,  "#FEF9E7"],   # 極低 → 淡黃
                [0.25, "#F9E4B7"],
                [0.5,  "#E59866"],   # 中   → 橙
                [0.75, "#C0392B"],   # 中高 → 紅
                [1.0,  "#641E16"],   # 極高 → 深紅
            ],
            zmin=0, zmax=100,
            hovertemplate=(
                "<b>%{y} — %{x}</b><br>"
                "比率：%{z:.2f}%<extra></extra>"
            ),
            colorbar=dict(
                title=dict(text="比率 (%)",
                           font=dict(size=11, color="#1C2833")),
                tickfont=dict(size=10, color="#2C3E50"),
                ticksuffix="%",
                thickness=14, len=0.75,
            ),
            xgap=4, ygap=4,
        ))
        fig_risk1.update_layout(
            height=280,
            paper_bgcolor=PAPER_BG,
            xaxis=dict(
                title=dict(text="高風險因子", font=AXIS_TITLE_FONT),
                tickfont=dict(size=12, color="#2C3E50", family="Arial"),
                side="bottom",
            ),
            yaxis=dict(
                title=dict(text="科別", font=AXIS_TITLE_FONT),
                tickfont=dict(size=12, color="#2C3E50", family="Arial"),
                automargin=True,
            ),
            margin=dict(t=20, b=70, l=80, r=100),
        )
        st.plotly_chart(fig_risk1, use_container_width=True)

        # ── 動態警示結論（>40% 自動輸出稽核建議）──────────────
        alerts = []
        for dept_i, dept in enumerate(valid_depts_risk):
            for fact_i, fname in enumerate(factor_names):
                val = hm_rows[dept_i][fact_i]
                if val > 40:
                    alerts.append((dept, fname, val))

        if alerts:
            st.markdown('<p class="section-title">🔔 自動稽核警示（比率 > 40% 的高風險組合）</p>',
                        unsafe_allow_html=True)
            # 依數值從高到低排序，最嚴重的排最前面
            alerts.sort(key=lambda x: x[2], reverse=True)
            for dept, fname, val in alerts:
                severity = "🔴 極度警示" if val >= 70 else "🟠 高度警示" if val >= 55 else "🟡 注意"
                bg = "#FADBD8" if val >= 70 else "#FDEBD0" if val >= 55 else "#FEF9E7"
                border = "#C0392B" if val >= 70 else "#E67E22" if val >= 55 else "#F39C12"
                txt_color = "#7B241C" if val >= 70 else "#784212" if val >= 55 else "#7D4700"
                sub = dff_fall[dff_fall["病人/住民-所在科別"] == dept]
                n_dept = len(sub)
                st.markdown(f"""
<div style='background:{bg};border-left:4px solid {border};
            padding:10px 16px;border-radius:4px;margin-bottom:6px;
            font-size:13px;color:{txt_color}'>
  {severity}｜⚠️ <b>{dept}</b> 的 <b>「{fname}」</b> 比例過高達
  <b>{val:.1f}%</b>（{dept} 共 {n_dept} 件跌倒事件）
  ，建議列為本月稽核重點，優先進行護理評估與環境改善。
</div>""", unsafe_allow_html=True)
        else:
            st.info("✅ 目前各科別高風險因子比率均在 40% 以下，無需緊急稽核介入。")

st.markdown('</div>', unsafe_allow_html=True)

# ── 頁底 ─────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align:center;color:#4D5656;font-size:12px;padding:8px 0'>
    🏥 國軍花蓮總醫院 病人安全事件儀表板 v3.3 ｜
    資料來源：病人安全通報系統 ｜ 本系統資料僅供內部品質管理使用
</div>""", unsafe_allow_html=True)
